import os
import collections
import requests
import time
import struct
import json
from ...framework.utils import helper
from ..base.uart_base import OpenDeviceBase
from ..configs.openrtk_predefine import *
import asyncio
import datetime


class Provider(OpenDeviceBase):
    def __init__(self, communicator):
        super().__init__(communicator)
        self.type = 'RTK'
        self.server_update_rate = 100
        self.sky_data = []
        pass

    def ping(self):
        print('start to check if it is openrtk')
        device_info_text = self.internal_input_command('pG')
        app_info_text = self.internal_input_command('gV')

        if device_info_text.find('OpenRTK') > -1:
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
        self.app_info = {
            'version': text
        }

    def load_properties(self):
        self.app_config_folder = os.path.join(
            os.getcwd(), 'setting', 'openrtk')

        with open(os.path.join(self.app_config_folder, json_file_name)) as json_data:
            self.properties = json.load(json_data)

        # TODO: maybe we need a base config file
        pass
    
    def on_receive_output_packet(self, packet_type, data, error=None):
        if packet_type == 'pS':
            self.add_output_packet('stream', 'pos', data)

        if packet_type == 'sK':
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

    def on_receive_input_packet(self, packet_type, data, error):
        self.input_result = {'packet_type': packet_type,
                             'data': data, 'error': error}

    def on_receive_bootloader_packet(self, packt_type, data, error):
        pass

    def get_log_info(self):
        pass

    def restart(self):
        pass

    # command list
    def serverStatus(self, *args):
        return {
            'packetType': 'ping',
            'data': {'status': '1'}
        }

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

    def get_log_info(self):
        return {
            "type": self.type,
            "model": self.device_info['name'],
            "logInfo": {
                "pn": self.device_info['pn'],
                "sn": self.device_info['sn'],
                "rtkProperties": json.dumps(self.properties)
            }
        }

    def getConf(self, *args):
        pass

    def getParams(self, *args):
        pass

    def setParameters(self, params, *args):
        pass

    def get_parameter(self, name, *args):
        pass

    def setParam(self, params, *args):
        pass

    def saveConfig(self, *args):
        pass

    def upgrade(self):
        pass
