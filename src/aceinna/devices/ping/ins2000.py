import sys
import time
import struct
from ...framework.utils import (helper, resource)
from ...framework.context import APP_CONTEXT


unlog_cmd = 'unlogall\r'
version_cmd = 'version\r'

def _run_command(communicator, command, size=1000, retry=10):
    communicator.write(command.encode())
    time.sleep(0.1)

    read_data = communicator.read(size)
    out_str = ""
    if read_data is not None:
        data_buffer = bytearray(read_data)
        if data_buffer and len(data_buffer) > 0:
            try:
                out_str = data_buffer.decode()
            except Exception:
                return ""

    return out_str

def ping(communicator, *args):
    '''INS2000 Device Ping
    '''
    unlog_text = _run_command(communicator, unlog_cmd)
    if unlog_text != None and unlog_text != '':
        device_info_text = _run_command(communicator, version_cmd)
        if device_info_text.find('INS2000') > -1:
            device_info_sp = device_info_text.split('\r\n')
            return {
                'device_type': 'INS2000',
                'device_info': device_info_sp[1],
                'app_info': device_info_sp[1]
            }

    return None
