import collections
import operator
import struct
from .base.event_base import EventBase
from ..framework.utils import helper
from ..framework.context import APP_CONTEXT

MSG_HEADER = [0x55, 0x55]
PACKET_TYPE_INDEX = 2
PRIVATE_PACKET_TYPE = ['RE', 'WE', 'UE', 'LE', 'SR']


class UartMessageParser(EventBase):
    def __init__(self, configuration):
        super(UartMessageParser, self).__init__()
        self.frame = []
        self.payload_len_idx = 5
        self.sync_pattern = collections.deque(2*[0], 2)
        self.find_header = False
        self.payload_len = 0
        self.properties = configuration
        # command,continuous_message

    def set_configuration(self, configuration):
        self.properties = configuration

    def analyse(self, data_block):
        if self.find_header:
            self.frame.append(data_block)
            if self.payload_len_idx == len(self.frame):
                self.payload_len = data_block

            elif 5 + self.payload_len + 2 == len(self.frame):
                packet_type = ''.join(
                    ["%c" % x for x in self.frame[PACKET_TYPE_INDEX:4]])
                self.find_header = False
                result = helper.calc_crc(self.frame[2:-2])
                if result[0] == self.frame[-2] and result[1] == self.frame[-1]:
                    # find a whole frame
                    self._parse_frame(self.frame, self.payload_len)

                    self.find_header = False
                    self.payload_len = 0
                    self.sync_pattern = collections.deque(2*[0], 2)
                else:
                    print("crc check error! packet_type:", packet_type)
                    input_packet_config = next(
                        (x for x in self.properties['userMessages']['inputPackets']
                         if x['name'] == packet_type), None)
                    if input_packet_config:
                        self.emit('command', packet_type=packet_type,
                                  data=[], error=True)

            # if payload_len > MAX_FRAME_LIMIT or len(frame) > MAX_FRAME_LIMIT:
            #     find_header = False
            #     payload_len = 0
        else:
            self.sync_pattern.append(data_block)
            if operator.eq(list(self.sync_pattern), MSG_HEADER):
                self.frame = MSG_HEADER[:]  # header_tp.copy()
                self.find_header = True

    def _parse_frame(self, frame, payload_len):
        packet_type_index = 2
        payload_len_idx = 4
        packet_type = ''.join(
            ["%c" % x for x in frame[packet_type_index:payload_len_idx]])
        frame_offset = payload_len_idx+1
        payload = frame[frame_offset:payload_len+frame_offset]
        if PRIVATE_PACKET_TYPE.__contains__(packet_type):
            self.unpack_private_packet(packet_type, payload)
            return

        if self.properties.__contains__('userMessages'):
            output_packet_config = next(
                (x for x in self.properties['userMessages']['outputPackets']
                 if x['name'] == packet_type), None)
            self.unpack_output_packet(output_packet_config, payload)

            input_packet_config = next(
                (x for x in self.properties['userMessages']['inputPackets']
                 if x['name'] == packet_type), None)
            self.unpack_input_packet(input_packet_config, payload)

            if output_packet_config is None and input_packet_config is None:
                APP_CONTEXT.get_logger().logger.info(
                    "%s packet not found in JSON!" % packet_type
                )

        if self.properties.__contains__('bootloaderMessages'):
            bootloader_packet_config = next(
                (x for x in self.properties['bootloaderMessages']
                 if x['name'] == packet_type), None)
            self.unpack_bootloader_packet(
                bootloader_packet_config, payload)

    def unpack_output_packet(self, packet_config, payload):
        '''
        Unpack output packet
        '''
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
                    pack_item = struct.pack(len_fmt, *payload_c)
                    item = struct.unpack(pack_fmt, pack_item)
                    out = [(value['name'], item[idx])
                           for idx, value in enumerate(packet_config['payload'])]
                    item = collections.OrderedDict(out)
                    data.append(item)
                    # self._logger.append(packet_config['name'], item)
                except Exception as ex:  # pylint: disable=broad-except
                    print(
                        "error happened when decode the payload, pls restart driver: {0}"
                        .format(ex))
        else:
            try:
                pack_item = struct.pack(len_fmt, *payload)
                data = struct.unpack(pack_fmt, pack_item)
                out = [(value['name'], data[idx])
                       for idx, value in enumerate(packet_config['payload'])]
                data = collections.OrderedDict(out)
                # self._logger.append(packet_config['name'], data)
                # return data
            except Exception as ex:  # pylint: disable=broad-except
                print(
                    "error happened when decode the payload of packets, pls restart driver: {0}"
                    .format(ex))

        self.emit('continuous_message',
                  packet_type=packet_config['name'],
                  data=data)

    def unpack_input_packet(self, packet_config, payload):
        '''
        Unpack input packet
        '''
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
                param_id = parameter['paramId']
                param_type = parameter['type']
                name = parameter['name']

                if param_type == 'uint8' or param_type == 'int8':
                    value = self._unpack_one(
                        param_type, payload[data_len:data_len + 1])
                    data_len = data_len + 1
                elif param_type == 'uint16' or param_type == 'int16':
                    value = self._unpack_one(
                        param_type, payload[data_len:data_len + 2])
                    data_len = data_len + 2
                elif param_type == 'uint32' or param_type == 'int32' or param_type == 'float':
                    value = self._unpack_one(
                        param_type, payload[data_len:data_len + 4])
                    data_len = data_len + 4
                elif param_type == 'uint64' or param_type == 'int64' or param_type == 'double':
                    value = self._unpack_one(
                        param_type, payload[data_len:data_len + 8])
                    data_len = data_len + 8
                elif param_type == 'ip4':
                    value = self._unpack_one(
                        param_type, payload[data_len:data_len + 4])
                    data_len = data_len + 4
                elif param_type == 'ip6':
                    value = self._unpack_one(
                        param_type, payload[data_len:data_len + 6])
                    data_len = data_len + 6
                elif 'char' in param_type:
                    ctype_n = param_type.replace('char', '')
                    ctype_l = int(ctype_n)
                    value = self._unpack_one(
                        param_type, payload[data_len:data_len + ctype_l])
                    data_len = data_len + ctype_l
                else:
                    print(
                        "no [{0}] when unpack_input_packet".format(param_type))
                    value = False

                data.append(
                    {"paramId": param_id, "name": name, "value": value})
        elif response_playload_type_config == 'userParameter':
            param_id = self._unpack_one('uint32', payload[0:4])
            param = filter(lambda item: item['paramId'] ==
                           param_id, user_configuration)
            try:
                first_item = next(iter(param), None)
                param_value = self._unpack_one(
                    first_item['type'], payload[4:12])
                data = {"paramId": param_id,
                        "name": first_item['name'], "value": param_value}
            except StopIteration:
                error = True
        elif response_playload_type_config == 'paramId':
            data = self._unpack_one('uint32', payload[0:4])
            if data:
                error = True
        elif response_playload_type_config == 'string':
            data = self._unpack_one('string', payload)
        elif response_playload_type_config == 'bytes':
            options = packet_config['responsePayload']['options']
            offset = options['offset']
            data = payload[offset:]
        else:
            data = payload

        self.emit('command',
                  packet_type=packet_config['name'],
                  data=data,
                  error=error)

    def unpack_bootloader_packet(self, packet_config, payload):
        '''
        Unpack bootloader packet
        '''
        if packet_config is None:
            return

        data = payload
        error = False
        self.emit('command',
                  packet_type=packet_config['name'],
                  data=data,
                  error=error)

    def unpack_private_packet(self, packet_type, payload):
        '''
        Unpack private command packet
        '''
        data = []
        if packet_type == 'RE':
            data = payload[3:]
        else:
            data = payload

        self.emit('command',
                  packet_type=packet_type,
                  data=data,
                  error=False)

    def _unpack_one(self, data_type, data):
        if data_type == 'uint64':
            try:
                pack_item = struct.pack('8B', *data)
            except:  # pylint: disable=bare-except
                return False
            return struct.unpack('<Q', pack_item)[0]
        elif data_type == 'int64':
            try:
                pack_item = struct.pack('8B', *data)
            except:  # pylint: disable=bare-except
                return False
            return struct.unpack('<q', pack_item)[0]
        elif data_type == 'double':
            try:
                pack_item = struct.pack('8B', *data)
            except:  # pylint: disable=bare-except
                return False
            return struct.unpack('d', pack_item)[0]
        elif data_type == 'uint32':
            try:
                pack_item = struct.pack('4B', *data)
            except:  # pylint: disable=bare-except
                return False
            return struct.unpack('<I', pack_item)[0]
        elif data_type == 'int32':
            try:
                pack_item = struct.pack('4B', *data)
            except:  # pylint: disable=bare-except
                return False
            return struct.unpack('<i', pack_item)[0]
        elif data_type == 'float':
            try:
                pack_item = struct.pack('4B', *data)
            except:  # pylint: disable=bare-except
                return False
            return struct.unpack('<f', pack_item)[0]
        elif data_type == 'uint16':
            try:
                pack_item = struct.pack('2B', *data)
            except:  # pylint: disable=bare-except
                return False
            return struct.unpack('<H', pack_item)[0]
        elif data_type == 'int16':
            try:
                pack_item = struct.pack('2B', *data)
            except:  # pylint: disable=bare-except
                return False
            return struct.unpack('<h', pack_item)[0]
        elif data_type == 'uint8':
            try:
                pack_item = struct.pack('1B', *data)
            except:  # pylint: disable=bare-except
                return False
            return struct.unpack('<B', pack_item)[0]
        elif data_type == 'int8':
            try:
                pack_item = struct.pack('1B', *data)
            except:  # pylint: disable=bare-except
                return False
            return struct.unpack('<b', pack_item)[0]
        elif 'char' in data_type:
            try:
                ctype_n = data_type.replace('char', '')
                pack_item = struct.pack(ctype_n + 'B', *data)
                return pack_item.decode()
            except:  # pylint: disable=bare-except
                return False
        elif data_type == 'string':
            try:
                fmt_str = '{0}B'.format(len(data))
                pack_item = struct.pack(fmt_str, *data)
                return pack_item
            except:  # pylint: disable=bare-except
                return False
        elif data_type == 'ip4':
            try:
                ip_1 = str(data[0])
                ip_2 = str(data[1])
                ip_3 = str(data[2])
                ip_4 = str(data[3])
                return ip_1+'.'+ip_2+'.'+ip_3+'.'+ip_4
            except:  # pylint: disable=bare-except
                return False
        elif data_type == 'ip6':
            try:
                ip_1 = str(data[0])
                ip_2 = str(data[1])
                ip_3 = str(data[2])
                ip_4 = str(data[3])
                ip_5 = str(data[4])
                ip_6 = str(data[5])
                return ip_1+'.'+ip_2+'.'+ip_3+'.'+ip_4+'.'+ip_5+'.'+ip_6
            except:  # pylint: disable=bare-except
                return False
        else:
            return False
