from abc import ABCMeta, abstractmethod
import sys
import threading
import operator
import datetime
import collections
import time
import struct
from ...framework.utils import helper
if sys.version_info[0] > 2:
    from queue import Queue
else:
    from Queue import Queue


class OpenDeviceBase:
    __metaclass__ = ABCMeta

    def __init__(self):
        self.threads = []  # thread of receiver and paser
        self.exit_thread = False  # flag of exit threads
        self.exit_lock = threading.Lock()  # lock of exit_thread
        self.data_queue = Queue()  # data container
        self.data_lock = threading.Lock()
        self.clients = []
        self.input_result = None
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

        self.on_receive_output_packet(packet_config['name'], data)

    def unpack_input_packet(self, packet_config, payload):
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
        pass

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

    def setup(self):
        ''' start 2 threads, receiver, parser
        '''
        self.load_properties()

        funcs = [self.receiver, self.parser]
        for func in funcs:
            t = threading.Thread(target=func, args=())
            t.start()
            print("Thread[{0}({1})] start at:[{2}].".format(
                t.name, t.ident, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            self.threads.append(t)

    def receiver(self):
        ''' receive rover data and push data into data_queue.
            return when occur Exception
        '''
        while True:
            try:
                data = bytearray(self.communicator.read())
            except Exception as e:
                print(e)
                self.exit_lock.acquire()
                self.exit_thread = True  # Notice thread paser to exit.
                self.exit_lock.release()
                return  # exit thread receiver

            if len(data):
                # print(datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S:') + ' '.join('0X{0:x}'.format(data[i]) for i in range(len(data))))
                self.data_lock.acquire()
                for d in data:
                    self.data_queue.put(d)
                self.data_lock.release()
            else:
                time.sleep(0.001)

    def parser(self):
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
            self.data_lock.acquire()
            if self.data_queue.empty():
                self.data_lock.release()
                time.sleep(0.001)
                continue
            else:
                data = self.data_queue.get()
                self.data_lock.release()
                # print(datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S:') + hex(data))

                if find_header:
                    frame.append(data)
                    if PAYLOAD_LEN_IDX == len(frame):
                        payload_len = data
                    # 5: 2 msg_header + 2 packet_type + 1 payload_len 2:len of checksum.
                    elif 5 + payload_len + 2 == len(frame):
                        find_header = False
                        # checksum
                        result = helper.calc_crc(frame[2:-2])
                        if result[0] == frame[-2] and result[1] == frame[-1]:
                            # find a whole frame
                            self.parse_frame(frame, payload_len)
                            find_header = False
                            payload_len = 0
                            sync_pattern = collections.deque(2*[0], 2)
                        else:
                            print("Checksum error!")
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

    def parse_frame(self, frame, payload_len):
        data = []
        PACKET_TYPE_INDEX = 2
        PAYLOAD_LEN_IDX = 4
        packet_type = ''.join(
            ["%c" % x for x in frame[PACKET_TYPE_INDEX:PAYLOAD_LEN_IDX]])
        frame_offset = PAYLOAD_LEN_IDX+1
        payload = frame[frame_offset:payload_len+frame_offset]

        output_packet_config = next(
            (x for x in self.properties['userMessages']['outputPackets'] if x['name'] == packet_type), None)
        input_packet_config = next(
            (x for x in self.properties['userMessages']['inputPackets'] if x['name'] == packet_type), None)
        bootloader_packet_config = next(
            (x for x in self.properties['bootloaderMessages'] if x['name'] == packet_type), None)

        if output_packet_config:
            self.unpack_output_packet(output_packet_config, payload)

        if input_packet_config:
            self.unpack_input_packet(input_packet_config, payload)

        if bootloader_packet_config != None:
            self.unpack_bootloader_packet(
                bootloader_packet_config, payload)

    def response(self, method, packet_type, data=None):
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

    def add_output_packet(self, method, packet_type, data):
        for client in self.clients:
            client.on_receive_output_packet(method, packet_type, data)
        pass

    def notify_client(self, method):
        for client in self.clients:
            client.on_receive_notify(method)
        pass

    def append_client(self, client):
        self.clients.append(client)

    def remove_client(self, client):
        self.clients.remove(client)
