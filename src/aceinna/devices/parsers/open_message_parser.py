import collections
import operator
import struct
from ..base.event_base import EventBase
from ...framework.utils import helper
from ...framework.context import APP_CONTEXT
from .open_packet_parser import (
    match_command_handler, common_continuous_parser)

MSG_HEADER = [0x55, 0x55]
PACKET_TYPE_INDEX = 2
PRIVATE_PACKET_TYPE = ['RE', 'WE', 'UE', 'LE', 'SR']
INPUT_PACKETS = ['gA', 'gB', 'gP', 'sC', 'uP', 'uB',
                 'rD', '\x15\x15', '\x00\x00',
                 'JI', 'JA', 'WA',
                 'RE', 'WE', 'UE', 'LE', 'SR']


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

    def set_run_command(self, command):
        pass

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
                    # self._parse_frame(self.frame, self.payload_len)
                    self._parse_message(
                        packet_type, self.payload_len, self.frame[5:self.payload_len+5])

                    self.find_header = False
                    self.payload_len = 0
                    self.sync_pattern = collections.deque(2*[0], 2)
                else:
                    APP_CONTEXT.get_logger().logger.info(
                        "crc check error! packet_type:{0}".format(packet_type))
                    input_packet_config = next(
                        (x for x in self.properties['userMessages']['inputPackets']
                         if x['name'] == packet_type), None)
                    if input_packet_config:
                        self.emit('command', packet_type=packet_type,
                                  data=[], error=True)
        else:
            self.sync_pattern.append(data_block)
            if operator.eq(list(self.sync_pattern), MSG_HEADER):
                self.frame = MSG_HEADER[:]  # header_tp.copy()
                self.find_header = True

    def _parse_message(self, packet_type, payload_len, payload):
        # parse interactive commands
        is_interactive_cmd = INPUT_PACKETS.__contains__(packet_type)
        if is_interactive_cmd:
            self._parse_input_packet(packet_type, payload_len, payload)
        else:
            # consider as output packet, parse output Messages
            self._parse_output_packet(packet_type, payload_len, payload)

    def _parse_input_packet(self, packet_type, payload_len, payload):
        # print(packet_type, payload, payload_len)
        payload_parser = match_command_handler(packet_type)

        if payload_parser:
            data, error = payload_parser(
                payload, self.properties['userConfiguration'])

            self.emit('command',
                      packet_type=packet_type,
                      data=data,
                      error=error)
        else:
            print('[Warning] Unsupported command {0}'.format(packet_type))

    def _parse_output_packet(self, packet_type, payload_len, payload):
        # check if it is the valid out packet
        payload_parser = common_continuous_parser
        output_packet_config = next(
            (x for x in self.properties['userMessages']['outputPackets']
             if x['name'] == packet_type), None)
        data = payload_parser(payload, output_packet_config)

        if not data:
            APP_CONTEXT.get_logger().logger.info(
                'Cannot parse packet type {0}. It may caused by firmware upgrade'.format(packet_type))
            return

        self.emit('continuous_message',
                  packet_type=packet_type,
                  data=data)
