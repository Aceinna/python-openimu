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
PAYLOAD_LEN_INDEX = 8
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


class EthernetMessageParser(MessageParserBase):
    def __init__(self, configuration):
        super(EthernetMessageParser, self).__init__(configuration)

    def set_run_command(self, command):
        pass

    def analyse(self, data):
        sync_pattern = data[0:2]
        if operator.eq(list(sync_pattern), MSG_HEADER) and len(data) >= PAYLOAD_LEN_INDEX:
            payload_len_byte = bytes(data[4:PAYLOAD_LEN_INDEX])
            payload_len = struct.unpack('<I', payload_len_byte)[0]

            packet_type_byte = bytes(data[PACKET_TYPE_INDEX:4])
            packet_type = struct.unpack('>H', packet_type_byte)[0]

            if len(data) < PAYLOAD_LEN_INDEX + payload_len + 2:
                APP_CONTEXT.get_logger().logger.info(
                    "crc check error! packet_type:{0}".format(packet_type))

                self.emit('crc_failure', packet_type=packet_type,
                            event_time=time.time())
                print('crc_failure', packet_type=packet_type,
                            event_time=time.time())
                return

            result = helper.calc_crc(data[2:PAYLOAD_LEN_INDEX+payload_len])

            if result[0] == data[PAYLOAD_LEN_INDEX + payload_len] and result[1] == data[PAYLOAD_LEN_INDEX + payload_len + 1]:
                self._parse_message(packet_type_byte, payload_len, data)
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
                                raw=data)

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
