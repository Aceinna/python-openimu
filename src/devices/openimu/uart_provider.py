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
        self.server_update_rate = 50
        self.communicator = communicator
        self.is_streaming = False
        self.clients = []
        self.input_result = None
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
        self.input_result = {'packet_type': packet_type, 'data': data}

    def get_input_result(self, packet_type, timeout=1):
        result = None
        start_time = datetime.datetime.now()
        while self.input_result is None:
            end_time = datetime.datetime.now()
            span = end_time - start_time
            if span.total_seconds() > timeout:
                break

        if self.input_result is not None and self.input_result['packet_type'] == packet_type:
            result = self.input_result['data'].copy()
            self.input_result = None

        return result

    # command list

    def getDeviceInfo(self, *args):
        self.response('getDeviceInfo',  'deviceInfo',
                      [
                          {'name': 'Product Name',
                              'value': self.device_info['name']},
                          {'name': 'PN', 'value': self.device_info['pn']},
                          {'name': 'Firmware Version',
                           'value': self.device_info['firmware_version']},
                          {'name': 'SN', 'value': self.device_info['sn']},
                          {'name': 'App Version',
                              'value': self.app_info['version']}
                      ])
        pass

    def getConf(self, *args):
        self.response('getConf', 'conf', self.properties)
        pass

    def startStream(self, *args):
        self.is_streaming = True
        self.response('startStream',  'success')

    def stopStream(self, *args):
        self.is_streaming = False
        self.response('stopStream', 'success')

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
        data = self.get_input_result('gA', timeout=1)
        print(data)
        if data:
            self.response('getParams', 'inputParams', data)
        else:
            self.response_error('getParams', 'No Response')

    def setParameters(self, params, *args):
        pass

    def get_parameter(self, name, *args):
        pass

    def set_parameter(self, id, value, *args):
        pass

    def saveConfig(self, *args):
        command_line = helper.build_input_packet('sC')
        self.communicator.write(command_line)

        data = self.get_input_result('sC', timeout=1)

        if data:
            self.response('saveConfig', 'success')
        else:
            self.response_error('saveConfig', 'Operation Failed')
        pass

    def upgrade(self):
        pass

    def on(self, data_type, callback):
        pass

    def response(self, method, packet_type, data):
        for client in self.clients:
            client.response_message(method, {
                'packetType': packet_type,
                'data': data
            })
        pass

    def response_error(self, method, message):
        for client in self.clients:
            client.response_message(method, {
                'packetType': 'error',
                'data': message
            })
        pass
