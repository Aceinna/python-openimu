import os
import time
import json
import binascii
import math
#import asyncio
import datetime
import threading
from ...framework.utils import helper
from ...framework.utils import resource
from ..base.uart_base import OpenDeviceBase
from ..configs.openimu_predefine import (
    APP_STR, get_app_names
)


class Provider(OpenDeviceBase):
    '''
    OpenIMU UART provider
    '''

    def __init__(self, communicator):
        super(Provider, self).__init__(communicator)
        self.type = 'IMU'
        self.server_update_rate = 50
        self.is_logging = False
        self.is_mag_align = False
        self.bootloader_baudrate = 57600
        self.device_info = None
        self.app_info = None
        self.app_config_folder = ''
        self.parameters = None
        self.enable_data_log = False
        self.prepare_folders()

    def prepare_folders(self):
        '''
        Prepare folders for data storage and configuration
        '''
        executor_path = resource.get_executor_path()
        setting_folder_name = 'setting'
        config_file_name = 'openimu.json'
        data_folder_path = os.path.join(executor_path, 'data')
        if not os.path.isdir(data_folder_path):
            os.makedirs(data_folder_path)

        # copy contents of app_config under executor path
        self.setting_folder_path = os.path.join(
            executor_path, setting_folder_name, 'openimu')

        for app_name in get_app_names():
            app_name_path = os.path.join(self.setting_folder_path, app_name)
            app_name_config_path = os.path.join(
                app_name_path, config_file_name)
            if not os.path.isfile(app_name_config_path):
                if not os.path.isdir(app_name_path):
                    os.makedirs(app_name_path)
                app_config_content = resource.get_content_from_bundle(
                    setting_folder_name, os.path.join('openimu', app_name, config_file_name))
                if app_config_content is None:
                    continue

                with open(app_name_config_path, "wb") as code:
                    code.write(app_config_content)

    def ping(self):
        '''
        Check if the connected device is OpenIMU
        '''
        # print('start to check if it is openimu')
        device_info_text = self.internal_input_command('pG')
        app_info_text = self.internal_input_command('gV')

        if device_info_text.find('OpenIMU') > -1 and \
                device_info_text.find('OpenRTK') == -1:
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
        split_len = len(split_text)
        pre_sn = split_text[3].split(':') if split_len == 4 else ''
        serial_num = pre_sn[1] if len(pre_sn) == 2 else ''
        self.device_info = {
            'name': split_text[0],
            'pn': split_text[1],
            'firmware_version': split_text[2],
            'sn': serial_num
        }

    def build_app_info(self, text):
        '''
        Build app info
        '''
        split_text = text.split(' ')
        app_name = next(
            (item for item in APP_STR if item in split_text), 'IMU')

        self.app_info = {
            'app_name': app_name,
            'version': text
        }

    def load_properties(self):
        # Load config from user working path
        local_config_file_path = os.path.join(os.getcwd(), 'openimu.json')
        if os.path.isfile(local_config_file_path):
            with open(local_config_file_path) as json_data:
                self.properties = json.load(json_data)
                return

        # Load the openimu.json based on its app
        app_name = self.app_info['app_name']
        app_file_path = os.path.join(
            self.setting_folder_path, app_name, 'openimu.json')

        with open(app_file_path) as json_data:
            self.properties = json.load(json_data)

    def after_setup(self):
        pass

    def on_read_raw(self, data):
        pass

    def on_receive_output_packet(self, packet_type, data):
        '''
        Listener for getting output packet
        '''
        self.add_output_packet('stream', packet_type, data)

    def on_receive_input_packet(self, packet_type, data, error):
        '''
        Listener for getting input command packet
        '''
        #print('input packet', packet_type, data)
        self.input_result = {'packet_type': packet_type,
                             'data': data, 'error': error}

    def on_receive_bootloader_packet(self, packet_type, data, error):
        '''
        Listener for getting bootloader command packet
        '''
        print('bootloader', packet_type, data)
        self.bootloader_result = {'packet_type': packet_type,
                                  'data': data, 'error': error}

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
        #           span.total_seconds() if span else 0, 's')

        if self.input_result is not None and self.input_result['packet_type'] == packet_type:
            result = self.input_result.copy()
        else:
            result['data'] = 'Command timeout'
            result['error'] = True

        self.input_result = None

        return result

    def get_bootloader_result(self, packet_type, timeout=1):
        '''
        Get bootloader result
        '''
        result = {'data': None, 'error': None}
        start_time = datetime.datetime.now()
        end_time = datetime.datetime.now()
        span = None

        while self.bootloader_result is None:
            end_time = datetime.datetime.now()
            span = end_time - start_time
            if span.total_seconds() > timeout:
                break

        if self.bootloader_result:
            print('get bootloader packet in:',
                  span.total_seconds() if span else 0, 's')

        if self.bootloader_result is not None and \
           self.bootloader_result['packet_type'] == packet_type:
            result = self.bootloader_result.copy()
        else:
            result['data'] = 'Command timeout'
            result['error'] = True

        self.bootloader_result = None

        return result

    def get_log_info(self):
        '''
        Build information for log
        '''
        packet_rate = next(
            (item['value'] for item in self.parameters if item['name'] == 'Packet Rate'), '100')
        return {
            "type": self.type,
            "model": self.device_info['name'],
            "logInfo": {
                "pn": self.device_info['pn'],
                "sn": self.device_info['sn'],
                "sampleRate": packet_rate,
                "appVersion": self.app_info['version'],
                "imuProperties": json.dumps(self.properties)
            }
        }

    # command list
    def get_device_info(self, *args):  # pylint: disable=invalid-name
        '''
        Get device information
        '''
        return {
            'packetType': 'deviceInfo',
            'data':  [
                {'name': 'Product Name',
                 'value': self.device_info['name']},
                {'name': 'PN', 'value': self.device_info['pn']},
                {'name': 'Firmware Version',
                 'value': self.device_info['firmware_version']},
                {'name': 'SN', 'value': self.device_info['sn']},
                {'name': 'App Version', 'value': self.app_info['version']}
            ]
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

        result = self.get_input_result('sC', timeout=1)

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

    def mag_align_start(self, *args):  # pylint: disable=invalid-name
        '''
        Start mag align action
        '''
        if not self.is_mag_align:
            self.is_mag_align = True

            thread = threading.Thread(
                target=self.thread_do_mag_align, args=())
            thread.start()
            print("Thread mag align start at:[{0}].".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        return {
            'packetType': 'success'
        }

    def thread_do_mag_align(self):
        '''
        Do mag align
        '''
        try:
            command_line = helper.build_input_packet(
                'ma', self.properties, 'start')
            self.communicator.write(command_line)
            result = self.get_input_result('ma', timeout=3)

            time.sleep(1)
            has_result = False
            while not has_result and self.is_mag_align:
                command_line = helper.build_input_packet(
                    'ma', self.properties, 'status')
                self.communicator.write(command_line)
                print('ma status', command_line)
                result = self.get_input_result('ma', timeout=1)
                if result['data'] == b'\x00':
                    has_result = True
                else:
                    time.sleep(0.5)

            command_line = helper.build_input_packet(
                'ma', self.properties, 'stored')
            self.communicator.write(command_line)
            result = self.get_input_result('ma', timeout=2)

            decoded_status = binascii.hexlify(result['data'])
            mag_value = self.decode_mag_align_output(decoded_status)
            self.is_mag_align = False

            self.add_output_packet('stream', 'mag_status', {
                'status': 'complete',
                'value': mag_value
            })
        except Exception:  # pylint: disable=broad-except
            self.is_mag_align = False
            self.add_output_packet('stream', 'mag_status', {
                'status': 'error'
            })

    def mag_align_abort(self, *args):  # pylint: disable=invalid-name
        '''
        Abort mag align action
        '''
        self.is_mag_align = False
        command_line = helper.build_input_packet(
            'ma', self.properties, 'abort')
        self.communicator.write(command_line)
        result = self.get_input_result('ma', timeout=1)

        if result['error']:
            return {
                'packetType': 'error',
                'data': {
                    'error': 1
                }
            }
        else:
            return {
                'packetType': 'success'
            }

    def mag_align_save(self, *args):  # pylint: disable=invalid-name
        '''
        Save mag align resut
        '''
        command_line = helper.build_input_packet(
            'ma', self.properties, 'save')
        self.communicator.write(command_line)
        result = self.get_input_result('ma', timeout=1)

        if result['error']:
            return {
                'packetType': 'error',
                'data': {
                    'error': 1
                }
            }
        else:
            return {
                'packetType': 'success'
            }

    def decode_mag_align_output(self, value):
        '''
        decode mag align output
        '''
        hard_iron_x = dict()
        hard_iron_y = dict()
        soft_iron_ratio = dict()
        soft_iron_angle = dict()

        hard_iron_x['value'] = self.hard_iron_cal(value[16:20], 'axis')
        hard_iron_x['name'] = 'Hard Iron X'
        hard_iron_x['argument'] = 'hard_iron_x'

        hard_iron_y['value'] = self.hard_iron_cal(value[20:24], 'axis')
        hard_iron_y['name'] = 'Hard Iron Y'
        hard_iron_y['argument'] = 'hard_iron_y'

        soft_iron_ratio['value'] = self.hard_iron_cal(value[24:28], 'ratio')
        soft_iron_ratio['name'] = 'Soft Iron Ratio'
        soft_iron_ratio['argument'] = 'soft_iron_ratio'

        soft_iron_angle['value'] = self.hard_iron_cal(value[28:32], 'angle')
        soft_iron_angle['name'] = 'Soft Iron Angle'
        soft_iron_angle['argument'] = 'soft_iron_angle'

        output = [hard_iron_x, hard_iron_y, soft_iron_ratio, soft_iron_angle]

        return output

    def hard_iron_cal(self, value, data_type):
        '''
        convert hard iron value
        '''
        decoded_value = int(value, 16)
        # print (decodedValue)
        if data_type == 'axis':
            if decoded_value > 2 ** 15:
                new_decoded_value = (decoded_value - 2 ** 16)
                return new_decoded_value / float(2 ** 15) * 8
            else:
                return decoded_value / float(2 ** 15) * 8

        if data_type == 'ratio':
            return decoded_value / float(2 ** 16 - 1)

        if data_type == 'angle':
            if decoded_value > 2 ** 15:
                decoded_value = decoded_value - 2 ** 16
                pi_value = 2 ** 15 / math.pi
                return decoded_value / pi_value

            pi_value = 2 ** 15 / math.pi
            return decoded_value / pi_value

    def upgrade_framework(self, file, *args):  # pylint: disable=invalid-name
        '''
        upgrade framework
        '''
        # start a thread to do upgrade
        if not self.is_upgrading:
            self.is_upgrading = True

            if self._logger is not None:
                self._logger.stop_user_log()

            thead = threading.Thread(
                target=self.thread_do_upgrade_framework, args=(file,))
            thead.start()
            print("Thread upgarde framework OpenIMU start at:[{0}].".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        return {
            'packetType': 'success'
        }
