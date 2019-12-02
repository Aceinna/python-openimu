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
from pathlib import Path
from azure.storage.blob import BlockBlobService
import threading
import traceback


class Provider(OpenDeviceBase):
    def __init__(self, communicator):
        super().__init__(communicator)
        self.type = 'IMU'
        self.server_update_rate = 50
        self.is_logging = False
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
        self.device_info = {
            'name': split_text[0],
            'pn': split_text[1],
            'firmware_version': split_text[2],
            'sn': split_text[3].split(':')[1] if split_len == 4 else '' 
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

    def on_receive_bootloader_packet(self, packet_type, data, error):
        print('bootloader', packet_type)
        self.bootloader_result = {'packet_type': packet_type,
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
        else:
            result['data'] = 'Command timeout'
            result['error'] = True

        return result

    def get_bootloader_result(self, packet_type, timeout=1):
        result = {'data': None, 'error': None}
        start_time = datetime.datetime.now()
        while self.bootloader_result is None:
            end_time = datetime.datetime.now()
            span = end_time - start_time
            if span.total_seconds() > timeout:
                break

        if self.bootloader_result is not None and self.bootloader_result['packet_type'] == packet_type:
            result = self.bootloader_result.copy()
            self.bootloader_result = None
        else:
            result['data'] = 'Command timeout'
            result['error'] = True

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

    def on_upgarde_failed(self, message):
        print(message)
        self.is_upgrading = False
        self.add_output_packet(
            'stream', 'upgrade_complete', {'success': False, 'message': message})
        pass

    def upgradeFramework(self, file, *args):
        # start a thread to do upgrade
        if not self.is_upgrading:
            self.is_upgrading = True
            t = threading.Thread(
                target=self.thread_do_upgrade_framework, args=(file,))
            t.start()
            print("Thread upgarde framework start at:[{0}].".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        return {
            'packetType': 'success'
        }

    def thread_do_upgrade_framework(self, file):
        try:
            # step.1 download firmware
            if not self.download_firmware(file):
                self.on_upgarde_failed('cannot find firmware file')
                return
            # step.2 jump to bootloader
            if not self.start_bootloader():
                self.on_upgarde_failed('Bootloader Start Failed')
                return
            # step.3 write to block
            self.write_firmware()
            # step.4 restart app
            self.restart()
        except Exception as e:
            self.on_upgarde_failed('Upgrade Failed')
            traceback.print_exc()

    def download_firmware(self, file):
        firmware_file = Path(file)

        if firmware_file.is_file():
            self.fw = open(file, 'rb').read()
        else:
            self.block_blob_service = BlockBlobService(account_name='navview',
                                                       account_key='+roYuNmQbtLvq2Tn227ELmb6s1hzavh0qVQwhLORkUpM0DN7gxFc4j+DF/rEla1EsTN2goHEA1J92moOM/lfxg==',
                                                       protocol='http')
            self.block_blob_service.get_blob_to_path('apps', file, file)
            self.fw = open(file, 'rb').read()

        print('upgrade fw: %s' % file)
        self.max_data_len = 240
        self.addr = 0
        self.fs_len = len(self.fw)
        return True

    def start_bootloader(self):
        try:
            command_line = helper.build_bootloader_input_packet('JI')
            self.communicator.write(command_line)
            time.sleep(2)
            data_buffer = self.communicator.read(500)
            parsed = self.extract_command_response('JI', data_buffer)
            print('parsed', parsed)
            self.communicator.serial_port.baudrate = 57600
            #print('JI response', result)
            return True
        except Exception as e:
            print('bootloader exception', e)
            return False

    def write_firmware(self):
        '''Upgrades firmware of connected device to file provided in argument
        '''
        while self.addr < self.fs_len:
            packet_data_len = self.max_data_len if (
                self.fs_len - self.addr) > self.max_data_len else (self.fs_len - self.addr)
            data = self.fw[self.addr: (self.addr + packet_data_len)]
            self.write_block(packet_data_len, self.addr, data)
            self.addr += packet_data_len
            self.add_output_packet('stream', 'upgrade_progress', {
                                   'addr': self.addr,
                                   'fs_len': self.fs_len
                                   })
            # output firmware upgrading

    def write_block(self, data_len, addr, data):
        print(data_len, addr)
        command_line = helper.build_bootloader_input_packet(
            'WA', None, data_len, addr, data)
        try:
            self.communicator.write(command_line)
        except Exception as e:
            self.exception_lock.acquire()
            self.exception_thread = True
            self.exception_lock.release()
            return

        if addr == 0:
            time.sleep(5)
        else:
            time.sleep(0.1)
        # self.get_bootloader_result('WA', timeout=1)
