import sys
import struct
import time
from ..dmu import dmu_helper
from ...framework.utils import (helper, resource)
from ...framework.context import APP_CONTEXT

ID = [0x49, 0x44]
VR = [0x56, 0x52]


def _run_command(communicator, message_type, response_message_type, message_bytes=[], size=100, retry=5):
    command_line = dmu_helper.build_packet(message_type, message_bytes)
    communicator.write(command_line)
    time.sleep(0.1)

    data_buffer = helper.read_untils_have_data(
        communicator, response_message_type, size, retry)

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
            formatted = ''

    return formatted


def _need_check(limit_type, device_type):
    if limit_type is None:
        return True

    return limit_type == device_type


def ping(communicator, *args):
    '''DMU Ping
    '''
    filter_device_type = args[0]
    is_need_check = _need_check(filter_device_type, 'DMU')

    if not is_need_check:
        return None

    pk_result = _run_command(communicator, 'PK', 'PK')

    if pk_result == []:
        id_packet_data = _run_command(communicator, 'GP', 'ID', ID)
        vr_packet_data = _run_command(communicator, 'GP', 'VR', VR)
        if id_packet_data is None or vr_packet_data is None:
            return None

        mode_string_len = len(id_packet_data[4:])
        model_string = struct.pack('{0}B'.format(
            mode_string_len), *id_packet_data[4:]).decode()

        ping_info = {
            'device_type': 'DMU',
            'device_info': id_packet_data,
            'app_info': vr_packet_data
        }

        # return ping info if specified the device type
        if filter_device_type == 'DMU':
            return ping_info

        if model_string.find('OpenIMU') > -1 or \
                model_string.find('OpenRTK') > -1:
            return None

        return ping_info

    return None
