from abc import ABCMeta, abstractmethod
import os
import sys
import threading
import uuid
import time
import struct
import traceback
from tqdm import tqdm
from pathlib import Path
from azure.storage.blob import BlockBlobService
from .event_base import EventBase
from ...framework.utils import (helper, resource)
from ...framework.file_storage import FileLoger
from ...framework.configuration import get_config
from ...framework.ans_platform_api import AnsPlatformAPI
from ..message_center import DeviceMessageCenter
from ..parser_manager import ParserManager

if sys.version_info[0] > 2:
    from queue import Queue
else:
    from Queue import Queue


class OpenDeviceBase(EventBase):
    '''
    Base class of open device(openimu, openrtk)
    '''
    __metaclass__ = ABCMeta

    def __init__(self, communicator):
        super(OpenDeviceBase, self).__init__()
        self.type = 'None'
        self.threads = []  # thread of receiver and paser
        self.exception_thread = False  # flag of exit threads
        self.exception_lock = threading.Lock()  # lock of exception_thread
        self.exit_thread = False
        self.data_lock = threading.Lock()
        self.clients = []
        self.is_streaming = False
        self.has_running_checker = False
        self.has_backup_checker = False
        self.connected = False  # set True in ping, set False in read exception
        self.is_upgrading = False
        self.complete_upgrade = False
        self.communicator = communicator
        self.bootloader_baudrate = 57600
        self.properties = None
        self.block_blob_service = None
        self._logger = None
        self.is_logging = False
        self.enable_data_log = True
        self.cli_options = None
        self._message_center = None
        self.sessionId = None
        self.ans_platform = AnsPlatformAPI()
        self._pbar = None

    @abstractmethod
    def load_properties(self):
        '''
        load configuration
        '''

    @abstractmethod
    def on_receive_output_packet(self, packet_type, data):
        '''
        Listener for receiving output packet
        '''

    @abstractmethod
    def after_setup(self):
        '''
        Do some operations after setup
        '''

    @abstractmethod
    def after_bootloader_switch(self):
        '''
        Do some opertions after bootloader is switched
        '''

    @abstractmethod
    def do_write_firmware(self, firmware_content):
        '''
        Do firmware upgrade
        '''

    @abstractmethod
    def get_device_info(self, *args):
        '''
        Get device info for connection log
        '''

    @abstractmethod
    def get_device_connection_info(self):
        '''
        Get device connection info, used to store to db
        '''

    def internal_input_command(self, command, read_length=500):
        '''
        Internal input command
        '''
        command_line = helper.build_input_packet(command)
        self.communicator.write(command_line)
        time.sleep(0.1)

        data_buffer = self.read_untils_have_data(command, read_length, 20)
        parsed = bytearray(data_buffer) if data_buffer and len(
            data_buffer) > 0 else None

        format_string = None
        if parsed is not None:
            try:
                if sys.version_info < (3, 0):
                    format_string = str(struct.pack(
                        '{0}B'.format(len(parsed)), *parsed))
                else:
                    format_string = str(struct.pack(
                        '{0}B'.format(len(parsed)), *parsed), 'utf-8')
            except UnicodeDecodeError:
                return ''

        if format_string is not None:
            return format_string
        return ''

    def read_untils_have_data(self, packet_type, read_length=200, retry_times=20):
        '''
        Get data from limit times of read
        '''
        return helper.read_untils_have_data(self.communicator, packet_type, read_length, retry_times)

    def _setup_message_center(self):
        if not self._message_center:
            self._message_center = DeviceMessageCenter(self.communicator)

        if not self._message_center.is_ready():
            parser = ParserManager.build(
                self.type, self.communicator.type, self.properties)
            self._message_center.set_parser(parser)
            self._message_center.on('continuous_message',
                                    self.on_receive_continuous_messsage)
            self._message_center.on('error',
                                    self.on_recevie_message_center_error)
            self._message_center.on('read_block',
                                    self.on_read_raw)
            self._message_center.setup()
        else:
            self._message_center.get_parser().set_configuration(self.properties)
            self._message_center.setup()

    def setup(self, options):
        ''' start 2 threads, receiver, parser
        '''
        self.load_properties()
        self._logger = FileLoger(self.properties)
        self.cli_options = options

        with_data_log = options and options.with_data_log

        self._setup_message_center()

        if with_data_log and not self.is_logging and self.enable_data_log:
            log_result = self._logger.start_user_log('data')
            if log_result == 1 or log_result == 2:
                raise Exception('Cannot start data logger')
            self.is_logging = True

        self.after_setup()

        self.sessionId = str(uuid.uuid1())

    def on_recevie_message_center_error(self, error_type, message):
        '''
        event handler after got message center error
        '''
        self.connected = False
        self.emit('exception', error_type, message)

    def on_receive_continuous_messsage(self, packet_type, data):
        '''
        event handler after got continuous message
        '''
        if isinstance(data, list):
            for item in data:
                self._logger.append(packet_type, item)
        else:
            self._logger.append(packet_type, data)

        self.on_receive_output_packet(packet_type, data)

    @abstractmethod
    def on_read_raw(self, data):
        '''
        Trigger when read raw data
        '''

    def get_command_lines(self):
        '''
        Get command line defines
        '''
        if self.properties.__contains__('CLICommands'):
            return self.properties['CLICommands']
        return []

    def add_output_packet(self, method, packet_type, data):
        '''
        Add output packet
        '''
        for client in self.clients:
            client.on_receive_output_packet(method, packet_type, data)

    def append_client(self, client):
        '''
        Append client connection, cache it
        '''
        self.clients.append(client)

    def remove_client(self, client):
        '''
        Remove specified client
        '''
        self._reset_client()
        self.clients.remove(client)

    def _reset_client(self):
        self.is_streaming = False
        self.is_upgrading = False

        self._message_center.resume()

        if self._logger is not None:
            self._logger.stop_user_log()
            self.is_logging = False

    def reset(self):
        '''
        Reset
        '''
        self._reset_client()
        # self.threads.clear()
        helper.clear_elements(self.threads)
        self.listeners.clear()
        # self.clients.clear()
        self.exception_thread = False
        # self.data_queue.queue.clear()

    def close(self):
        '''
        Close and disconnect
        '''
        helper.clear_elements(self.clients)
        self.reset()
        self._message_center.stop()
        self._message_center = None
        self.exit_thread = True

    def restart(self):
        '''
        Restart device
        '''
        # output firmware upgrade finished
        time.sleep(1)
        command_line = helper.build_bootloader_input_packet('JA')
        self.communicator.write(command_line)
        print('Restarting app ...')
        time.sleep(5)

        self.emit('complete_upgrade')

    def thread_do_upgrade_framework(self, file):
        '''
        Do upgrade firmware
        '''
        try:
            # step.1 download firmware
            can_download, firmware_content = self.download_firmware(file)
            if not can_download:
                self.handle_upgrade_error('cannot find firmware file')
                return
            # step.2 jump to bootloader
            if not self.switch_to_bootloader():
                self.handle_upgrade_error('Bootloader Start Failed')
                return
            # step.3 write to block, use self write from specified device
            print('Firmware upgrading...')
            total = self.do_write_firmware(firmware_content)
            self._pbar = tqdm(total=total)
            # self.write_firmware()
            # step.4 restart app
            # self.restart()
        except Exception:  # pylint:disable=broad-except
            self.handle_upgrade_error('Upgrade Failed')
            traceback.print_exc()

    def _do_download_firmware(self, file):
        firmware_content = None

        # try find file directly
        directly_file = Path(file)

        if directly_file.is_file():
            firmware_content = open(directly_file, 'rb').read()
            return firmware_content

        # try find from executor path
        executor_path_file = Path(os.path.join(
            resource.get_executor_path(), file))

        if executor_path_file.is_file():
            firmware_content = open(executor_path_file, 'rb').read()
            return firmware_content

        # at last download from azure
        upgarde_root = os.path.join(resource.get_executor_path(), 'upgrade')

        if not os.path.exists(upgarde_root):
            os.makedirs(upgarde_root)

        del_list = os.listdir(upgarde_root)
        for f in del_list:
            file_path = os.path.join(upgarde_root, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

        firmware_file_path = os.path.join(upgarde_root, file)
        firmware_file = Path(firmware_file_path)

        config = get_config()

        if firmware_file.is_file():
            firmware_content = open(firmware_file_path, 'rb').read()
        else:
            self.block_blob_service = BlockBlobService(
                account_name=config.AZURE_STORAGE_ACCOUNT, protocol='https')
            self.block_blob_service.get_blob_to_path(
                config.AZURE_STORAGE_APPS_CONTAINER, file, firmware_file_path)
            firmware_content = open(firmware_file_path, 'rb').read()

        return firmware_content

    def download_firmware(self, file):
        '''
        Downlaod firmware from Azure storage
        '''
        can_download = False
        firmware_content = None
        try:
            firmware_content = self._do_download_firmware(file)
            can_download = True
        except Exception:  # pylint:disable=broad-except
            can_download = False

        return can_download, firmware_content

    def switch_to_bootloader(self):
        '''
        Switch to bootloader
        '''
        try:
            # TODO: should send set quiet command before go to bootloader mode
            command_line = helper.build_bootloader_input_packet('JI')
            self.communicator.reset_buffer()  # clear input and output buffer
            self.communicator.write(command_line, True)
            time.sleep(3)
            # It is used to skip streaming data with size 1000 per read
            self.read_untils_have_data('JI', 1000, 50)
            # A hook after bootloader is switched
            self.after_bootloader_switch()
            return True
        except Exception as ex:  # pylint:disable=broad-except
            print('bootloader exception', ex)
            return False

    def upgrade_completed(self, options):
        '''
        Actions after upgrade complete
        '''
        # self.data_queue.queue.clear()
        self.is_upgrading = False

        self.load_properties()
        self._logger = FileLoger(self.properties)
        self.cli_options = options

        self._message_center.get_parser().set_configuration(self.properties)
        self._message_center.resume()

        with_data_log = options and options.with_data_log

        if with_data_log and not self.is_logging and self.enable_data_log:
            log_result = self._logger.start_user_log('data')
            if log_result == 1 or log_result == 2:
                raise Exception('Cannot start data logger')
            self.is_logging = True

    def start_data_log(self):
        '''
        Start to log
        '''
        if self.is_logging:
            return False

        if self._logger is None:
            self._logger = FileLoger(self.properties)

        log_result = self._logger.start_user_log('data')
        if log_result == 1 or log_result == 2:
            raise Exception('Cannot start data logger')
        self.is_logging = True

    def stop_data_log(self):
        '''
        Stop logging
        '''
        if self.is_logging and not self._logger:
            self._logger.stop_user_log()
            self.is_logging = False

    def handle_upgrade_error(self, message):
        '''
        Linstener for upgrade failure
        '''
        print('Upgrade failed')
        if self._pbar:
            self._pbar.close()
        self.is_upgrading = False
        self._message_center.resume()
        self.add_output_packet(
            'stream', 'upgrade_complete', {'success': False, 'message': message})

    def handle_upgrade_process(self, step, current, total):
        if self._pbar:
            self._pbar.update(step)
        self.add_output_packet('stream', 'upgrade_progress', {
            'addr': current,
            'fs_len': total
        })

    def handle_upgrade_complete(self):
        if self._pbar:
            self._pbar.close()
        self.restart()

    def connect_log(self, params):
        if resource.is_dev_mode():
            return {
                'packetType': 'success'
            }

        access_token = params['token']
        device_info = self.get_device_connection_info()

        self.ans_platform.set_access_token(access_token)
        self.ans_platform.log_device_connection(
            sessionId=self.sessionId,
            device_info=device_info)

        return {
            'packetType': 'success'
        }
