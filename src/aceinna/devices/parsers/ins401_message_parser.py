import collections
import operator
import time
import struct
from ..base.message_parser_base import MessageParserBase
from ...framework.utils import helper
from ...framework.context import APP_CONTEXT
from .ins401_packet_parser import (
    match_command_handler, common_continuous_parser, other_output_parser)

MSG_HEADER = [0x55, 0x55]
PACKET_TYPE_INDEX = 2
INPUT_PACKETS = [
    b'\x01\xcc',  # Get device information
    b'\x02\xcc',  # Get parameter
    b'\x03\xcc',  # Set parameter
    b'\x04\xcc',  # Save config
    b'\x01\x0b',  # Send odometer
    b'\x02\x0b'  # Send NMEA
]
OUTPUT_PACKETS = [
    b'\x01\n',  # IMU 100hz 30 3000
    b'\x02\n',  # GNSS 1hz 77 77
    b'\x03\n',  # INS 100hz 108 10800
    b'\x04\n',  # Odometer 20hz 500
    b'\x05\n',  # diagnostic 1hz 31 31
    b'\x06\n'  # RTCM Rover 3000
]


class ANALYSIS_STATUS:
    INIT = 0
    FOUND_HEADER = 1
    FOUND_PAYLOAD_LENGTH = 2
    FOUND_PACKET_TYPE = 3
    CRC_PASSED = 4


class EthernetPacket:
    _payload_length = 0
    _raw_data_bytes = []
    _payload_bytes = []
    _packet_type = None

    def __init__(self):
        self._payload_length = 0
        self._raw_data_bytes = []
        self._payload_bytes = []
        self._packet_type = None

    @property
    def payload_length(self):
        return self._payload_length

    @property
    def packet_type(self):
        return self._packet_type

    @property
    def payload(self):
        return self._raw_data_bytes[5: self._payload_length]

    @property
    def raw(self):
        return self._raw_data_bytes

    def accept_to_header(self, bytes_data):
        self._raw_data_bytes.extend(bytes_data)

    def accept_to_length(self, bytes_data):
        payload_len_byte = bytes(bytes_data)
        payload_len = struct.unpack('<I', payload_len_byte)[0]
        self._payload_length = payload_len+8
        self._raw_data_bytes.extend(bytes_data)

    def accept_to_packet_type(self, bytes_data):
        self._packet_type = bytes(bytes_data)
        self._raw_data_bytes.extend(bytes_data)

    def accept_to_payload(self, byte_data):
        self._raw_data_bytes.append(byte_data)

    def check_crc(self):
        crc_calculate_value = helper.calc_crc(self._raw_data_bytes[2:-2])
        crc_value = self._raw_data_bytes[-2:]
        return crc_calculate_value == crc_value


# class EthernetMessageParser(MessageParserBase):
#     _current_analysis_status = ANALYSIS_STATUS.INIT
#     _current_packet = None
#     _read_index = 0
#     _current_packet_type = []
#     _current_packet_payload_length = []

#     def __init__(self, configuration):
#         super(EthernetMessageParser, self).__init__(configuration)
#         self._current_analysis_status = ANALYSIS_STATUS.INIT
#         self._sync_pattern = collections.deque(2*[0], 2)
#         self._current_packet_type = []
#         self._current_packet_payload_length = []

#     def set_run_command(self, command):
#         pass

#     def analyse(self, data):
#         for value in data:
#             if self._current_analysis_status == ANALYSIS_STATUS.INIT:
#                 self._sync_pattern.append(value)

#                 if self._sync_pattern[0] == MSG_HEADER[0] and self._sync_pattern[1] == MSG_HEADER[1]:
#                     self._current_packet = EthernetPacket()
#                     self._current_packet.accept_to_header(
#                         list(self._sync_pattern))
#                     self._current_analysis_status = ANALYSIS_STATUS.FOUND_HEADER
#                     self._read_index = len(MSG_HEADER)

#                 continue

#             if self._current_analysis_status == ANALYSIS_STATUS.FOUND_HEADER:
#                 if len(self._current_packet_type) < 2:
#                     self._current_packet_type.append(value)

#                 if len(self._current_packet_type) == 2:
#                     self._current_packet.accept_to_packet_type(
#                         self._current_packet_type)
#                     self._current_analysis_status = ANALYSIS_STATUS.FOUND_PACKET_TYPE
#                     self._read_index += 2

#                 continue

#             if self._current_analysis_status == ANALYSIS_STATUS.FOUND_PACKET_TYPE:
#                 if len(self._current_packet_payload_length) < 4:
#                     self._current_packet_payload_length.append(value)

#                 if len(self._current_packet_payload_length) == 4:
#                     self._current_packet.accept_to_length(
#                         self._current_packet_payload_length)
#                     self._current_analysis_status = ANALYSIS_STATUS.FOUND_PAYLOAD_LENGTH
#                     self._read_index += 4
#                 continue

#             if self._current_analysis_status == ANALYSIS_STATUS.FOUND_PAYLOAD_LENGTH:
#                 self._current_packet.accept_to_payload(value)
#                 self._read_index += 1
#                 if self._read_index == self._current_packet.payload_length + 2:
#                     # calculate crc
#                     crc_result = self._current_packet.check_crc()
#                     if not crc_result:
#                         self.reset()
#                         continue

