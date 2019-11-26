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
        self.server_update_rate = 100
        self.communicator = communicator
        self.is_streaming = False
        pass

    def ping(self):
        device_info_text = self.internal_input_command('pG')
        app_info_text = self.internal_input_command('gV')

        print(device_info_text)
        print(app_info_text)

        self.build_device_info(device_info_text)
        self.build_app_info(app_info_text)

        if device_info_text.find('OpenRTK') > -1:
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

        if not os.path.exists(self.app_config_folder):
            print('downloading config json files from github, please waiting for a while')
            os.makedirs(self.app_config_folder)

            filepath = self.app_config_folder + '/' + json_file_name

            try:
                r = requests.get(url)
                with open(filepath, "wb") as code:
                    code.write(r.content)
            except Exception as e:
                print(e)

        # Load the basic openimu.json(IMU application)
        with open(os.path.join(self.app_config_folder, json_file_name)) as json_data:
            self.properties = json.load(json_data)

        # TODO: maybe we need a base config file
        pass

    def on_receive_output_packet(self, packet_type, data, error=None):
        if packet_type == 'NV':
            self.add_output_packet('stream', 'pos', data)

        if packet_type == 'SA':
            self.add_output_packet('stream', 'snr', data)

        if packet_type == 'SK':
            self.add_output_packet('stream', 'skyview', data)

    def on_receive_input_packet(self, packet_type, data, error):
        self.input_result = {'packet_type': packet_type,
                             'data': data, 'error': error}

    # command list
    def serverStatus(self, *args):
        return {
            'packetType': 'ping',
            'data': '1'
        }

    def getDeviceInfo(self, *args):
        return {
            'packetType': 'deviceInfo',
            'data': [
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
        pass

    def getConf(self, *args):
        pass

    def startStream(self):
        self.is_streaming = True
        self.response('startStream',  'success')
        self.notify_client('startStream')

    def stopStream(self):
        self.is_streaming = False
        self.response('stopStream', 'success')
        self.notify_client('stopStream')

    def startLog(self, *args):
        pass

    def stopLog(self, *args):
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
