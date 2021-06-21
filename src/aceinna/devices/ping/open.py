import sys
import time
import struct
from ...framework.utils import (helper, resource)
from ...framework.context import APP_CONTEXT

pG = 'pG'
gV = 'gV'


def _run_command(communicator, command, size, retry):
    command_line = helper.build_input_packet(command)
    communicator.write(command_line)
    time.sleep(0.1)

    data_buffer = helper.read_untils_have_data(
        communicator, command, size, retry)

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


def run_command_as_string(communicator, command, size=1000, retry=10):
    ''' Run command and parse result as string
    '''
    data_buffer = _run_command(communicator, command, size, retry)
    result = _format_string(data_buffer)

    return result


def ping(communicator, *args):
    '''OpenDevice Ping
    '''
    filter_device_type = args[0]

    device_info_text = run_command_as_string(communicator, pG)
    app_info_text = run_command_as_string(communicator, gV)

    # Prevent action. Get app info again,
    # if cannot retrieve any info at the first time of ping. Should find the root cause.
    if app_info_text == '':
        app_info_text = run_command_as_string(communicator, gV)

    if _need_check(filter_device_type, 'RTK') and device_info_text.find('OpenRTK') > -1:
        return {
            'device_type': 'OpenRTK',
            'device_info': device_info_text,
            'app_info': app_info_text
        }

    if _need_check(filter_device_type, 'RTKL') and device_info_text.find('RTK330L') > -1:
        return {
            'device_type': 'RTKL',
            'device_info': device_info_text,
            'app_info': app_info_text
        }

    if _need_check(filter_device_type, 'IMU') and device_info_text.find('OpenIMU') > -1 and \
            device_info_text.find('OpenRTK') == -1:
        return {
            'device_type': 'OpenIMU',
            'device_info': device_info_text,
            'app_info': app_info_text
        }

    return None
