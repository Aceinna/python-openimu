import sys
import time
import struct
from ...framework.utils import (helper, resource)
from ...framework.context import APP_CONTEXT
pG = [0x01, 0xcc]


def _run_command(communicator, command):
    command_line = helper.build_ethernet_packet(
        communicator.get_dst_mac(), communicator.get_src_mac(), pG)

    data_buffer = []
    cmd_type = struct.unpack('>H', bytes(pG))[0]
    read_line = communicator.write_read(command_line, cmd_type)
    if read_line:
        packet_raw = read_line[14:]
        packet_type = packet_raw[2:4]
        if packet_type == bytes(command):
            packet_length = struct.unpack('<I', packet_raw[4:8])[0]
            data_buffer = packet_raw[8: 8 + packet_length]

    return data_buffer


def _format_string(data_buffer):
    parsed = bytearray(data_buffer) if data_buffer and len(
        data_buffer) > 0 else None

    formatted = ''
    if parsed is not None:
        try:
            if sys.version_info < (3, 0):
                formatted = str(struct.pack(
                    '{0}B'.format(len(parsed)), *parsed))
            else:
                formatted = str(struct.pack(
                    '{0}B'.format(len(parsed)), *parsed), 'utf-8')
        except UnicodeDecodeError:
            APP_CONTEXT.get_logger().logger.error('Parse data as string failed')
            formatted = ''

    return formatted


def _need_check(limit_type, device_type):
    if limit_type is None:
        return True

    return limit_type == device_type


def run_command_as_string(communicator, command):
    ''' Run command and parse result as string
    '''
    data_buffer = _run_command(communicator, command)
    result = _format_string(data_buffer)

    return result


def ping(communicator, *args):
    '''OpenDevice Ping
    '''
    info_text = run_command_as_string(communicator, pG)

    # Prevent action. Get app info again,
    # if cannot retrieve any info at the first time of ping. Should find the root cause.
    
    if info_text.find('INS401') > -1:
        split_text = info_text.split(' RTK_INS')
        device_info_text = split_text[0]
        app_info_text = 'RTK_INS' + split_text[1]
        return {
            'device_type': 'INS401',
            'device_info': device_info_text,
            'app_info': app_info_text
        }

    return None
