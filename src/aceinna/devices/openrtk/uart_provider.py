import time
import json
import serial
import serial.tools.list_ports
import struct

from ...framework.context import APP_CONTEXT
from ..base.rtk_provider_base import RTKProviderBase

from ..upgrade_workers import (
    FirmwareUpgradeWorker,
    UPGRADE_EVENT,
    SDK8100UpgradeWorker
)
from ...framework.utils import helper
from ...framework.utils.print import print_red


class Provider(RTKProviderBase):
    '''
    OpenRTK UART provider
    '''

    def __init__(self, communicator, *args):
        super(Provider, self).__init__(communicator)
        self.bootloader_baudrate = 115200
        self.config_file_name = 'openrtk.json'
        self.device_category = 'OpenRTK'
        self.port_index_define = {
            'user': 0,
            'rtcm': 1,
            'debug': 2,
        }

    def thread_debug_port_receiver(self, *args, **kwargs):
        if self.debug_logf is None:
            return

        cmd_log = 'log debug on\r\n'
        self.debug_serial_port.write(cmd_log.encode())

        # log data
        while True:
            try:
                data = bytearray(self.debug_serial_port.read_all())
            except Exception as e:
                print_red('DEBUG PORT Thread error: {0}'.format(e))
                return  # exit thread receiver
            if data and len(data) > 0:
                self.debug_logf.write(data)
            else:
                time.sleep(0.001)

    def thread_rtcm_port_receiver(self, *args, **kwargs):
        if self.rtcm_logf is None:
            return
        while True:
            try:
                data = bytearray(self.rtcm_serial_port.read_all())
            except Exception as e:
                print_red('RTCM PORT Thread error: {0}'.format(e))
                return  # exit thread receiver
            if len(data):
                self.rtcm_logf.write(data)
            else:
                time.sleep(0.001)

    def before_write_content(self):
        self.communicator.serial_port.baudrate = self.bootloader_baudrate
        self.communicator.serial_port.reset_input_buffer()

    def firmware_write_command_generator(self, data_len, current, data):
        command_WA = 'WA'
        message_bytes = []
        message_bytes.extend(struct.pack('>I', current))
        message_bytes.extend(struct.pack('B', data_len))
        message_bytes.extend(data)
        return helper.build_packet(command_WA, message_bytes)

    # override

    def build_worker(self, rule, content):
        if rule == 'rtk':
            firmware_worker = FirmwareUpgradeWorker(
                self.communicator, content,
                self.firmware_write_command_generator)
            firmware_worker.on(UPGRADE_EVENT.BEFORE_WRITE,
                               lambda: self.before_write_content())
            firmware_worker.on(
                UPGRADE_EVENT.FIRST_PACKET, lambda: time.sleep(8))
            return firmware_worker

        if rule == 'sdk':
            sdk_port = ''
            if (self.properties["initial"]["useDefaultUart"]):
                user_port_num, port_name = self.build_connected_serial_port_info()
                sdk_port = port_name + str(int(user_port_num) + 3)
            else:
                for uart in self.properties["initial"]["uart"]:
                    if uart['enable'] == 1:
                        if uart['name'] == 'SDK':
                            sdk_port = uart["value"]

            sdk_uart = serial.Serial(
                sdk_port, self.bootloader_baudrate, timeout=0.1)
            if not sdk_uart.isOpen():
                raise Exception('Cannot open SDK upgrade port')

            return SDK8100UpgradeWorker(sdk_uart, content)

    # command list
    # use base methods
