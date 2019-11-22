import os
import collections
import requests
import time
import struct
import json
from ...framework.utils import helper
from ..base.uart_base import OpenDeviceBase
from ..configs.openimu_predefine import *


class Provider(OpenDeviceBase):
    def __init__(self, communicator):
        super().__init__()
        self.communicator = communicator
        self.is_streaming = False
        self.clients = []
        pass

    def ping(self):
        device_info_text = self.internal_input_command('pG')
        app_info_text = self.internal_input_command('gV')

        print(device_info_text)
        print(app_info_text)

        self.build_device_info(device_info_text)
        self.build_app_info(app_info_text)

        if device_info_text.find('OpenIMU') > -1:
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
        self.app_info = {
            'app_name': split_text[1],
            'version': split_text[2]
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

        # Load the basic openimu.json(IMU application)
        app_name = self.app_info['app_name']
        with open(os.path.join(self.app_config_folder, app_name, 'openimu.json')) as json_data:
            self.properties = json.load(json_data)

        # TODO: read app id, then load specified json
        pass

    def append_client(self, client):
        self.clients.append(client)

    def remove_client(self, client):
        self.clients.remove(client)

    def on_receive_output_packet(self, packet_type, data, error):
        if self.is_streaming:
            self.response('stream', {'packetType': packet_type, 'data': data})
        pass

    def on_receive_input_packet(self, packet_type, data, error):
        # self.response(data)
        if packet_type == 'gA':
            self.response('getParams', {
                'packetType': 'inputParams',
                'data': data
            })
        if packet_type == 'sC':
            self.response('getParams', {
                'packetType': 'inputParams',
                'data': data
            })

    # command list
    def serverStatus(self, *args):
        self.response('serverStatus', {
                      'packetType': 'ping', 'data': {'status': '1'}})
        pass

    def getDeviceInfo(self, *args):
        self.response('getDeviceInfo', {
            'packetType': 'deviceInfo',
            'data': [
                {'name': 'Product Name', 'value': self.device_info.name},
                {'name': 'PN', 'value': self.device_info.pn},
                {'name': 'Firmware Version',
                    'value': self.device_info.firmware_version},
                {'name': 'SN', 'value': self.device_info.sn},
                {'name': 'App Version', 'value': self.app_info.version}
            ]
        })
        pass

    def startStream(self, *args):
        self.is_streaming = True
        self.response('startStream', {'packetType': 'success'})

    def stopStream(self, *args):
        self.is_streaming = False
        self.response('startStream', {'packetType': 'success'})

    def startLog(self, *args):
        # start log
        self.response()
        pass

    def stopLog(self, *args):
        self.response()
        pass

    def getParams(self, *args):
        command_line = helper.build_input_packet('gA')
        self.communicator.write(command_line)
        pass

    def set_parameters(self, params, *args):
        pass

    def get_parameter(self, name, *args):
        pass

    def set_parameter(self, id, value, *args):
        pass

    def saveConfig(self, *args):
        command_line = helper.build_input_packet('sC')
        self.communicator.write(command_line)
        pass

    def upgrade(self):
        pass

    def on(self, data_type, callback):
        pass

    def response(self, method, data):
        for client in self.clients:
            client.response_message(method, data)
        pass
