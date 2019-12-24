import os
import collections
import requests
import time
import struct
import json
import binascii
import math
#import asyncio
import datetime
import threading
from ...framework.utils import helper
from ..base.uart_base import OpenDeviceBase
from ..configs.openimu_predefine import *


class Provider(OpenDeviceBase):
    def __init__(self, communicator):
        super(Provider, self).__init__(communicator)
        self.type = 'IMU'
        self.server_update_rate = 50
        self.is_logging = False
        self.is_mag_align = False
        pass

    def ping(self):
        print('start to check if it is openimu')
        device_info_text = self.internal_input_command('pG')
        app_info_text = self.internal_input_command('gV')

        if device_info_text.find('OpenIMU') > -1 and \
                device_info_text.find('OpenRTK') == -1:
            self.build_device_info(device_info_text)
            self.build_app_info(app_info_text)
            self.connected = True
            return True
        return False

    def build_device_info(self, text):
        split_text = text.split(' ')
        split_len = len(split_text)
        pre_sn = split_text[3].split(':') if split_len == 4 else ''
        sn = pre_sn[1] if len(pre_sn) == 2 else ''
        self.device_info = {
            'name': split_text[0],
            'pn': split_text[1],
            'firmware_version': split_text[2],
            'sn': sn
        }

    def build_app_info(self, text):
        split_text = text.split(' ')
        app_name = next(
            (item for item in app_str if item in split_text), 'IMU')

        self.app_info = {
            'app_name': app_name,
            'version': text
        }

    def load_properties(self):
        self.app_config_folder = os.path.join(
            os.getcwd(), 'setting', 'openimu')

        if not os.path.exists(self.app_config_folder):
            os.makedirs(self.app_config_folder)
            for app_name in get_app_names():
                os.makedirs(self.app_config_folder + '/' + app_name)

        # Load the openimu.json based on its app
        app_name = self.app_info['app_name']
        app_file_path = os.path.join(
            self.app_config_folder, app_name, 'openimu.json')

        exist_json_file = os.path.isfile(app_file_path)

        if not exist_json_file:
            try:
                print(
                    'downloading config json files from github, please waiting for a while')
                r = requests.get(app_url_base + '/' +
                                 app_name + '/openimu.json')
                r.raise_for_status()
                r.close()
                with open(app_file_path, "wb") as code:
                    code.write(r.content)
                    exist_json_file = True
            except Exception as e:
                exist_json_file = False
                print(e)
                raise

        if exist_json_file:
            with open(app_file_path) as json_data:
                self.properties = json.load(json_data)

    def on_receive_output_packet(self, packet_type, data, error=None):
        self.add_output_packet('stream', packet_type, data)

    def on_receive_input_packet(self, packet_type, data, error):
        #print('input packet', packet_type, data)
        self.input_result = {'packet_type': packet_type,
                             'data': data, 'error': error}

    def on_receive_bootloader_packet(self, packet_type, data, error):
        print('bootloader', packet_type, data)
        self.bootloader_result = {'packet_type': packet_type,
                                  'data': data, 'error': error}

    def get_input_result(self, packet_type, timeout=1):
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

        if self.bootloader_result is not None and self.bootloader_result['packet_type'] == packet_type:
            result = self.bootloader_result.copy()
        else:
            result['data'] = 'Command timeout'
            result['error'] = True

        self.bootloader_result = None

        return result

    def get_log_info(self):
        packet_rate = next(
            (item['value'] for item in self.parameters if x['name'] == 'Packet Rate'), '100')
        return {
            "type": self.type,
            "model": self.device_info['name'],
            "logInfo": {
                "pn": self.device_info['pn'],
                "sn": self.device_info['sn'],
                "sampleRate": packet_rate,
                "appVersion": self.app_info.version,
                "imuProperties": json.dumps(self.properties)
            }
        }

    def restart(self):
        # output firmware upgrade finished
        '''restart app
        '''
        time.sleep(1)
        command_line = helper.build_bootloader_input_packet('JA')
        self.communicator.write(command_line)
        print('Restarting app ...')
        time.sleep(5)

        self.complete_upgrade = True

    # command list
    def getDeviceInfo(self, *args):
        return {
            'packetType': 'deviceInfo',
            'data':  [
                          {'name': 'Product Name',
                              'value': self.device_info['name']},
                          {'name': 'PN', 'value': self.device_info['pn']},
                          {'name': 'Firmware Version',
                           'value': self.device_info['firmware_version']},
                          {'name': 'SN', 'value': self.device_info['sn']},
                          {'name': 'App Version',
                              'value': self.app_info['version']}
            ]
        }

    def getConf(self, *args):
        return {
            'packetType': 'conf',
            'data': self.properties
        }

    def getParams(self, *args):
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

    def setParams(self, params, *args):
        for parameter in params:
            result = self.setParam(parameter)
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

    def getParameter(self, name, *args):
        pass

    def setParam(self, params, *args):
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

    def saveConfig(self, *args):
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
        pass

    def magAlignStart(self, *args):
        if not self.is_mag_align:
            self.is_mag_align = True

            t = threading.Thread(
                target=self.thread_do_mag_align, args=())
            t.start()
            print("Thread mag align start at:[{0}].".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        return {
            'packetType': 'success'
        }

    def thread_do_mag_align(self):
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
            mag_value = self.decodeOutput(decoded_status)
            self.is_mag_align = False

            self.add_output_packet('stream', 'mag_status', {
                'status': 'complete',
                'value': mag_value
            })
        except Exception as e:
            self.is_mag_align = False
            self.add_output_packet('stream', 'mag_status', {
                'status': 'error'
            })

    def magAlignAbort(self, *args):
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

    def magAlignSave(self, *args):
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

    def decodeOutput(self, value):
        hard_iron_x = dict()
        hard_iron_y = dict()
        soft_iron_ratio = dict()
        soft_iron_angle = dict()

        hard_iron_x['value'] = self.hardIronCal(value[16:20], 'axis')
        hard_iron_x['name'] = 'Hard Iron X'
        hard_iron_x['argument'] = 'hard_iron_x'

        hard_iron_y['value'] = self.hardIronCal(value[20:24], 'axis')
        hard_iron_y['name'] = 'Hard Iron Y'
        hard_iron_y['argument'] = 'hard_iron_y'

        soft_iron_ratio['value'] = self.hardIronCal(value[24:28], 'ratio')
        soft_iron_ratio['name'] = 'Soft Iron Ratio'
        soft_iron_ratio['argument'] = 'soft_iron_ratio'

        soft_iron_angle['value'] = self.hardIronCal(value[28:32], 'angle')
        soft_iron_angle['name'] = 'Soft Iron Angle'
        soft_iron_angle['argument'] = 'soft_iron_angle'

        output = [hard_iron_x, hard_iron_y, soft_iron_ratio, soft_iron_angle]

        return output

    def hardIronCal(self, value, type):
        decodedValue = int(value, 16)
        # print (decodedValue)
        if type == 'axis':
            if decodedValue > 2 ** 15:
                newDecodedValue = (decodedValue - 2 ** 16)
                return newDecodedValue / float(2 ** 15) * 8
            else:
                return decodedValue / float(2 ** 15) * 8

        if type == 'ratio':
            return decodedValue / float(2 ** 16 - 1)

        if type == 'angle':
            if decodedValue > 2 ** 15:
                decodedValue = decodedValue - 2 ** 16
                piValue = 2 ** 15 / math.pi
                return decodedValue / piValue

            piValue = 2 ** 15 / math.pi
            return decodedValue / piValue

    def upgradeFramework(self, file, *args):
        # start a thread to do upgrade
        if not self.is_upgrading:
            self.is_upgrading = True

            if self._logger is not None:
                self._logger.stop_user_log()

            t = threading.Thread(
                target=self.thread_do_upgrade_framework, args=(file,))
            t.start()
            print("Thread upgarde framework OpenIMU start at:[{0}].".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        return {
            'packetType': 'success'
        }