#                     # crc valid
#                     self._current_analysis_status = ANALYSIS_STATUS.CRC_PASSED

#                 if self._current_analysis_status == ANALYSIS_STATUS.CRC_PASSED:
#                     # self.crc_passed_count += 1
#                     # packets.push(this._currentPacket);
#                     self._parse_message(self._current_packet)
#                     self.reset()

#                 continue

#     def reset(self):
#         self._current_analysis_status = ANALYSIS_STATUS.INIT
#         self._sync_pattern = collections.deque(2*[0], 2)
#         self._current_packet_type = []
#         self._current_packet_payload_length = []
#         self._read_index = 0

#     def _parse_message(self, data_packet):
#         # parse interactive commands
#         is_interactive_cmd = INPUT_PACKETS.__contains__(
#             data_packet.packet_type)
#         if is_interactive_cmd:
#             self._parse_input_packet(data_packet)
#         else:
#             # consider as output packet, parse output Messages
#             self._parse_output_packet(data_packet)

#     def _parse_input_packet(self, data_packet):
#         payload_parser = match_command_handler(data_packet.packet_type)
#         if payload_parser:
#             data, error = payload_parser(
#                 data_packet.payload, self.properties['userConfiguration'])

#             self.emit('command',
#                       packet_type=data_packet.packet_type,
#                       data=data,
#                       error=error,
#                       raw=data_packet.raw)
#         else:
#             print('[Warning] Unsupported command {0}'.format(
#                 str(data_packet.packet_type)))

#     def _parse_output_packet(self, data_packet):
#         # check if it is the valid out packet
#         is_output_packet = OUTPUT_PACKETS.__contains__(data_packet.packet_type)
#         if is_output_packet:
#             self.emit('continuous_message',
#                       packet_type=data_packet.packet_type,
#                       data=data_packet.payload,
#                       event_time=time.time(),
#                       raw=data_packet.raw)
#             return


class EthernetMessageParser(MessageParserBase):
    def __init__(self, configuration):
        super(EthernetMessageParser, self).__init__(configuration)
        self.frame = []
        self.payload_len_idx = 8
        self.sync_pattern = collections.deque(2*[0], 2)
        self.find_header = False
        self.payload_len = 0
        # command,continuous_message

    def set_run_command(self, command):
        pass

    def analyse(self, data):
        for data_block in data:
            if self.find_header:
                self.frame.append(data_block)

                if self.payload_len_idx == len(self.frame):
                    payload_len_byte = bytes(self.frame[4:])
                    self.payload_len = struct.unpack('<I', payload_len_byte)[0]

                elif 8 + self.payload_len + 2 == len(self.frame):
                    packet_type_byte = bytes(self.frame[PACKET_TYPE_INDEX:4])
                    packet_type = struct.unpack('>H', packet_type_byte)[0]
                    self.find_header = False
                    result = helper.calc_crc(self.frame[2:-2])
                    if result[0] == self.frame[-2] and result[1] == self.frame[-1]:
                        # find a whole frame
                        # self._parse_frame(self.frame, self.payload_len)
                        self._parse_message(
                            struct.pack('>H', packet_type), self.payload_len, self.frame)

                        self.find_header = False
                        self.payload_len = 0
                        self.sync_pattern = collections.deque(2*[0], 2)
                    else:
                        APP_CONTEXT.get_logger().logger.info(
                            "crc check error! packet_type:{0}".format(packet_type))

                        self.emit('crc_failure', packet_type=packet_type,
                                event_time=time.time())
                        input_packet_config = next(
                            (x for x in self.properties['userMessages']['inputPackets']
                            if x['name'] == packet_type), None)
                        if input_packet_config:
                            self.emit('command',
                                    packet_type=packet_type,
                                    data=[],
                                    error=True,
                                    raw=self.frame)
            else:
                self.sync_pattern.append(data_block)
                if operator.eq(list(self.sync_pattern), MSG_HEADER):
                    self.frame = MSG_HEADER[:]  # header_tp.copy()
                    self.find_header = True

    def _parse_message(self, packet_type, payload_len, frame):
        payload = frame[self.payload_len_idx:payload_len+self.payload_len_idx]
        # parse interactive commands
        is_interactive_cmd = INPUT_PACKETS.__contains__(packet_type)

        if is_interactive_cmd:
            self._parse_input_packet(packet_type, payload, frame)
        else:
            # consider as output packet, parse output Messages
            self._parse_output_packet(packet_type, payload, frame)

    def _parse_input_packet(self, packet_type, payload, frame):
        payload_parser = match_command_handler(packet_type)

        if payload_parser:
            data, error = payload_parser(
                payload, self.properties['userConfiguration'])
            self.emit('command',
                      packet_type=packet_type,
                      data=data,
                      error=error,
                      raw=frame)
        else:
            print('[Warning] Unsupported command {0}'.format(
                packet_type.encode()))

    def _parse_output_packet(self, packet_type, payload, frame):
        # check if it is the valid out packet
        is_output_packet = OUTPUT_PACKETS.__contains__(packet_type)
        if is_output_packet:

            self.emit('continuous_message',
                      packet_type=packet_type,
                      data=payload,
                      event_time=time.time(),
                      raw=frame)
            return

