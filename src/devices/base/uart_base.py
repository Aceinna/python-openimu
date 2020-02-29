from abc import ABCMeta, abstractmethod
import os
import sys
import threading
import operator
import datetime
import collections
import time
import struct
import traceback
from pathlib import Path
from ...framework.utils import helper
from ...framework.file_storage import FileLoger
from azure.storage.blob import BlockBlobService
if sys.version_info[0] > 2:
    from queue import Queue
else:
    from Queue import Queue


class OpenDeviceBase(object):
    __metaclass__ = ABCMeta

    def __init__(self, communicator):
        self.threads = []  # thread of receiver and paser
        self.exception_thread = False  # flag of exit threads
        self.exception_lock = threading.Lock()  # lock of exception_thread
        self.exit_thread = False
        self.data_queue = Queue()  # data container
        self.data_lock = threading.Lock()
        self.clients = []
        self.input_result = None
        self.bootloader_result = None
        self.listeners = {}
        self.is_streaming = False
        self.has_running_checker = False
        self._logger = None
        self.connected = False
        self.is_upgrading = False
        self.complete_upgrade = False
        self.communicator = communicator
        self.bootloader_baudrate = 57600
        pass

    @abstractmethod
    def load_properties(self):
        pass

    @abstractmethod
    def after_setup(self):
        pass

    def internal_input_command(self, command, read_length=500):
        command_line = helper.build_input_packet(command)
        self.communicator.write(command_line)
        time.sleep(0.1)

        data_buffer = self.read_untils_have_data(command, read_length, 20)
        parsed = bytearray(data_buffer) if data_buffer and len(
            data_buffer) > 0 else None

        format_string = None
        if parsed is not None:
            if (sys.version_info < (3, 0)):
                format_string = str(struct.pack(
                    '{0}B'.format(len(parsed)), *parsed))
            else:
                format_string = str(struct.pack(
                    '{0}B'.format(len(parsed)), *parsed), 'utf-8')

        if format_string is not None:
            return format_string
        return ''

    def extract_command_response(self, command, data_buffer):
        command_0 = ord(command[0])
        command_1 = ord(command[1])
        sync_pattern = collections.deque(4*[0], 4)
        sync_state = 0
        packet_buffer = []
        for i, new_byte in enumerate(data_buffer):
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
        response = False
        trys = 0

        while not response and trys < retry_times:
            data_buffer = bytearray(self.communicator.read(read_length))
            if data_buffer:
                # print('data_buffer', data_buffer)
                response = self.extract_command_response(
                    packet_type, data_buffer)
            trys += 1

        # print('read end', time.time(), 'try times', trys, 'response', response)

        return response

    def unpack_output_packet(self, packet_config, payload):
        if packet_config is None:
            return

        data = None
        is_list = 0
        length = 0
        pack_fmt = '<'
        for value in packet_config['payload']:
            if value['type'] == 'float':
                pack_fmt += 'f'
                length += 4
            elif value['type'] == 'uint32':
                pack_fmt += 'I'
                length += 4
            elif value['type'] == 'int32':
                pack_fmt += 'i'
                length += 4
            elif value['type'] == 'int16':
                pack_fmt += 'h'
                length += 2
            elif value['type'] == 'uint16':
                pack_fmt += 'H'
                length += 2
            elif value['type'] == 'double':
                pack_fmt += 'd'
                length += 8
            elif value['type'] == 'int64':
                pack_fmt += 'q'
                length += 8
            elif value['type'] == 'uint64':
                pack_fmt += 'Q'
                length += 8
            elif value['type'] == 'char':
                pack_fmt += 'c'
                length += 1
            elif value['type'] == 'uchar':
                pack_fmt += 'B'
                length += 1
            elif value['type'] == 'uint8':
                pack_fmt += 'B'
                length += 1
        len_fmt = '{0}B'.format(length)

        has_list = packet_config.__contains__('isList')
        if has_list:
            is_list = packet_config['isList']

        if is_list == 1:
            packet_num = len(payload) // length
            data = []
            for i in range(packet_num):
                payload_c = payload[i*length:(i+1)*length]
                try:
                    b = struct.pack(len_fmt, *payload_c)
                    item = struct.unpack(pack_fmt, b)
                    out = [(value['name'], item[idx])
                           for idx, value in enumerate(packet_config['payload'])]
                    item = collections.OrderedDict(out)
                    data.append(item)
                    self._logger.append(packet_config['name'], item)
                except Exception as e:
                    print(
                        "error happened when decode the payload, pls restart driver: {0}".format(e))
        else:
            try:
                b = struct.pack(len_fmt, *payload)
                data = struct.unpack(pack_fmt, b)
                out = [(value['name'], data[idx])
                       for idx, value in enumerate(packet_config['payload'])]
                data = collections.OrderedDict(out)
                self._logger.append(packet_config['name'], data)
                # return data
            except Exception as e:
                print(
                    "error happened when decode the payload of packets, pls restart driver: {0}".format(e))

        self.on_receive_output_packet(packet_config['name'], data)

    def unpack_input_packet(self, packet_config, payload):
        if packet_config is None:
            return

        data = None
        error = False
        response_playload_type_config = packet_config['responsePayload']['type'] \
            if packet_config['responsePayload'].__contains__('type') else ''
        user_configuration = self.properties['userConfiguration']

        if response_playload_type_config == 'userConfiguration':
            data = []
            data_len = 0
            for parameter in user_configuration:
                id = parameter['paramId']
                type = parameter['type']
                name = parameter['name']

                if type == 'uint8' or type == 'int8':
                    value = self.unpack_one(
                        type, payload[data_len:data_len + 1])
                    data_len = data_len + 1
                elif type == 'uint16' or type == 'int16':
                    value = self.unpack_one(
                        type, payload[data_len:data_len + 2])
                    data_len = data_len + 2
                elif type == 'uint32' or type == 'int32' or type == 'float':
                    value = self.unpack_one(
                        type, payload[data_len:data_len + 4])
                    data_len = data_len + 4
                elif type == 'uint64' or type == 'int64' or type == 'double':
                    value = self.unpack_one(
                        type, payload[data_len:data_len + 8])
                    data_len = data_len + 8
                elif type == 'ip4':
                    value = self.unpack_one(
                        type, payload[data_len:data_len + 4])
                    data_len = data_len + 4
                elif type == 'ip6':
                    value = self.unpack_one(
                        type, payload[data_len:data_len + 6])
                    data_len = data_len + 6
                elif 'char' in type:
                    ctype_n = type.replace('char', '')
                    ctype_l = int(ctype_n)
                    value = self.unpack_one(
                        type, payload[data_len:data_len + ctype_l])
                    data_len = data_len + ctype_l
                else:
                    print(
                        "no [{0}] when unpack_input_packet".format(type))
                    value = False

                data.append({"paramId": id, "name": name, "value": value})
        elif response_playload_type_config == 'userParameter':
            param_id = self.unpack_one('uint32', payload[0:4])

            param = filter(lambda item: item.paramId ==
                           param_id, user_configuration)
            if len(param) > 0:
                param_value = self.unpack_one(param['type'], payload[4:12])
                data = {"paramId": param_id,
                        "name": param['name'], "value": param_value}
            else:
                error = True
        elif response_playload_type_config == 'paramId':
            data = self.unpack_one('uint32', payload[0:4])
            if data:
                error = True
        elif response_playload_type_config == 'string':
            data = self.unpack_one('string', payload)
        else:
            data = True

        self.on_receive_input_packet(packet_config['name'], data, error)

    def unpack_bootloader_packet(self, packet_config, payload):
        if packet_config is None:
            return

        data = payload
        error = False
        self.on_receive_bootloader_packet(packet_config['name'], data, error)

    def unpack_one(self, type, data):
        if type == 'uint64':
            try:
                b = struct.pack('8B', *data)
            except:
                return False
            return struct.unpack('<Q', b)[0]
        elif type == 'int64':
            try:
                b = struct.pack('8B', *data)
            except:
                return False
            return struct.unpack('<q', b)[0]
        elif type == 'double':
            try:
                b = struct.pack('8B', *data)
            except:
                return False
            return struct.unpack('d', b)[0]
        elif type == 'uint32':
            try:
                b = struct.pack('4B', *data)
            except:
                return False
            return struct.unpack('<I', b)[0]
        elif type == 'int32':
            try:
                b = struct.pack('4B', *data)
            except:
                return False
            return struct.unpack('<i', b)[0]
        elif type == 'float':
            try:
                b = struct.pack('4B', *data)
            except:
                return False
            return struct.unpack('<f', b)[0]
        elif type == 'uint16':
            try:
                b = struct.pack('2B', *data)
            except:
                return False
            return struct.unpack('<H', b)[0]
        elif type == 'int16':
            try:
                b = struct.pack('2B', *data)
            except:
                return False
            return struct.unpack('<h', b)[0]
        elif type == 'uint8':
            try:
                b = struct.pack('1B', *data)
            except:
                return False
            return struct.unpack('<B', b)[0]
        elif type == 'int8':
            try:
                b = struct.pack('1B', *data)
            except:
                return False
            return struct.unpack('<b', b)[0]
        elif 'char' in type:
            try:
                ctype_n = type.replace('char', '')
                b = struct.pack(ctype_n + 'B', *data)
                return b.decode()
            except:
                return False
        elif type == 'string':
            try:
                fmt_str = '{0}B'.format(len(data))
                b = struct.pack(fmt_str, *data)
                return b
            except:
                return False
        elif type == 'ip4':
            try:
                ip_1 = str(data[0])
                ip_2 = str(data[1])
                ip_3 = str(data[2])
                ip_4 = str(data[3])
                return ip_1+'.'+ip_2+'.'+ip_3+'.'+ip_4
            except:
                return False
        elif type == 'ip6':
            try:
                ip_1 = str(data[0])
                ip_2 = str(data[1])
                ip_3 = str(data[2])
                ip_4 = str(data[3])
                ip_5 = str(data[4])
                ip_6 = str(data[5])
                return ip_1+'.'+ip_2+'.'+ip_3+'.'+ip_4+'.'+ip_5+'.'+ip_6
            except:
                return False
        else:
            return False

    def setup(self, options):
        ''' start 2 threads, receiver, parser
        '''
        self.load_properties()
        self._logger = FileLoger(self.properties)
        if not options.nolog and self.properties['type'] != 'openrtk':
            self._logger.start_user_log('data')

        if not self.has_running_checker:
            t = threading.Thread(target=self.thread_running_checker, args=())
            t.start()
            # TODO: write to log
            # print("Thread checker start at:[{0}].".format(
            #     datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            self.has_running_checker = True

        funcs = [self.thread_receiver, self.thread_parser]
        for func in funcs:
            t = threading.Thread(target=func, args=(options.nolog,))
            t.start()
            # TODO: write to log
            # print("Thread[{0}({1})] start at:[{2}].".format(
            #     t.name, t.ident, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            self.threads.append(t)
        if not options.nolog:
            self.after_setup()

    @abstractmethod
    def on_read_raw(self, data):
        pass

    def thread_receiver(self, nolog):
        ''' receive rover data and push data into data_queue.
            return when occur Exception
        '''
        while True:
            if self.is_upgrading:
                time.sleep(0.1)
                continue

            try:
                data = bytearray(self.communicator.read())
            except Exception as e:
                print('Thread:receiver error:', e)
                self.exception_lock.acquire()
                self.exception_thread = True  # Notice thread paser to exit.
                self.exception_lock.release()
                return  # exit thread receiver

            if len(data):
                if nolog:
                    self.on_read_raw(data)
                # print(datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S:') + ' '.join('0X{0:x}'.format(data[i]) for i in range(len(data))))
                self.data_lock.acquire()
                for d in data:
                    self.data_queue.put(d)
                self.data_lock.release()
            else:
                time.sleep(0.001)

    def thread_parser(self, *args):
        ''' get rover data from data_queue and parse data into one whole frame.
            return when occur Exception in thread receiver.
        '''
        MSG_HEADER = [0x55, 0x55]
        PAYLOAD_LEN_IDX = 5
        MSG_SUB_ID_IDX = 3
        # assume max len of frame is smaller than MAX_FRAME_LIMIT.
        MAX_FRAME_LIMIT = 500

        sync_pattern = collections.deque(2*[0], 2)
        find_header = False
        frame = []
        payload_len = 0

        while True:
            self.exception_lock.acquire()
            if self.exception_thread:
                self.exception_lock.release()
                return  # exit thread parser
            self.exception_lock.release()

            if self.is_upgrading:
                time.sleep(0.1)
                continue

            self.data_lock.acquire()
            if self.data_queue.empty():
                self.data_lock.release()
                time.sleep(0.001)
                continue
            else:
                data = self.data_queue.get()
                self.data_lock.release()

                if find_header:
                    frame.append(data)
                    if PAYLOAD_LEN_IDX == len(frame):
                        payload_len = data
                    # 5: 2 msg_header + 2 packet_type + 1 payload_len 2:len of checksum.
                    elif 5 + payload_len + 2 == len(frame):
                        find_header = False
                        result = helper.calc_crc(frame[2:-2])
                        if result[0] == frame[-2] and result[1] == frame[-1]:
                            # find a whole frame
                            self.parse_frame(frame, payload_len)
                            find_header = False
                            payload_len = 0
                            sync_pattern = collections.deque(2*[0], 2)
                        else:
                            print("crc check error!")
                    else:
                        pass

                    # if payload_len > MAX_FRAME_LIMIT or len(frame) > MAX_FRAME_LIMIT:
                    #     find_header = False
                    #     payload_len = 0
                else:
                    sync_pattern.append(data)
                    if operator.eq(list(sync_pattern), MSG_HEADER):
                        frame = MSG_HEADER[:]  # header_tp.copy()
                        find_header = True
                        pass

    def thread_running_checker(self):
        while True:
            self.exception_lock.acquire()
            if self.exception_thread:
                self.connected = False
                self.emit('exception', 'app', 'communicator read error')
            self.exception_lock.release()

            if self.complete_upgrade:
                self.emit('complete_upgrade')
                self.complete_upgrade = False

            if self.exit_thread:
                return

            try:
                time.sleep(0.1)
            except KeyboardInterrupt:  # response for KeyboardInterrupt such as Ctrl+C
                return True

    def parse_frame(self, frame, payload_len):
        data = []
        PACKET_TYPE_INDEX = 2
        PAYLOAD_LEN_IDX = 4
        packet_type = ''.join(
            ["%c" % x for x in frame[PACKET_TYPE_INDEX:PAYLOAD_LEN_IDX]])
        frame_offset = PAYLOAD_LEN_IDX+1
        payload = frame[frame_offset:payload_len+frame_offset]
        # print(packet_type)
        if self.properties.__contains__('userMessages'):
            output_packet_config = next(
                (x for x in self.properties['userMessages']['outputPackets'] if x['name'] == packet_type), None)
            self.unpack_output_packet(output_packet_config, payload)

            input_packet_config = next(
                (x for x in self.properties['userMessages']['inputPackets'] if x['name'] == packet_type), None)
            self.unpack_input_packet(input_packet_config, payload)

        if self.properties.__contains__('bootloaderMessages'):
            bootloader_packet_config = next(
                (x for x in self.properties['bootloaderMessages'] if x['name'] == packet_type), None)
            self.unpack_bootloader_packet(
                bootloader_packet_config, payload)

    def add_output_packet(self, method, packet_type, data):
        for client in self.clients:
            client.on_receive_output_packet(method, packet_type, data)
        pass

    def append_client(self, client):
        self.clients.append(client)

    def remove_client(self, client):
        self.reset_client()
        self.clients.remove(client)

    def reset_client(self):
        self.input_result = None
        self.bootloader_result = None
        self.is_streaming = False
        self.is_upgrading = False
        if self._logger is not None:
            self._logger.stop_user_log()

    def reset(self):
        self.reset_client()
        # self.threads.clear()
        helper.clear_elements(self.threads)
        self.listeners.clear()
        # self.clients.clear()
        self.exception_thread = False
        self.data_queue.queue.clear()

    def close(self):
        self.reset()
        self.exit_thread = True

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
        upgarde_root = os.path.join(os.getcwd(), 'upgrade')

        if not os.path.exists(upgarde_root):
            os.makedirs(upgarde_root)

        firmware_file_path = os.path.join(upgarde_root, file)
        firmware_file = Path(firmware_file_path)

        if firmware_file.is_file():
            self.fw = open(firmware_file_path, 'rb').read()
        else:
            self.block_blob_service = BlockBlobService(
                account_name='navview', protocol='https')
            self.block_blob_service.get_blob_to_path(
                'apps', file, firmware_file_path)
            self.fw = open(firmware_file_path, 'rb').read()

        print('upgrade fw: %s' % file)
        self.max_data_len = 240
        self.addr = 0
        self.fs_len = len(self.fw)
        return True

    def start_bootloader(self):
        try:
            # TODO: should send set quiet command before go to bootloader mode
            command_line = helper.build_bootloader_input_packet('JI')
            self.communicator.reset_buffer()  # clear input and output buffer
            self.communicator.write(command_line, True)
            time.sleep(3)
            # It is used to skip streaming data with size 1000 per read
            parsed = self.read_untils_have_data('JI', 1000, 50)
            #print('parsed', parsed)
            self.communicator.serial_port.baudrate = self.bootloader_baudrate
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
        # print(data_len, addr, time.time())
        command_line = helper.build_bootloader_input_packet(
            'WA', None, data_len, addr, data)
        try:
            self.communicator.write(command_line, True)
        except Exception as e:
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
        self.input_result = None
        self.bootloader_result = None
        self.data_queue.queue.clear()
        self.is_upgrading = False

        self.load_properties()
        self._logger = FileLoger(self.properties)
        if not options.nolog and self.properties['type'] != 'openrtk':
            self._logger.start_user_log('data')

    def on_upgarde_failed(self, message):
        self.is_upgrading = False
        self.add_output_packet(
            'stream', 'upgrade_complete', {'success': False, 'message': message})
        pass

    def on(self, event_type, handler):
        if not self.listeners.__contains__(event_type):
            self.listeners[event_type] = []

        self.listeners[event_type].append(handler)

    def emit(self, event_type, *args):
        handlers = self.listeners[event_type]
        if handlers is not None and len(handlers) > 0:
            for handler in handlers:
                handler(*args)
