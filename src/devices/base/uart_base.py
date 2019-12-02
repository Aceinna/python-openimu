from abc import ABCMeta, abstractmethod
import sys
import threading
import operator
import datetime
import collections
import time
import struct
from ...framework.utils import helper
from ...framework.file_storage import FileLoger
if sys.version_info[0] > 2:
    from queue import Queue
else:
    from Queue import Queue


class OpenDeviceBase:
    __metaclass__ = ABCMeta

    def __init__(self):
        self.threads = []  # thread of receiver and paser
        self.exception_thread = False  # flag of exit threads
        self.exception_lock = threading.Lock()  # lock of exception_thread
        self.exit_thread = False
        self.data_queue = Queue()  # data container
        self.data_lock = threading.Lock()
        self.clients = []
        self.input_result = None
        self.listeners = {}
        self.is_streaming = False
        self.has_running_checker = False
        self._logger = None
        self.connected = False
        self.is_upgrading = False
        pass

    @abstractmethod
    def load_properties(self):
        pass

    def internal_input_command(self, command, read_length=500):
        command_line = helper.build_input_packet(command)
        self.communicator.write(command_line)
        time.sleep(0.05)
        data_buffer = self.communicator.read(read_length)
        # print('parsed', data_buffer)
        parsed = self.extract_command_response(command, data_buffer)
        format_string = None
        if parsed is not None:
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
                # command_start(2) packet_length(1) crc(2)
                if len(packet_buffer) == packet_buffer[2] + 5:
                    if packet_buffer[-2:] == helper.calc_crc(packet_buffer[:-2]):
                        data = packet_buffer[3:packet_buffer[2]+3]
                        return data
                    else:
                        sync_state = 0  # CRC did not match

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
                    out = [(value['name'], data[idx])
                           for idx, value in enumerate(packet_config['payload'])]
                    item = collections.OrderedDict(out)
                    data.append(data)
                except Exception as e:
                    print(
                        "error happened when decode the payload, pls restart IMU firmware: {0}".format(e))
        else:
            try:
                b = struct.pack(len_fmt, *payload)
                data = struct.unpack(pack_fmt, b)
                out = [(value['name'], data[idx])
                       for idx, value in enumerate(packet_config['payload'])]
                data = collections.OrderedDict(out)
                # return data
            except Exception as e:
                print(
                    "error happened when decode the payload of packets, pls restart IMU: {0}".format(e))

        self._logger.append(packet_config['name'], data)
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
            for parameter in user_configuration:
                id = parameter['paramId']
                type = parameter['type']
                name = parameter['name']
                value = self.unpack_one(type, payload[id*8:(id+1)*8])
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
        elif type == 'uint32':
            try:
                b = struct.pack('4B', *data)
            except:
                return False
            return struct.unpack('<L', b)[0]
        elif type == 'char8':
            try:
                b = struct.pack('8B', *data)
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
        elif type == 'double':
            try:
                b = struct.pack('8B', *data)
            except:
                return False
            return struct.unpack('d', b)[0]

    def setup(self, options):
        ''' start 2 threads, receiver, parser
        '''
        self.load_properties()
        self._logger = FileLoger(self.properties)
        if not options.nolog:
            self._logger.start_user_log('data')

        if not self.has_running_checker:
            t = threading.Thread(target=self.thread_running_checker, args=())
            t.start()
            print("Thread checker start at:[{0}].".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            self.has_running_checker = True

        funcs = [self.thread_receiver, self.thread_parser]
        for func in funcs:
            t = threading.Thread(target=func, args=())
            t.start()
            print("Thread[{0}({1})] start at:[{2}].".format(
                t.name, t.ident, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            self.threads.append(t)

    def thread_receiver(self):
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
                # print(datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S:') + ' '.join('0X{0:x}'.format(data[i]) for i in range(len(data))))
                self.data_lock.acquire()
                for d in data:
                    self.data_queue.put(d)
                self.data_lock.release()
            else:
                time.sleep(0.001)

    def thread_parser(self):
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
        #print(packet_type)
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
        self.clients.remove(client)

    def reset(self):
        self.threads.clear()
        self.listeners.clear()
        # self.clients.clear()
        self.input_result = None
        self.is_streaming = False
        self.is_upgrading = False
        self.exception_thread = False
        self.data_queue.queue.clear()
        if self._logger is not None:
            self._logger.stop_user_log()

    def close(self):
        self.reset()
        self.exit_thread = True

    def on(self, event_type, handler):
        if not self.listeners.__contains__(event_type):
            self.listeners[event_type] = []

        self.listeners[event_type].append(handler)
        # print('on', len(self.listeners[event_type]))

    def emit(self, event_type, *args):
        handlers = self.listeners[event_type]
        if handlers is not None and len(handlers) > 0:
            for handler in handlers:
                handler(*args)
