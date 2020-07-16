from abc import ABCMeta, abstractmethod
import os
import sys
import threading
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

    def _parse_buffer(self, data_buffer):
        response = {
            'parsed': False,
            'parsed_end_index': 0,
            'result': []
        }
        data_queue = Queue()
        data_queue.queue.extend(data_buffer)

        command_start = [0x55, 0x55]
        parsed_data = []
        is_header_found = False
        packet_type = ''
        data_buffer_len = len(data_buffer)

        while not data_queue.empty():
            if is_header_found:
                # if matched packet, is_header_found = False, parsed_data = []
                if not data_queue.empty():
                    packet_type_start = data_queue.get()
                else:
                    break

                if not data_queue.empty():
                    packet_type_end = data_queue.get()
                else:
                    break

                if not data_queue.empty():
                    packet_len = data_queue.get()
                    packet_type = ''.join(
                        ["%c" % x for x in [packet_type_start, packet_type_end]])
                    packet_data = []

                    if data_queue.qsize() >= packet_len:
                        # take packet
                        for _ in range(packet_len):
                            packet_data.append(data_queue.get())
                    else:
                        break
                    # update response
                    response['parsed'] = True
                    response['result'].append({
                        'type': packet_type,
                        'data': packet_data
                    })
                    response['parsed_end_index'] += data_buffer_len - \
                        data_queue.qsize()
                    data_buffer_len = data_queue.qsize()
                    parsed_data = []
                    is_header_found = False
                else:
                    break
            else:
                byte_item = data_queue.get()
                parsed_data.append(byte_item)

                if len(parsed_data) > 2:
                    parsed_data = parsed_data[-2:]

                if parsed_data == command_start:
                    # find message start
                    is_header_found = True
                    parsed_data = []

        return response

    # may lost data
    def read_untils_have_data(self, packet_type, read_length=200, retry_times=20):
        '''
        Get data from limit times of read
        '''
        result = None
        trys = 0
        data_buffer = []
        self.data_queue.queue.clear()

        while trys < retry_times:
            data_buffer_per_time = bytearray(
                self.communicator.read(read_length))
            data_buffer.extend(data_buffer_per_time)

            response = self._parse_buffer(data_buffer)
            if response['parsed']:
                matched_packet = next(
                    (packet['data'] for packet in response['result'] if packet['type'] == packet_type), None)
                if matched_packet is not None:
                    result = matched_packet
                    break
                else:
                    # clear buffer to parsed index
                    data_buffer = data_buffer[response['parsed_end_index']:]
            trys += 1

        return result

    def _setup_message_center(self):
        if not self._message_center:
            self._message_center = DeviceMessageCenter(self.communicator)

        if not self._message_center.is_ready():
            uart_parser = ParserManager.build(self.type, self.properties)
            self._message_center.set_parser(uart_parser)
            self._message_center.on(
                'continuous_message',
                self.on_receive_continuous_messsage
            )
            self._message_center.on(
                'error',
                self.on_recevie_message_center_error
            )
            self._message_center.on(
                'read_block',
                self.on_read_raw
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

        self._setup_message_center()

        if with_data_log and not self.is_logging and self.enable_data_log:
            log_result = self._logger.start_user_log('data')
            if log_result == 1 or log_result == 2:
                raise Exception('Cannot start data logger')
            self.is_logging = True

        self.after_setup()

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
            if not self.download_firmware(file):
                self.on_upgarde_failed('cannot find firmware file')
                return
            # step.2 jump to bootloader
            if not self.switch_to_bootloader():
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

    def _do_download_firmware(self, file):
        upgarde_root = os.path.join(resource.get_executor_path(), 'upgrade')
        firmware_content = None

        if not os.path.exists(upgarde_root):
            os.makedirs(upgarde_root)

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
        try:
            self.firmware_content = self._do_download_firmware(file)
            self.addr = 0
            self.fs_len = len(self.firmware_content)
            can_download = True
        except Exception as e:
            can_download = False

        return can_download

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
        # self.data_queue.queue.clear()
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
