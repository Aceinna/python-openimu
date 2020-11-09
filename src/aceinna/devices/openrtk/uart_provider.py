import os
import time
import json
import datetime
import threading
import math
import re
import collections
import serial
import serial.tools.list_ports
from .ntrip_client import NTRIPClient
from ...framework.utils import (
    helper, resource
)
from ...framework.context import APP_CONTEXT
from ..base.provider_base import OpenDeviceBase
from ..configs.openrtk_predefine import (
    APP_STR, get_app_names
)
from ..decorator import with_device_message
from .firmware_parser import parser as firmware_content_parser
from ...models import InternalCombineAppParseRule
from ..upgrade_workers import (
    FirmwareUpgradeWorker,
    SDKUpgradeWorker
)
from ..upgrade_center import UpgradeCenter
from ..parsers.open_field_parser import encode_value


class Provider(OpenDeviceBase):
    '''
    OpenRTK UART provider
    '''

    def __init__(self, communicator, *args):
        super(Provider, self).__init__(communicator)
        self.type = 'RTK'
        self.server_update_rate = 100
        self.sky_data = []
        self.pS_data = []
        self.ps_dic = collections.OrderedDict()
        self.inspva_flag = 0
        self.bootloader_baudrate = 115200
        self.app_config_folder = ''
        self.device_info = None
        self.app_info = None
        self.parameters = None
        self.setting_folder_path = None
        self.data_folder = None
        self.debug_serial_port = None
        self.rtcm_serial_port = None
        self.user_logf = None
        self.debug_logf = None
        self.rtcm_logf = None
        self.debug_c_f = None
        self.enable_data_log = False
        self.is_app_matched = False
        self.ntrip_client_enable = False
        self.nmea_buffer = []
        self.nmea_sync = 0
        self.prepare_folders()
        self.ntripClient = None
        self.connected = True

    def prepare_folders(self):
        '''
        Prepare folders for data storage and configuration
        '''
        executor_path = resource.get_executor_path()
        setting_folder_name = 'setting'
        config_file_name = 'openrtk.json'

        data_folder_path = os.path.join(executor_path, 'data')
        if not os.path.isdir(data_folder_path):
            os.makedirs(data_folder_path)
        self.data_folder = data_folder_path

        # copy contents of app_config under executor path
        self.setting_folder_path = os.path.join(
            executor_path, setting_folder_name, 'openrtk')

        for app_name in get_app_names():
            app_name_path = os.path.join(self.setting_folder_path, app_name)
            app_name_config_path = os.path.join(
                app_name_path, config_file_name)
            if not os.path.isfile(app_name_config_path):
                if not os.path.isdir(app_name_path):
                    os.makedirs(app_name_path)
                app_config_content = resource.get_content_from_bundle(
                    setting_folder_name, os.path.join('openrtk', app_name, config_file_name))
                if app_config_content is None:
                    continue

                with open(app_name_config_path, "wb") as code:
                    code.write(app_config_content)

    def bind_device_info(self, device_access, device_info, app_info):
        self._build_device_info(device_info)
        self._build_app_info(app_info)
        self.connected = True

        port_name = device_access.port

        return '# Connected {0} with UART on {1} #\n\rDevice:{2} \n\rFirmware:{3}'\
            .format('OpenRTK', port_name, device_info, app_info)

    def _build_device_info(self, text):
        '''
        Build device info
        '''
        split_text = [x for x in text.split(' ') if x != '']
        sn = split_text[4]
        # remove the prefix of SN
        if sn.find('SN:') == 0:
            sn = sn[3:]

        self.device_info = {
            'name': split_text[0],
            'imu': split_text[1],
            'pn': split_text[2],
            'firmware_version': split_text[3],
            'sn': sn
        }

    def _build_app_info(self, text):
        '''
        Build app info
        '''
        app_version = text

        split_text = app_version.split(' ')
        app_name = next(
            (item for item in APP_STR if item in split_text), None)

        if not app_name:
            app_name = 'INS'
            self.is_app_matched = False
        else:
            self.is_app_matched = True

        self.app_info = {
            'app_name': app_name,
            'version': text
        }

    def load_properties(self):
        # Load config from user working path
        local_config_file_path = os.path.join(os.getcwd(), 'openrtk.json')
        if os.path.isfile(local_config_file_path):
            with open(local_config_file_path) as json_data:
                self.properties = json.load(json_data)
                return

        # Load the openimu.json based on its app
        app_name = self.app_info['app_name']
        app_file_path = os.path.join(
            self.setting_folder_path, app_name, 'openrtk.json')

        with open(app_file_path) as json_data:
            self.properties = json.load(json_data)

    def ntrip_client_thread(self):
        self.ntripClient = NTRIPClient(self.properties, self.communicator)
        self.ntripClient.run()

    def build_connected_serial_port_info(self):
        if not self.communicator.serial_port:
            return None, None

        user_port = self.communicator.serial_port.port
        user_port_num = ''
        port_name = ''
        for i in range(len(user_port)-1, -1, -1):
            if (user_port[i] >= '0' and user_port[i] <= '9'):
                user_port_num = user_port[i] + user_port_num
            else:
                port_name = user_port[:i+1]
                break
        return user_port_num, port_name

    def after_setup(self):
        set_user_para = self.cli_options and self.cli_options.set_user_para
        self.ntrip_client_enable = self.cli_options and self.cli_options.ntrip_client
        # with_raw_log = self.cli_options and self.cli_options.with_raw_log

        if set_user_para:
            result = self.set_params(
                self.properties["initial"]["userParameters"])
            ##print('set user para {0}'.format(result))
            if (result['packetType'] == 'success'):
                self.save_config()

        if self.ntrip_client_enable:
            t = threading.Thread(target=self.ntrip_client_thread)
            t.start()

        # if with_raw_log:
        connection = None
        debug_port = ''
        rtcm_port = ''
        try:
            if (self.properties["initial"]["useDefaultUart"]):
                user_port_num, port_name = self.build_connected_serial_port_info()
                if not user_port_num or not port_name:
                    return False
                #print('user_port {0} {1}'.format(user_port_num, port_name))
                debug_port = port_name + str(int(user_port_num) + 2)
                rtcm_port = port_name + str(int(user_port_num) + 1)
            else:
                for x in self.properties["initial"]["uart"]:
                    if x['enable'] == 1:
                        if x['name'] == 'DEBUG':
                            debug_port = x["value"]
                        elif x['name'] == 'GNSS':
                            rtcm_port = x["value"]

            if self.data_folder is not None:
                dir_time = time.strftime("%Y%m%d_%H%M%S", time.localtime())
                file_time = time.strftime(
                    "%Y_%m_%d_%H_%M_%S", time.localtime())
                file_name = self.data_folder + '/' + 'openrtk_log_' + dir_time
                os.mkdir(file_name)
                self.user_logf = open(
                    file_name + '/' + 'user_' + file_time + '.bin', "wb")

            if rtcm_port != '':
                print('OpenRTK log GNSS UART {0}'.format(rtcm_port))
                self.rtcm_serial_port = serial.Serial(
                    rtcm_port, '460800', timeout=0.1)
                if self.rtcm_serial_port.isOpen():
                    self.rtcm_logf = open(
                        file_name + '/' + 'rtcm_rover_' + file_time + '.bin', "wb")
                    t = threading.Thread(
                        target=self.thread_rtcm_port_receiver, args=(file_name,))
                    t.start()

            if debug_port != '':
                print('OpenRTK log DEBUG UART {0}'.format(debug_port))
                self.debug_serial_port = serial.Serial(
                    debug_port, '460800', timeout=0.1)
                if self.debug_serial_port.isOpen():
                    if self.app_info['app_name'] == 'RAWDATA':
                        self.debug_logf = open(
                            file_name + '/' + 'rtcm_base_' + file_time + '.bin', "wb")
                    elif self.app_info['app_name'] == 'RTK':
                        self.debug_logf = open(
                            file_name + '/' + 'rtcm_base_' + file_time + '.bin', "wb")
                    else:
                        self.debug_logf = open(
                            file_name + '/' + 'rtcm_base_' + file_time + '.bin', "wb")
                    t = threading.Thread(
                        target=self.thread_debug_port_receiver, args=(file_name,))
                    t.start()

        except Exception as e:
            if self.debug_serial_port is not None:
                if self.debug_serial_port.isOpen():
                    self.debug_serial_port.close()
            if self.rtcm_serial_port is not None:
                if self.rtcm_serial_port.isOpen():
                    self.rtcm_serial_port.close()
            self.debug_serial_port = None
            self.rtcm_serial_port = None
            print(e)
            return False

    def after_bootloader_switch(self):
        self.communicator.serial_port.baudrate = self.bootloader_baudrate

    def nmea_checksum(self, data):
        data = data.replace("\r", "").replace("\n", "").replace("$", "")
        nmeadata, cksum = re.split('\*', data)
        calc_cksum = 0
        for s in nmeadata:
            calc_cksum ^= ord(s)
        return int(cksum, 16), calc_cksum

    def on_read_raw(self, data):
        for bytedata in data:
            if bytedata == 0x24:
                self.nmea_buffer = []
                self.nmea_sync = 0
                self.nmea_buffer.append(chr(bytedata))
            else:
                self.nmea_buffer.append(chr(bytedata))
                if self.nmea_sync == 0:
                    if bytedata == 0x0D:
                        self.nmea_sync = 1
                elif self.nmea_sync == 1:
                    if bytedata == 0x0A:
                        try:
                            str_nmea = ''.join(self.nmea_buffer)
                            cksum, calc_cksum = self.nmea_checksum(
                                str_nmea)
                            if cksum == calc_cksum:
                                if str_nmea.find("$GPGGA") != -1:
                                    print()
                                    if self.ntrip_client_enable and self.ntripClient != None:
                                        self.ntripClient.send(str_nmea)
                                print(str_nmea, end='')

                                # else:
                                #     print("nmea checksum wrong {0} {1}".format(cksum, calc_cksum))
                        except Exception as e:
                            # print('NMEA fault:{0}'.format(e))
                            pass
                    self.nmea_buffer = []
                    self.nmea_sync = 0

        if self.user_logf is not None:
            self.user_logf.write(data)

    def thread_debug_port_receiver(self, *args, **kwargs):
        if self.debug_logf is None:
            return

        is_get_configuration = 0
        file_name = args[0]
        self.debug_c_f = open(file_name + '/' + 'configuration.json', "w")

        while True:
            if is_get_configuration:
                break
            cmd_configuration = 'get configuration\r\n'
            self.debug_serial_port.write(cmd_configuration.encode())
            try_times = 20
            for i in range(try_times):
                data_buffer = self.debug_serial_port.read(500)
                if len(data_buffer):
                    try:
                        #print('len = {0}'.format(len(data_buffer)))
                        str_data = bytes.decode(data_buffer)
                        # print('{0}'.format(str_data))
                        json_data = json.loads(str_data)
                        for key in json_data.keys():
                            if key == 'openrtk configuration':
                                print('{0}'.format(json_data))
                                if self.debug_c_f:
                                    self.debug_c_f.write(str_data)
                                    self.debug_c_f.close()
                                is_get_configuration = 1
                        if is_get_configuration:
                            break
                    except Exception as e:
                        #print('DEBUG PORT Thread:json error:', e)
                        # the json will not be completed
                        pass

        cmd_log = 'log debug on\r\n'
        self.debug_serial_port.write(cmd_log.encode())

        # log data
        while True:
            try:
                data = bytearray(self.debug_serial_port.read_all())
            except Exception as e:
                print('DEBUG PORT Thread:receiver error:', e)
                return  # exit thread receiver
            if len(data):
                self.debug_logf.write(data)
            else:
                time.sleep(0.001)

    def thread_rtcm_port_receiver(self, *args, **kwargs):
        if self.rtcm_logf is None:
            return
        while True:
            try:
                data = bytearray(self.rtcm_serial_port.read_all())
            except Exception as e:
                print('RTCM PORT Thread:receiver error:', e)
                return  # exit thread receiver
            if len(data):
                self.rtcm_logf.write(data)
            else:
                time.sleep(0.001)

    def on_receive_output_packet(self, packet_type, data, error=None):
        '''
        Listener for getting output packet
        '''
        # $GPGGA,080319.00,3130.4858508,N,12024.0998832,E,4,25,0.5,12.459,M,0.000,M,2.0,*46
        if packet_type == 'gN':
            if self.ntrip_client_enable:
                # $GPGGA
                gpgga = '$GPGGA'
                # time
                timeOfWeek = float(data['GPS_TimeofWeek'])
                dsec = int(timeOfWeek)
                msec = timeOfWeek - dsec
                sec = dsec % 86400
                hour = int(sec / 3600)
                minute = int(sec % 3600 / 60)
                second = sec % 60
                gga_time = format(hour*10000 + minute*100 +
                                  second + msec - 18, '09.2f')
                gpgga = gpgga + ',' + gga_time
                # latitude
                latitude = float(data['latitude']) * 180 / 2147483648.0
                if latitude >= 0:
                    latflag = 'N'
                else:
                    latflag = 'S'
                    latitude = math.fabs(latitude)
                lat_d = int(latitude)
                lat_m = (latitude-lat_d) * 60
                lat_dm = format(lat_d*100 + lat_m, '012.7f')
                gpgga = gpgga + ',' + lat_dm + ',' + latflag
                # longitude
                longitude = float(data['longitude']) * 180 / 2147483648.0
                if longitude >= 0:
                    lonflag = 'E'
                else:
                    lonflag = 'W'
                    longitude = math.fabs(longitude)
                lon_d = int(longitude)
                lon_m = (longitude-lon_d) * 60
                lon_dm = format(lon_d*100 + lon_m, '013.7f')
                gpgga = gpgga + ',' + lon_dm + ',' + lonflag
                # positionMode
                gpgga = gpgga + ',' + str(data['positionMode'])
                # svs
                gpgga = gpgga + ',' + str(data['numberOfSVs'])
                # hop
                gpgga = gpgga + ',' + format(float(data['hdop']), '03.1f')
                # height
                gpgga = gpgga + ',' + \
                    format(float(data['height']), '06.3f') + ',M'
                #
                gpgga = gpgga + ',0.000,M'
                # diffage
                gpgga = gpgga + ',' + \
                    format(float(data['diffage']), '03.1f') + ','
                # ckm
                checksum = 0
                for i in range(1, len(gpgga)):
                    checksum = checksum ^ ord(gpgga[i])
                str_checksum = hex(checksum)
                if str_checksum.startswith("0x"):
                    str_checksum = str_checksum[2:]
                gpgga = gpgga + '*' + str_checksum + '\r\n'
                print(gpgga)
                if self.ntripClient != None:
                    self.ntripClient.send(gpgga)
                return

        elif packet_type == 'pS':
            try:
                if data['latitude'] != 0.0 and data['longitude'] != 0.0:
                    if self.pS_data:
                        if self.pS_data['GPS_Week'] == data['GPS_Week']:
                            if data['GPS_TimeofWeek'] - self.pS_data['GPS_TimeofWeek'] >= 0.2:
                                self.add_output_packet('stream', 'pos', data)
                                self.pS_data = data

                                if data['insStatus'] >= 3 and data['insStatus'] <= 5:
                                    ins_status = 'INS_INACTIVE'
                                    if data['insStatus'] == 3:
                                        ins_status = 'INS_SOLUTION_GOOD'
                                    elif data['insStatus'] == 4:
                                        ins_status = 'INS_SOLUTION_FREE'
                                    elif data['insStatus'] == 5:
                                        ins_status = 'INS_ALIGNMENT_COMPLETE'

                                    ins_pos_type = 'INS_INVALID'
                                    if data['insPositionType'] == 1:
                                        ins_pos_type = 'INS_SPP'
                                    elif data['insPositionType'] == 4:
                                        ins_pos_type = 'INS_RTKFIXED'
                                    elif data['insPositionType'] == 5:
                                        ins_pos_type = 'INS_RTKFLOAT'

                                    inspva = '#INSPVA,%s,%10.2f, %s, %s,%12.8f,%13.8f,%8.3f,%9.3f,%9.3f,%9.3f,%9.3f,%9.3f,%9.3f' %\
                                        (data['GPS_Week'], data['GPS_TimeofWeek'], ins_status, ins_pos_type,
                                         data['latitude'], data['longitude'], data['height'],
                                         data['velocityNorth'], data['velocityEast'], data['velocityUp'],
                                         data['roll'], data['pitch'], data['heading'])
                                    print(inspva)
                        else:
                            self.add_output_packet('stream', 'pos', data)
                            self.pS_data = data
                    else:
                        self.add_output_packet('stream', 'pos', data)
                        self.pS_data = data
            except Exception as e:
                # print(e)
                pass

        elif packet_type == 'sK':
            if self.sky_data:
                if self.sky_data[0]['timeOfWeek'] == data[0]['timeOfWeek']:
                    self.sky_data.extend(data)
                else:
                    self.add_output_packet('stream', 'skyview', self.sky_data)
                    self.add_output_packet('stream', 'snr', self.sky_data)
                    self.sky_data = []
                    self.sky_data.extend(data)
            else:
                self.sky_data.extend(data)

        elif packet_type == 'g1':
            self.ps_dic['positionMode'] = data['position_type']
            self.ps_dic['numberOfSVs'] = data['number_of_satellites_in_solution']
            self.ps_dic['hdop'] = data['hdop']
            self.ps_dic['age'] = data['diffage']
            if self.inspva_flag == 0:
                self.ps_dic['GPS_Week'] = data['GPS_Week']
                self.ps_dic['GPS_TimeofWeek'] = data['GPS_TimeOfWeek'] * 0.001
                self.ps_dic['latitude'] = data['latitude']
                self.ps_dic['longitude'] = data['longitude']
                self.ps_dic['height'] = data['height']
                self.ps_dic['velocityMode'] = 1
                self.ps_dic['velocityNorth'] = data['north_vel']
                self.ps_dic['velocityEast'] = data['east_vel']
                self.ps_dic['velocityUp'] = data['up_vel']
                self.ps_dic['latitude_std'] = data['latitude_standard_deviation']
                self.ps_dic['longitude_std'] = data['longitude_standard_deviation']
                self.ps_dic['height_std'] = data['height_standard_deviation']
                self.ps_dic['north_vel_std'] = data['north_vel_standard_deviation']
                self.ps_dic['east_vel_std'] = data['east_vel_standard_deviation']
                self.ps_dic['up_vel_std'] = data['up_vel_standard_deviation']
                self.add_output_packet('stream', 'pos', self.ps_dic)

        elif packet_type == 'i1':
            self.inspva_flag = 1
            if data['GPS_TimeOfWeek'] % 200 == 0:
                self.ps_dic['GPS_Week'] = data['GPS_Week']
                self.ps_dic['GPS_TimeofWeek'] = data['GPS_TimeOfWeek'] * 0.001
                self.ps_dic['latitude'] = data['latitude']
                self.ps_dic['longitude'] = data['longitude']
                self.ps_dic['height'] = data['height']
                if data['ins_position_type'] != 1 and data['ins_position_type'] != 4 and data['ins_position_type'] != 5:
                    self.ps_dic['velocityMode'] = 2
                else:
                    self.ps_dic['velocityMode'] = 1
                self.ps_dic['insStatus'] = data['ins_status']
                self.ps_dic['insPositionType'] = data['ins_position_type']
                self.ps_dic['velocityNorth'] = data['north_velocity']
                self.ps_dic['velocityEast'] = data['east_velocity']
                self.ps_dic['velocityUp'] = data['up_velocity']
                self.ps_dic['roll'] = data['roll']
                self.ps_dic['pitch'] = data['pitch']
                self.ps_dic['heading'] = data['heading']
                self.ps_dic['latitude_std'] = data['latitude_std']
                self.ps_dic['longitude_std'] = data['longitude_std']
                self.ps_dic['height_std'] = data['height_std']
                self.ps_dic['north_vel_std'] = data['north_velocity_std']
                self.ps_dic['east_vel_std'] = data['east_velocity_std']
                self.ps_dic['up_vel_std'] = data['up_velocity_std']
                self.ps_dic['roll_std'] = data['roll_std']
                self.ps_dic['pitch_std'] = data['pitch_std']
                self.ps_dic['heading_std'] = data['heading_std']
                self.add_output_packet('stream', 'pos', self.ps_dic)

        elif packet_type == 'y1':
            if self.sky_data:
                if self.sky_data[0]['GPS_TimeOfWeek'] == data[0]['GPS_TimeOfWeek']:
                    self.sky_data.extend(data)
                else:
                    # print(self.sky_data)
                    self.add_output_packet('stream', 'skyview', self.sky_data)
                    self.add_output_packet('stream', 'snr', self.sky_data)
                    self.sky_data = []
                    self.sky_data.extend(data)
            else:
                self.sky_data.extend(data)

        else:
            output_packet_config = next(
                (x for x in self.properties['userMessages']['outputPackets']
                 if x['name'] == packet_type), None)
            if output_packet_config and output_packet_config.__contains__('from') \
                    and output_packet_config['from'] == 'imu':
                self.add_output_packet('stream', 'imu', data)

    def do_write_firmware(self, firmware_content):
        rules = [
            InternalCombineAppParseRule('rtk', 'rtk_start:', 4),
            InternalCombineAppParseRule('sdk', 'sdk_start:', 4),
        ]

        parsed_content = firmware_content_parser(firmware_content, rules)

        if (self.properties["initial"]["useDefaultUart"]):
            user_port_num, port_name = self.build_connected_serial_port_info()
            sdk_port = port_name + str(int(user_port_num) + 3)
        else:
            for x in self.properties["initial"]["uart"]:
                if x['enable'] == 1:
                    if x['name'] == 'DEBUG':
                        debug_port = x["value"]
                    elif x['name'] == 'GNSS':
                        rtcm_port = x["value"]
                    elif x['name'] == 'SDK':
                        sdk_port = x["value"]

        sdk_uart = serial.Serial(sdk_port, 115200, timeout=0.1)
        if not sdk_uart.isOpen():
            raise Exception('Cannot open SDK upgrade port')

        upgrade_center = UpgradeCenter()

        upgrade_center.register(
            FirmwareUpgradeWorker(self.communicator, parsed_content['rtk']))

        upgrade_center.register(
            SDKUpgradeWorker(sdk_uart, parsed_content['sdk']))

        upgrade_center.on('progress', self.handle_upgrade_process)
        upgrade_center.on('error', self.handle_upgrade_error)
        upgrade_center.on('finish', self.handle_upgrade_complete)
        upgrade_center.start()

    def get_device_connection_info(self):
        return {
            'modelName': self.device_info['name'],
            'deviceType': self.type,
            'serialNumber': self.device_info['sn'],
            'partNumber': self.device_info['pn'],
            'firmware': self.device_info['firmware_version']
        }

    # command list
    def server_status(self, *args):  # pylint: disable=invalid-name
        '''
        Get server connection status
        '''
        return {
            'packetType': 'ping',
            'data': {'status': '1'}
        }

    def get_device_info(self, *args):  # pylint: disable=invalid-name
        '''
        Get device information
        '''
        return {
            'packetType': 'deviceInfo',
            'data':  [
                {'name': 'Product Name', 'value': self.device_info['name']},
                {'name': 'IMU', 'value': self.device_info['imu']},
                {'name': 'PN', 'value': self.device_info['pn']},
                {'name': 'Firmware Version',
                 'value': self.device_info['firmware_version']},
                {'name': 'SN', 'value': self.device_info['sn']},
                {'name': 'App Version', 'value': self.app_info['version']}
            ]
        }

    def get_log_info(self):
        '''
        Build information for log
        '''
        return {
            "type": self.type,
            "model": self.device_info['name'],
            "logInfo": {
                "pn": self.device_info['pn'],
                "sn": self.device_info['sn'],
                "rtkProperties": json.dumps(self.properties)
            }
        }

    def get_conf(self, *args):  # pylint: disable=unused-argument
        '''
        Get json configuration
        '''
        return {
            'packetType': 'conf',
            'data': {
                'outputs': self.properties['userMessages']['outputPackets'],
                'inputParams': self.properties['userConfiguration']
            }
        }

    @with_device_message
    def get_params(self, *args):  # pylint: disable=unused-argument
        '''
        Get all parameters
        '''
        has_error = False
        parameter_values = []

        if self.app_info['app_name'] == 'INS':
            conf_parameters = self.properties['userConfiguration']
            conf_parameters_len = len(conf_parameters)-1
            step = 10

            for i in range(2, conf_parameters_len, step):
                start_byte = i
                end_byte = i+step-1 if i+step < conf_parameters_len else conf_parameters_len
                time.sleep(0.1)
                command_line = helper.build_packet(
                    'gB', [start_byte, end_byte])
                result = yield self._message_center.build(command=command_line, timeout=10)
                if result['error']:
                    has_error = True
                    break

                parameter_values.extend(result['data'])
        else:
            command_line = helper.build_input_packet('gA')
            result = yield self._message_center.build(command=command_line, timeout=3)
            if result['error']:
                has_error = True

            parameter_values = result['data']

        if not has_error:
            self.parameters = parameter_values
            yield {
                'packetType': 'inputParams',
                'data': parameter_values
            }

        yield {
            'packetType': 'error',
            'data': 'No Response'
        }

    @with_device_message
    def get_param(self, params, *args):  # pylint: disable=unused-argument
        '''
        Update paramter value
        '''
        command_line = helper.build_input_packet(
            'gP', properties=self.properties, param=params['paramId'])
        # self.communicator.write(command_line)
        # result = self.get_input_result('gP', timeout=1)
        result = yield self._message_center.build(command=command_line)

        if result['data']:
            self.parameters = result['data']
            yield {
                'packetType': 'inputParam',
                'data': result['data']
            }

        yield {
            'packetType': 'error',
            'data': 'No Response'
        }

    @with_device_message
    def set_params(self, params, *args):  # pylint: disable=unused-argument
        '''
        Update paramters value
        '''
        input_parameters = self.properties['userConfiguration']
        grouped_parameters = {}

        for parameter in params:
            exist_parameter = next(
                (x for x in input_parameters if x['paramId'] == parameter['paramId']), None)

            if exist_parameter:
                has_group = grouped_parameters.__contains__(
                    exist_parameter['category'])
                if not has_group:
                    grouped_parameters[exist_parameter['category']] = []

                current_group = grouped_parameters[exist_parameter['category']]

                current_group.append(
                    {'paramId': parameter['paramId'], 'value': parameter['value'], 'type': exist_parameter['type']})

        for group in grouped_parameters.values():
            message_bytes = []
            for parameter in group:
                message_bytes.extend(
                    encode_value('int8', parameter['paramId'])
                )
                message_bytes.extend(
                    encode_value(parameter['type'], parameter['value'])
                )
                # print('parameter type {0}, value {1}'.format(
                #     parameter['type'], parameter['value']))
            # result = self.set_param(parameter)
            command_line = helper.build_packet(
                'uB', message_bytes)
            # for s in command_line:
            #     print(hex(s))

            result = yield self._message_center.build(command=command_line)

            packet_type = result['packet_type']
            data = result['data']

            if packet_type == 'error':
                yield {
                    'packetType': 'error',
                    'data': {
                        'error': data
                    }
                }
                break

            if data > 0:
                yield {
                    'packetType': 'error',
                    'data': {
                        'error': data
                    }
                }
                break

        yield {
            'packetType': 'success',
            'data': {
                'error': 0
            }
        }

    @with_device_message
    def set_param(self, params, *args):  # pylint: disable=unused-argument
        '''
        Update paramter value
        '''
        command_line = helper.build_input_packet(
            'uP', properties=self.properties, param=params['paramId'], value=params['value'])
        # self.communicator.write(command_line)
        # result = self.get_input_result('uP', timeout=1)
        result = yield self._message_center.build(command=command_line)

        error = result['error']
        data = result['data']
        if error:
            yield {
                'packetType': 'error',
                'data': {
                    'error': data
                }
            }

        yield {
            'packetType': 'success',
            'data': {
                'error': data
            }
        }

    @with_device_message
    def save_config(self, *args):  # pylint: disable=unused-argument
        '''
        Save configuration
        '''
        command_line = helper.build_input_packet('sC')
        # self.communicator.write(command_line)
        # result = self.get_input_result('sC', timeout=2)
        result = yield self._message_center.build(command=command_line, timeout=2)

        data = result['data']
        error = result['error']
        if data:
            yield {
                'packetType': 'success',
                'data': error
            }

        yield {
            'packetType': 'success',
            'data': error
        }

    @with_device_message
    def reset_params(self, params, *args):  # pylint: disable=unused-argument
        '''
        Reset params to default
        '''
        command_line = helper.build_input_packet('rD')
        result = yield self._message_center.build(command=command_line, timeout=2)

        error = result['error']
        data = result['data']
        if error:
            yield {
                'packetType': 'error',
                'data': {
                    'error': error
                }
            }

        yield {
            'packetType': 'success',
            'data': data
        }

    def upgrade_framework(self, params, *args):  # pylint: disable=unused-argument
        '''
        Upgrade framework
        '''
        file = ''
        if isinstance(params, str):
            file = params

        if isinstance(params, dict):
            file = params['file']

        # start a thread to do upgrade
        if not self.is_upgrading:
            self.is_upgrading = True
            self._message_center.pause()

            if self._logger is not None:
                self._logger.stop_user_log()

            thread = threading.Thread(
                target=self.thread_do_upgrade_framework, args=(file,))
            thread.start()
            print("Upgrade OpenRTK firmware started at:[{0}].".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        return {
            'packetType': 'success'
        }
