import collections
import time
import struct
import re
from ..base.message_parser_base import MessageParserBase

MSG_HEADER = [0x55, 0x55]
PACKET_TYPE_INDEX = 2
PRIVATE_PACKET_TYPE = ['RE', 'WE', 'UE', 'LE', 'SR']
INPUT_PACKETS = ['pG', 'uC', 'uP', 'uA', 'uB',
                 'sC', 'rD',
                 'gC', 'gA', 'gB', 'gP', 'gV',
                 '\x15\x15', '\x00\x00', 'ma',
                 'JI', 'JA', 'WA',
                 'RE', 'WE', 'UE', 'LE', 'SR']
OTHER_OUTPUT_PACKETS = ['CD', 'CB']


class UartMessageParser(MessageParserBase):
    def __init__(self, configuration):
        super(UartMessageParser, self).__init__(configuration)
        self.frame = []
        self.sync_pattern = collections.deque(3*[0], 3)
        self.sync_state = 0
        self.message_id = 0
        self.header_len = 0
        self.data_len = 0
        self.message_type = 0
        self.nmea_state = 0
        self.nmea_frame = []
        # command,continuous_message

    def set_run_command(self, command):
        pass

    def analyse(self, data_block):
        self.sync_pattern.append(data_block)
        if self.sync_state == 1:
            self.frame.append(data_block)
            packet_len = len(self.frame)
            if packet_len == 6:
                # b_buf = b''.join(map(lambda x:int.to_bytes(x, 1, 'little'), self.buf))
                b_buf = bytearray(self.frame)
                self.message_id, = struct.unpack('<H', b_buf[4:6])
                if self.message_id == 1462:
                    self.header_len = 12
                else:
                    self.header_len = self.frame[3]

            if self.header_len == packet_len:
                if self.message_id == 1462:
                    self.message_type = 0
                    self.data_len = self.frame[3]
                else:
                    self.message_type = self.frame[6]
                    b_buf = bytearray(self.frame)
                    self.data_len,  = struct.unpack('<H', b_buf[8:10])

            if self.data_len > 0 and packet_len == self.data_len + self.header_len + 4:
                # self.data = b''.join(map(lambda x:int.to_bytes(x, 1, 'little'), self.buf))
                data = bytearray(self.frame)
                if self.check_crc(data):
                    self._parse_message(self.message_id, packet_len, data)
                self.frame = []
                self.sync_state = 0
        else:
            if list(self.sync_pattern) == [0xAA, 0x44, 0x12] or list(self.sync_pattern) == [0xAA, 0x44, 0x13]:
                self.frame = [self.sync_pattern[0], self.sync_pattern[1], self.sync_pattern[2]]
                self.sync_state = 1

        if self.nmea_state == 1:
            self.nmea_frame.append(data_block)
            if data_block == 0x0A:
                if len(self.nmea_frame) >= 6 and \
                    self.nmea_frame[-5] == ord('*') and self.nmea_frame[-2] == 0x0D:
                    nmea = ''
                    try:
                        buf = bytearray(self.nmea_frame)
                        nmea = buf.decode('utf-8')
                    except:
                        pass

                    if nmea != '':
                        ridx = nmea.rfind('$')
                        if ridx > 0:
                            nmea = nmea[ridx:]
                        try:
                            cksum, calc_cksum = self.nmea_checksum(nmea)
                            if cksum == calc_cksum:
                                self._parse_nmea(nmea)
                        except:
                            print(nmea)

                self.nmea_frame = []
                self.nmea_state = 0
        else:
            if data_block == 0x24:
                self.nmea_state = 1
                self.nmea_frame = [data_block]


    def nmea_checksum(self, data):
        data = data.replace("\r", "").replace("\n", "").replace("$", "")
        nmeadata, cksum = re.split('\*', data, maxsplit=1)
        calc_cksum = 0
        for s in nmeadata:
            calc_cksum ^= ord(s)
        return int(cksum, 16), calc_cksum

    def check_crc(self, packet):
        """check packet crc"""
        crc = self.crc(packet[:-4])
        check_crc, = struct.unpack('<L', packet[-4:])
        return crc == check_crc

    def output_fmt(self, payload):
        """generate struct format"""
        packet_fmt = '<'
        keys = []
        for item in payload:
            if item["type"] == "int8":
                packet_fmt += 'b'
            if item["type"] == "uint8":
                packet_fmt += 'B'
            if item["type"] == "bool":
                packet_fmt += '?'
            if item["type"] == "int16":
                packet_fmt += 'h'
            if item["type"] == "uint16":
                packet_fmt += 'H'
            if item["type"] == "int32":
                packet_fmt += 'i'
            if item["type"] == "uint32":
                packet_fmt += 'I'
            if item["type"] == "int64":
                packet_fmt += 'q'
            if item["type"] == "uint64":
                packet_fmt += 'Q'
            if item["type"] == "float":
                packet_fmt += 'f'
            if item["type"] == "double":
                packet_fmt += 'd'
            if item["type"] == "string":
                packet_fmt += item["length"] + 's'

            keys.append(item["name"])

        return packet_fmt, keys


    def crc(self, data):
        """crc"""
        crc_rst = 0
        temp1 = 0
        temp2 = 0
        for byte_data in data:
            temp1 = (crc_rst >> 8)  & 0x00FFFFFF
            temp2 = self.crc_value((crc_rst ^ byte_data) & 0xFF)
            crc_rst = temp1 ^ temp2

        return crc_rst

    def crc_value(self, value):
        """Calculate a CRC value to be used by CRC calculation functions"""
        j = 8
        crc = value
        while j > 0:
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
            j -= 1

        return crc


    def _parse_message(self, packet_type, payload_len, frame):
        # parse interactive commands
        self._parse_output_packet(packet_type, frame)

    def _parse_input_packet(self, packet_type, payload, frame):
        pass

    def _parse_nmea(self, nmea):
        self.emit('continuous_message',
                  packet_type='nmea',
                  data=nmea,
                  event_time=time.time())

    def _parse_output_packet(self, packet_type, packet):
        """parse output packet"""
        message_id = packet_type
        message_id_str = str(message_id)
        if not message_id_str in self.properties["packetsTypeList"]:
            return

        message_str = self.properties["packetsTypeList"][message_id_str]
        if not message_str in self.properties["outputPackets"]:
            return

        payload = self.properties["outputPackets"][message_str]["payload"]
        bin_format, keys = self.output_fmt(payload)

        try:
            packets = struct.unpack(bin_format, packet[self.header_len:-4])
        except Exception as e:
            return

        dict_pack = dict(zip(keys, packets))
        dict_pack['header_message_id'] = message_id
        if message_id == 1462:
            dict_pack['header_gps_week'], = struct.unpack('<H', packet[6:8])
            dict_pack['header_gps_seconds'], = struct.unpack('i', packet[8:12])
        else:
            dict_pack['header_gps_week'], = struct.unpack('<H', packet[14:16])
            dict_pack['header_gps_seconds'], = struct.unpack('i', packet[16:20])

        # print(message_id, dict_pack)

        self.emit('continuous_message',
                  packet_type=packet_type,
                  data=dict_pack,
                  event_time=time.time())
