import os
import collections
import requests
import time
import struct
import json
from ...framework.utils import helper
from ..base.uart_base import OpenDeviceBase
from ..configs.openimu_predefine import *
import asyncio
import datetime


class Provider(OpenDeviceBase):
    def __init__(self, communicator):
        super().__init__()
        self.type = 'IMU'
        self.server_update_rate = 50
        self.communicator = communicator
        self.is_logging = False
        pass

    def ping(self):
        print('start to check if it is openimu')
        device_info_text = self.internal_input_command('pG')
        app_info_text = self.internal_input_command('gV')

        if device_info_text.find('OpenIMU') > -1:
            self.build_device_info(device_info_text)
            self.build_app_info(app_info_text)
            self.connected = True
            return True
        return False

    def build_device_info(self, text):
        split_text = text.split(' ')
        self.device_info = {
            'name': split_text[0],
            'pn': split_text[1],
            'firmware_version': split_text[2],
            'sn': split_text[3]
        }

    def build_app_info(self, text):
        split_text = text.split(' ')

        app_name = next((item for item in app_str if item in split_text), 'IMU')

        self.app_info = {
            'app_name': app_name,
            'version': split_text
        }

    def load_properties(self):
        self.app_config_folder = os.path.join(
            os.getcwd(), 'setting', 'openimu')

        if not os.path.exists(self.app_config_folder):
            print('downloading config json files from github, please waiting for a while')
            os.makedirs(self.app_config_folder)
            for app_name in get_app_names():
                os.makedirs(self.app_config_folder + '/' + app_name)
            i = 0
            for url in get_app_urls():
                filepath = self.app_config_folder + '/' + \
                    get_app_names()[i] + '/' + 'openimu.json'
                i = i+1
                try:
                    r = requests.get(url)
                    with open(filepath, "wb") as code:
                        code.write(r.content)
                except Exception as e:
                    print(e)

        # Load the openimu.json based on its app
        app_name = self.app_info['app_name']
        with open(os.path.join(self.app_config_folder, app_name, 'openimu.json')) as json_data:
            self.properties = json.load(json_data)
        pass

    def on_receive_output_packet(self, packet_type, data, error=None):

        self.add_output_packet('stream', packet_type, data)

    def on_receive_input_packet(self, packet_type, data, error):
        self.input_result = {'packet_type': packet_type,
                             'data': data, 'error': error}

    def get_input_result(self, packet_type, timeout=1):
        result = {'data': None, 'error': None}
        start_time = datetime.datetime.now()
        while self.input_result is None:
            end_time = datetime.datetime.now()
            span = end_time - start_time
            if span.total_seconds() > timeout:
                break

        if self.input_result is not None and self.input_result['packet_type'] == packet_type:
            result = self.input_result.copy()
            self.input_result = None

        return {
            'data': result['data'],
            'error': result['error']
        }

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
        pass
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
        result = self.get_input_result('gA', timeout=1)

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

    def setParameters(self, params, *args):
        pass

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

    def startMagAlign(self):
        pass

    def stopMagAlign(self):
        pass

    def upgradeFramework(self):
        # start a thread to do upgrade
        command_line = helper.build_bootloader_packet(
            'uP', properties=self.properties, param=params['paramId'], value=params['value'])
        self.communicator.write(command_line)

        return {
            'packetType': 'success'
        }
