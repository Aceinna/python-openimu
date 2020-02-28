import os
import time
import json
import datetime
import threading
import serial
import serial.tools.list_ports
from ...framework.utils import helper
from ...framework.utils import resource
from ..base.uart_base import OpenDeviceBase
from ..configs.openrtk_predefine import JSON_FILE_NAME
# import asyncio


class Provider(OpenDeviceBase):
    '''
    OpenRTK UART provider
    '''

    def __init__(self, communicator):
        super(Provider, self).__init__(communicator)
        self.type = 'RTK'
        self.server_update_rate = 100
        self.sky_data = []
        self.bootloader_baudrate = 115200
        self.app_config_folder = ''
        self.device_info = None
        self.app_info = None
        self.parameters = None
        self.setting_folder_path = None
        self.connection_file = None
        self.data_folder = None
        self.debug_serial_port = None
        self.rtcm_serial_port = None
        self.user_logf = None
        self.debug_logf = None
        self.rtcm_logf = None
        self.prepare_folders()

    def prepare_folders(self):
        '''
        Prepare folders for data storage and configuration
        '''
        executor_path = resource.get_executor_path()
        setting_folder_name = 'setting'
        data_folder_path = os.path.join(executor_path, 'data')
        if not os.path.isdir(data_folder_path):
            os.makedirs(data_folder_path)

        # copy contents of app_config under executor path
        self.setting_folder_path = os.path.join(
            executor_path, setting_folder_name, 'openrtk')
        self.connection_file = os.path.join(
            executor_path, setting_folder_name, 'connection.json')
        self.data_folder = data_folder_path

        config_path = os.path.join(self.setting_folder_path, JSON_FILE_NAME)
        if not os.path.isfile(config_path):
            if not os.path.isdir(self.setting_folder_path):
                os.makedirs(self.setting_folder_path)
            app_config_content = resource.get_content_from_bundle(
                setting_folder_name, os.path.join('openrtk', JSON_FILE_NAME))

            with open(config_path, "wb") as code:
                code.write(app_config_content)

    def ping(self):
        '''
        Check if the connected device is OpenRTK
        '''
        # print('start to check if it is openrtk')
        device_info_text = self.internal_input_command('pG')
        app_info_text = self.internal_input_command('gV')

        if device_info_text.find('OpenRTK') > -1:
            self.build_device_info(device_info_text)
            self.build_app_info(app_info_text)
            self.connected = True
            print('Connected', device_info_text)
            return True
        return False

    def build_device_info(self, text):
        '''
        Build device info
        '''
        split_text = text.split(' ')
        self.device_info = {
            'name': split_text[0],
            'imu': split_text[1],
            'pn': split_text[2],
            'firmware_version': split_text[3],
            'sn': split_text[4]
        }

    def build_app_info(self, text):
        '''
        Build app info
        '''
        self.app_info = {
            'version': text
        }

    def load_properties(self):
        with open(os.path.join(self.setting_folder_path, JSON_FILE_NAME)) as json_data:
            self.properties = json.load(json_data)

        # TODO: maybe we need a base config file

    def after_setup(self):
        connection = None
        debug_port = ''
        rtcm_port = ''
        try:
            if not os.path.isfile(self.connection_file):
                return False
            with open(self.connection_file) as json_data:
                connection = json.load(json_data)
            user_port = connection['port']
            user_port_num = ''
            port_name = ''
            for i in range(len(user_port)-1, -1, -1):
                if (user_port[i] >= '0' and user_port[i] <= '9'):
                    user_port_num = user_port[i] + user_port_num
                else:
                    port_name = user_port[:i+1]
                    break
            #print('user_port {0} {1}'.format(user_port_num, port_name))
            debug_port = port_name + str(int(user_port_num) + 2)
            rtcm_port = port_name + str(int(user_port_num) + 3)

            self.debug_serial_port = serial.Serial(
                debug_port, '460800', timeout=0.005)
            self.rtcm_serial_port = serial.Serial(
                rtcm_port, '460800', timeout=0.005)
            if self.debug_serial_port.isOpen() and self.rtcm_serial_port.isOpen():
                #print("debug port {0} and rtcm port {1} open success".format(debug_port, rtcm_port))

                if self.data_folder is not None:
                    file_time = time.strftime(
                        "%Y_%m_%d_%H_%M_%S", time.localtime())
                    self.user_logf = open(
                        self.data_folder + '/' + 'user_' + file_time, "wb")
                    self.debug_logf = open(
                        self.data_folder + '/' + 'debug_' + file_time, "wb")
                    self.rtcm_logf = open(
                        self.data_folder + '/' + 'rtcm_' + file_time, "wb")

                    funcs = [self.thread_debug_port_receiver,
                             self.thread_rtcm_port_receiver]
                    for func in funcs:
                        thread = threading.Thread(target=func, args=())
                        thread.start()

                    return True
            return False
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

    def on_read_raw(self, data):
        if self.user_logf is not None:
            self.user_logf.write(data)

    def thread_debug_port_receiver(self):
        if self.debug_logf is None:
            return
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

    def thread_rtcm_port_receiver(self):
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
        if packet_type == 'pS':
            self.add_output_packet('stream', 'pos', data)

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

        else:
            output_packet_config = next(
                (x for x in self.properties['userMessages']['outputPackets']
                 if x['name'] == packet_type), None)
            if output_packet_config and output_packet_config.__contains__('from') \
                    and output_packet_config['from'] == 'imu':
                self.add_output_packet('stream', 'imu', data)

    def on_receive_input_packet(self, packet_type, data, error):
        '''
        Listener for getting input command packet
        '''
        self.input_result = {'packet_type': packet_type,
                             'data': data, 'error': error}

    def on_receive_bootloader_packet(self, packet_type, data, error):
        '''
        Listener for getting bootloader command packet
        '''

    def get_input_result(self, packet_type, timeout=1):
        '''
        Get input command result
        '''
        result = {'data': None, 'error': None}
        start_time = datetime.datetime.now()
        end_time = datetime.datetime.now()
        span = None

        while self.input_result is None:
            end_time = datetime.datetime.now()
            span = end_time - start_time
            if span.total_seconds() > timeout:
                break

        # if self.input_result:
        #     print('get input packet in:',
        #           span.total_seconds() if span \
        #           else 0, 's', ',packet type:', self.input_result['packet_type'], packet_type)

        if self.input_result is not None and self.input_result['packet_type'] == packet_type:
            result = self.input_result.copy()
        else:
            result['data'] = 'Command timeout'
            result['error'] = True

        self.input_result = None

        return result

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

    def get_log_info(self):  # pylint: disable=invalid-name
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

    def get_conf(self, *args):  # pylint: disable=invalid-name
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

    def get_params(self, *args):  # pylint: disable=invalid-name
        '''
        Get all parameters
        '''
        command_line = helper.build_input_packet('gA')
        self.communicator.write(command_line)
        result = self.get_input_result('gA', timeout=2)

        if result['data']:
            self.parameters = result['data']
            return {
                'packetType': 'inputParams',
                'data': result['data']
            }
        else:
            return {
                'packetType': 'error',
                'data': 'No Response'
            }

    def get_param(self, params, *args):  # pylint: disable=invalid-name
        '''
        Update paramter value
        '''
        command_line = helper.build_input_packet(
            'gP', properties=self.properties, param=params['paramId'])
        self.communicator.write(command_line)
        result = self.get_input_result('gP', timeout=1)

        if result['data']:
            self.parameters = result['data']
            return {
                'packetType': 'inputParam',
                'data': result['data']
            }
        else:
            return {
                'packetType': 'error',
                'data': 'No Response'
            }

    def set_params(self, params, *args):  # pylint: disable=invalid-name
        '''
        Update paramters value
        '''
        for parameter in params:
            result = self.set_param(parameter)
            if result['packetType'] == 'error':
                return {
                    'packetType': 'error',
                    'data': {
                        'error': result['data']['error']
                    }
                }
            if result['data']['error'] > 0:
                return {
                    'packetType': 'error',
                    'data': {
                        'error': result['data']['error']
                    }
                }

        return {
            'packetType': 'success',
            'data': {
                'error': 0
            }
        }

    def set_param(self, params, *args):  # pylint: disable=invalid-name
        '''
        Update paramter value
        '''
        command_line = helper.build_input_packet(
            'uP', properties=self.properties, param=params['paramId'], value=params['value'])
        self.communicator.write(command_line)
        result = self.get_input_result('uP', timeout=1)

        if result['error']:
            return {
                'packetType': 'error',
                'data': {
                    'error': result['data']
                }
            }
        else:
            return {
                'packetType': 'success',
                'data': {
                    'error': result['data']
                }
            }

    def save_config(self, *args):  # pylint: disable=invalid-name
        '''
        Save configuration
        '''
        command_line = helper.build_input_packet('sC')
        self.communicator.write(command_line)

        result = self.get_input_result('sC', timeout=2)

        if result['data']:
            return {
                'packetType': 'success',
                'data': result['data']
            }
        else:
            return {
                'packetType': 'success',
                'data': result['error']
            }

    def upgrade_framework(self, file, *args):  # pylint: disable=invalid-name
        '''
        Upgrade framework
        '''
        # start a thread to do upgrade
        if not self.is_upgrading:
            self.is_upgrading = True

            if self._logger is not None:
                self._logger.stop_user_log()

            thread = threading.Thread(
                target=self.thread_do_upgrade_framework, args=(file,))
            thread.start()
            print("Thread upgarde framework OpenRTK start at:[{0}].".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        return {
            'packetType': 'success'
        }
