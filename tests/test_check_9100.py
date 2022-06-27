import os
from pickle import FALSE
import sys
import time
import serial
from queue import Queue
try:
    from aceinna.models import WebserverArgs
    from aceinna.core.driver import (Driver, DriverEvents)
    from aceinna.framework import AppLogger
    from aceinna.framework.utils import resource
    from aceinna.framework.context import APP_CONTEXT
    from aceinna.framework.utils import helper

except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.models import WebserverArgs
    from aceinna.core.driver import (Driver, DriverEvents)
    from aceinna.framework import AppLogger
    from aceinna.framework.utils import resource
    from aceinna.framework.context import APP_CONTEXT
    from aceinna.framework.utils import helper

LOOP_TIMES = 100

PORT = "/dev/cu.usbserial-143300"

BAUDRATE = 115200


def _match(result, check_data):
    check_data_len = len(check_data)
    result_len = len(result)

    if result_len < check_data_len:
        return False

    for m in range(result_len):
        is_diff = False

        if m + check_data_len > result_len:
            return False

        for n in range(check_data_len):
            if result[m+n] != check_data[n]:
                is_diff = True
                break

        if not is_diff:
            return True

    return False


def read_until(serial_port: serial.Serial, check_data, read_times=1000, read_len=None):
    is_match = False

    while read_times > 0:
        if read_len:
            result = serial_port.read(read_len)
        else:
            result = serial_port.read_all()
        if len(result) > 0:
            is_match = _match(result, check_data)
            break

        time.sleep(0.01)
        read_times -= 1

    return is_match


def send_JS(serial_port: serial.Serial):
    cmd = helper.build_bootloader_input_packet('JS')
    serial_port.write(cmd)
    time.sleep(0.5)

    response = helper.read_untils_have_data(
        serial_port, 'JS', read_length=1000, read_timeout=5)

    return True


def send_sync(serial_port):
    sync = [0xfd, 0xc6, 0x49, 0x28]
    expect_response = [0x3A, 0x54, 0x2C, 0xA6]
    retry_times = 10
    is_matched = False

    for i in range(retry_times):
        serial_port.write(sync)
        serial_port.write(sync)
        serial_port.write(sync)
        time.sleep(0.5)

        is_matched = read_until(serial_port, expect_response, 100)
        if is_matched:
            break

    return is_matched


def send_JG(serial_port):
    cmd = helper.build_bootloader_input_packet('JG')
    serial_port.write(cmd)
    time.sleep(0.5)
    response = helper.read_untils_have_data(serial_port, 'JG')
    return True if response is not None else False


class TestApp:
    def __init__(self):
        pass

    def send_commands(self, serial_port):
        # send JS
        if not send_JS(serial_port):
            print('send JS failed')
            return False
        # send sync
        if not send_sync(serial_port):
            print('send sync failed')
            return False
        # send JG
        if not send_JG(serial_port):
            print('send JG failed')
            return False

        return True

    def start(self):
        # set a loop time
        loop = 0
        while loop < LOOP_TIMES:
            print('Loop: {0}/{1}'.format(loop+1, LOOP_TIMES))
            # connect to device
            serial_port = serial.Serial(port=PORT, baudrate=BAUDRATE, timeout=0.1)
            #serial_port.open()

            if not serial_port.is_open:
                print('Cannot open serial port')
                return

            try:
                result = self.send_commands(serial_port)
                if not result:
                    raise Exception('commands failed')
            except Exception as ex:
                print(ex)
                break

            serial_port.close()
            time.sleep(20)

            loop += 1

if __name__ == '__main__':
    TestApp().start()
