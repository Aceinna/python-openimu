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
        # print(packet_type, data)
