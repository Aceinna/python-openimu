from abc import ABCMeta, abstractmethod
import os
import sys
import threading
import operator
import collections
import time
import struct
import traceback
from pathlib import Path
from azure.storage.blob import BlockBlobService
from .event_base import EventBase
from ...framework.utils import (helper, resource)
from ...framework.file_storage import FileLoger
from ...framework.configuration import get_config
from ..message_center import DeviceMessageCenter
from ..mssage_parser import UartMessageParser
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
        self.threads = []  # thread of receiver and paser
        self.exception_thread = False  # flag of exit threads
        self.exception_lock = threading.Lock()  # lock of exception_thread
        self.exit_thread = False
        self.data_queue = Queue()  # data container
        self.data_lock = threading.Lock()
        self.clients = []
        self.input_result = None
        self.bootloader_result = None
        self.is_streaming = False
        self.has_running_checker = False
        self.has_backup_checker = False
        self.connected = False
        self.is_upgrading = False
        self.complete_upgrade = False
        self.communicator = communicator
        self.bootloader_baudrate = 57600
        self.properties = None
        self.firmware_content = []
        self.fs_len = 0
        self.addr = 0
        self.max_data_len = 240
        self.block_blob_service = None
        self._logger = None
        self.is_logging = False
        self.enable_data_log = True
        self.cli_options = None
        self._message_center = None

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
        pass

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

    def _extract_command_response(self, command, data_buffer):
        command_0 = ord(command[0])
        command_1 = ord(command[1])
        sync_pattern = collections.deque(4*[0], 4)
        sync_state = 0
        packet_buffer = []
        for new_byte in data_buffer:
            sync_pattern.append(new_byte)
            if list(sync_pattern) == [0x55, 0x55, command_0, command_1]:
                packet_buffer = [command_0, command_1]
                sync_state = 1
            elif sync_state == 1:
                packet_buffer.append(new_byte)
                if len(packet_buffer) == packet_buffer[2] + 5:
                    if packet_buffer[-2:] == helper.calc_crc(packet_buffer[:-2]):
                        data = packet_buffer[3:packet_buffer[2]+3]
                        return data
                    else:
                        sync_state = 0  # CRC did not match

    # may lost data
    def read_untils_have_data(self, packet_type, read_length=200, retry_times=20):
        '''
        Get data from limit times of read
        '''
        response = False
        trys = 0

        while not response and trys < retry_times:
            data_buffer = bytearray(self.communicator.read(read_length))
            if data_buffer:
                # print('data_buffer', data_buffer)
                response = self._extract_command_response(
                    packet_type, data_buffer)
            trys += 1

        # print('read end', time.time(), 'try times', trys, 'response', response)

        return response

    def _setup_message_center(self):
        if not self._message_center:
            self._message_center = DeviceMessageCenter(self.communicator)

        if not self._message_center.is_ready():
            uart_parser = UartMessageParser(self.properties)
            self._message_center.set_parser(uart_parser)
            self._message_center.on(
                'continuous_message', self.on_receive_continuous_messsage)
            self._message_center.on(
                'error', self.on_recevie_message_center_error
            )
            self._message_center.on(
                'read_block', self.on_read_raw
            )
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
        with_raw_log = options and options.with_raw_log

        self._setup_message_center()

        if with_data_log and not self.is_logging and self.enable_data_log:
            log_result = self._logger.start_user_log('data')
            if log_result == 1 or log_result == 2:
                raise Exception('Cannot start data logger')
            self.is_logging = True

        if with_raw_log:
            self.after_setup()

        # Backup mode checker
        # if not self.has_backup_checker:
        #     thread = threading.Thread(
        #         target=self.thread_backup_checker, args=())
        #     thread.start()
        #     self.has_backup_checker = True

    def on_recevie_message_center_error(self, error_type, message):
        '''
        event handler after got message center error
        '''
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
        pass

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
        self.input_result = None
        self.bootloader_result = None
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
        self.data_queue.queue.clear()

    def close(self):
        '''
        Close and disconnect
        '''
        self.reset()
        self._message_center.stop()
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
            if not self.download_firmware(file):
                self.on_upgarde_failed('cannot find firmware file')
                return
            # step.2 jump to bootloader
            if not self.start_bootloader():
                self.on_upgarde_failed('Bootloader Start Failed')
                return
            # step.3 write to block
            print('Firmware upgrading...')
            self.write_firmware()
            # step.4 restart app
            self.restart()
        except Exception:  # pylint:disable=broad-except
            self.on_upgarde_failed('Upgrade Failed')
            traceback.print_exc()

    def download_firmware(self, file):
        '''
        Downlaod firmware from Azure storage
        '''
        upgarde_root = os.path.join(resource.get_executor_path(), 'upgrade')

        if not os.path.exists(upgarde_root):
            os.makedirs(upgarde_root)

        firmware_file_path = os.path.join(upgarde_root, file)
        firmware_file = Path(firmware_file_path)

        config = get_config()

        if firmware_file.is_file():
            self.firmware_content = open(firmware_file_path, 'rb').read()
        else:
            self.block_blob_service = BlockBlobService(
                account_name=config.AZURE_STORAGE_ACCOUNT, protocol='https')
            self.block_blob_service.get_blob_to_path(
                config.AZURE_STORAGE_APPS_CONTAINER, file, firmware_file_path)
            self.firmware_content = open(firmware_file_path, 'rb').read()

        self.addr = 0
        self.fs_len = len(self.firmware_content)
        return True

    def start_bootloader(self):
        '''
        Start bootloader
        '''
        try:
            # TODO: should send set quiet command before go to bootloader mode
            command_line = helper.build_bootloader_input_packet('JI')
            self.communicator.reset_buffer()  # clear input and output buffer
            self.communicator.write(command_line, True)
            time.sleep(3)
            # It is used to skip streaming data with size 1000 per read
            self.read_untils_have_data('JI', 1000, 50)
            self.communicator.serial_port.baudrate = self.bootloader_baudrate
            return True
        except Exception as ex:  # pylint:disable=broad-except
            print('bootloader exception', ex)
            return False

    def write_firmware(self):
        '''Upgrades firmware of connected device to file provided in argument
        '''
        while self.addr < self.fs_len:
            packet_data_len = self.max_data_len if (
                self.fs_len - self.addr) > self.max_data_len else (self.fs_len - self.addr)
            data = self.firmware_content[self.addr: (
                self.addr + packet_data_len)]
            self.write_block(packet_data_len, self.addr, data)
            self.addr += packet_data_len
            self.add_output_packet('stream', 'upgrade_progress', {
                'addr': self.addr,
                'fs_len': self.fs_len
            })
            # output firmware upgrading

    def write_block(self, data_len, addr, data):
        '''
        Send block to bootloader
        '''
        # print(data_len, addr, time.time())
        command_line = helper.build_bootloader_input_packet(
            'WA', data_len, addr, data)
        try:
            self.communicator.write(command_line, True)
        except Exception:  # pylint: disable=broad-except
            self.exception_lock.acquire()
            self.exception_thread = True
            self.exception_lock.release()
            return

        if addr == 0:
            time.sleep(8)

        response = self.read_untils_have_data('WA', 50, 50)
        # wait WA end if cannot read response in defined retry times
        if response is None:
            time.sleep(0.1)

    def upgrade_completed(self, options):
        '''
        Actions after upgrade complete
        '''
        self.input_result = None
        self.bootloader_result = None
        self.data_queue.queue.clear()
        self.is_upgrading = False

        self.load_properties()
        self._logger = FileLoger(self.properties)
        self.cli_options = options

        self._message_center.get_parser().set_configuration(self.properties)
        self._message_center.resume()

        if options and not options.with_data_log and self.enable_data_log:
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

    def on_upgarde_failed(self, message):
        '''
        Linstener for upgrade failure
        '''
        self.is_upgrading = False
        self._message_center.resume()
        self.add_output_packet(
            'stream', 'upgrade_complete', {'success': False, 'message': message})
