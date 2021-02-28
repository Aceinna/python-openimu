import os
import re
import sys
import time
import json
import binascii
import math
# import asyncio
import datetime
import threading
import struct
from ...framework.utils import helper
from ...framework.utils import resource
from ..base import OpenDeviceBase

from ...framework.context import APP_CONTEXT
from ..decorator import with_device_message
from ...framework.configuration import get_config
from ..upgrade_workers import FirmwareUpgradeWorker
from ..upgrade_center import UpgradeCenter
from ..parsers.open_field_parser import encode_value


class Provider(OpenDeviceBase):
    '''
    INS2000 UART provider
    '''

    def __init__(self, communicator, *args):
        super(Provider, self).__init__(communicator)
        self.type = 'INS2000'
        self.server_update_rate = 50
        self.is_logging = False
        self.is_mag_align = False
        self.bootloader_baudrate = 460800
        self.device_info = None
        self.app_info = None
        self.app_config_folder = ''
        self.parameters = None
        self.enable_data_log = True
        self.data_folder_path = None
        self.prepare_folders()
        self.is_backup = False
        self.is_restore = False
        self.is_app_matched = False
        self.connected = True
        self.raw_log_file = None
        self.best_gnss_pos = None
        self.inspvax = None
        self.gps_week = 0
        self.gps_seconds = 0

    def prepare_folders(self):
        '''
        Prepare folders for data storage and configuration
        '''
        executor_path = resource.get_executor_path()
        setting_folder_name = 'setting'
        config_file_name = 'INS2000.json'

        self.data_folder_path = os.path.join(executor_path, 'data')
        if not os.path.isdir(self.data_folder_path):
            os.makedirs(self.data_folder_path)

        self.setting_folder_path = os.path.join(
            executor_path, setting_folder_name, 'INS2000')

        config_file_path = os.path.join(
            self.setting_folder_path, config_file_name)

        if not os.path.isfile(config_file_path):
            if not os.path.isdir(self.setting_folder_path):
                os.makedirs(self.setting_folder_path)

            app_config_content = resource.get_content_from_bundle(
                setting_folder_name, os.path.join('INS2000', config_file_name))

            with open(config_file_path, "wb") as code:
                code.write(app_config_content)

    @property
    def is_in_bootloader(self):
        ''' Check if the connected device is in bootloader mode
        '''
        return False

    def bind_device_info(self, device_access, device_info, app_info):
        self._build_device_info(device_info)
        self._build_app_info(app_info)
        self.connected = True

        return '# Connected {0} #\n\rDevice:{1} \n\rFirmware:{2}'\
            .format(self.type, device_info, app_info)

    def _build_device_info(self, text):
        '''
        Build device info
        '''

    def _build_app_info(self, text):
        '''
        Build app info
        '''

    def load_properties(self):
        '''
        load properties
        '''
        # Load config from user working path
        local_config_file_path = os.path.join(os.getcwd(), 'INS2000.json')
        if os.path.isfile(local_config_file_path):
            with open(local_config_file_path) as json_data:
                self.properties = json.load(json_data)
                return

        # Load the openimu.json based on its app
        app_file_path = os.path.join(
            self.setting_folder_path, 'INS2000.json')

        with open(app_file_path) as json_data:
            self.properties = json.load(json_data)

    def after_setup(self):
        setupcommands = self.properties["setupcommands"]

        if self.data_folder_path is not None:
            dir_time = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            file_time = time.strftime(
                "%Y_%m_%d_%H_%M_%S", time.localtime())
            file_name = self.data_folder_path + '/' + 'ins2000_log_' + dir_time
            os.mkdir(file_name)
            self.raw_log_file = open(
                file_name + '/' + 'raw_' + file_time + '.bin', "wb")

        # self.communicator.flushInput()
        for cmd in setupcommands:
            self.communicator.write(cmd.encode())
            time.sleep(0.01)

    def after_bootloader_switch(self):
        self.communicator.serial_port.baudrate = self.bootloader_baudrate

    def on_read_raw(self, data):
        if self.raw_log_file is not None:
            self.raw_log_file.write(data)

    def on_receive_output_packet(self, packet_type, data):
        '''receive output packet'''
        # print(type(packet_type))
        if type(packet_type) == int:
            self.gps_week = data['header_gps_week']
            self.gps_seconds = data['header_gps_seconds']

        if packet_type == 1429:
            if data['lat'] != 0.0 and data['lon'] != 0.0:
                # print(packet_type, data)
                self.best_gnss_pos = data
                self.output_pos()

        if packet_type == 1465:
            # print(packet_type, data)
            if data['lat'] != 0.0 and data['lon'] != 0.0:
                # print(packet_type, data)
                self.inspvax = data
                self.output_pos()

        if packet_type == 1462:
            self.output_imu(data)

        if packet_type == 'nmea':
            self.output_nmea(data)

    def output_pos(self):
        '''output pos'''
        if self.best_gnss_pos is not None and \
            self.inspvax is not None and \
            self.best_gnss_pos['header_gps_week'] == self.inspvax['header_gps_week'] and \
            self.best_gnss_pos['header_gps_seconds'] == self.inspvax['header_gps_seconds']:
            # print(self.best_gnss_pos, self.inspvax)
            pos_data = {}
            pos_data['GPS_Week'] = self.inspvax['header_gps_week']
            pos_data['GPS_TimeofWeek'] = self.inspvax['header_gps_seconds'] * 0.001
            pos_data['positionMode'] = self.getpostype(self.inspvax['pos_type'])
            pos_data['hdop'] = 1.0
            pos_data['age'] = self.best_gnss_pos['diff_age']
            pos_data['numberOfSVs'] = self.best_gnss_pos['soln_svs']
            pos_data['latitude'] = self.inspvax['lat']
            pos_data['longitude'] = self.inspvax['lon']
            pos_data['height'] = self.inspvax['hgt'] + self.inspvax['undulation']
            pos_data['velocityMode'] = 1
            if pos_data['positionMode'] != 1 and \
                pos_data['positionMode'] != 4 and \
                pos_data['positionMode'] != 5:
                pos_data['velocityMode'] = 2
            pos_data['insStatus'] = self.inspvax['ins_status']
            pos_data['insPositionType'] = pos_data['positionMode']
            pos_data['roll'] = self.inspvax['roll']
            pos_data['pitch'] = self.inspvax['pitch']
            pos_data['velocityNorth'] = self.inspvax['north_velocity']
            pos_data['velocityEast'] = self.inspvax['east_velocity']
            pos_data['velocityUp'] = self.inspvax['up_velocity']
            pos_data['latitude_std'] = self.inspvax['lat_sigma']
            pos_data['longitude_std'] = self.inspvax['lon_sigma']
            pos_data['height_std'] = self.inspvax['hgt_sigma']
            pos_data['north_vel_std'] = self.inspvax['north_velocity_sigma']
            pos_data['east_vel_std'] = self.inspvax['east_velocity_sigma']
            pos_data['up_vel_std'] = self.inspvax['up_velocity_sigma']
            self.add_output_packet('pos', pos_data)


    def output_imu(self, imudata):
        '''output imu'''
        imu_data = {}
        imu_data['GPS_Week'] = imudata['header_gps_week']
        imu_data['GPS_TimeOfWeek'] = imudata['header_gps_seconds'] * 0.001
        imu_data['x_accel'] = imudata['x_accel']
        imu_data['y_accel'] = imudata['y_accel']
        imu_data['z_accel'] = imudata['z_accel']
        imu_data['x_gyro'] = imudata['x_gyro']
        imu_data['y_gyro'] = imudata['y_gyro']
        imu_data['z_gyro'] = imudata['z_gyro']
        self.add_output_packet('imu', imu_data)

    def getpostype(self, position_type):
        """get position type"""
        positions = {
            '16': 1,
            '53': 1,
            '17': 2,
            '54': 2,
            '50': 4,
            '56': 4,
            '55': 5,
            '34': 5,
        }
        return positions.get(str(position_type), 0)


    def output_nmea(self, data):
        if 'GSV' in data:
            self._output_gsv(data)

    def _output_gsv(self, gsv):
        idx = gsv.find('*')
        if idx < 0:
            return
        gsv_arr = gsv[:idx].split(',')
        snr_arr = gsv_arr[4:]
        if len(snr_arr) % 4 != 0:
            return
        sys_tag = gsv_arr[0][1:3]
        sys_tabs = {
            'GP': 0,
            'GL': 1,
            'GA': 2,
            'GQ': 3,
            'BD': 4
        }
        num = int(len(snr_arr) / 4)
        snr = []
        for i in range(num):
            snr.append({
                'GPS_Week': self.gps_week,
                'GPS_TimeOfWeek': int(self.gps_seconds * 0.001),
                'satelliteId': snr_arr[i * 4 + 0],
                'systemId': sys_tabs.get(sys_tag),
                'antennaId': 0,
                'elevation': snr_arr[i * 4 + 1],
                'azimuth': snr_arr[i * 4 + 2],
                'l1cn0': snr_arr[i * 4 + 3],
                'l2cn0': 0
            })

        self.add_output_packet('snr', snr)
        self.add_output_packet('skyview', snr)

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
                {'name': 'Product Name', 'value': 'INS2000'},
                {'name': 'IMU', 'value': ''},
                {'name': 'PN', 'value': ''},
                {'name': 'Firmware Version',
                 'value': ''},
                {'name': 'SN', 'value': ''},
                {'name': 'App Version', 'value': ''}
            ]
        }

    def get_log_info(self):
        '''
        Build information for log
        '''
        return {
        }

    def get_conf(self, *args):  # pylint: disable=unused-argument
        '''
        Get json configuration
        '''
        return {
            'packetType': 'conf',
            'data': {
                'outputs': self.properties['userMessages']['outputPackets'],
                'inputParams': []
            }
        }


    @with_device_message
    def get_params(self, *args):  # pylint: disable=unused-argument
        '''
        Get all parameters
        '''
        parameter_values = []
        yield {
            'packetType': 'inputParams',
            'data': parameter_values
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

        data = result['data']
        error = result['error']

        if error:
            yield {
                'packetType': 'error',
                'data': 'No Response'
            }

        if data:
            self.parameters = data
            yield {
                'packetType': 'inputParam',
                'data': data
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
            # print("Upgrade OpenRTK firmware started at:[{0}].".format(
            #     datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        return {
            'packetType': 'success'
        }
