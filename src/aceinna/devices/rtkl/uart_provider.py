import time
import serial
import serial.tools.list_ports

from ..base.rtk_provider_base import RTKProviderBase
from ..upgrade_workers import (
    FirmwareUpgradeWorker,
    FIRMWARE_EVENT_TYPE,
    SDKUpgradeWorker
)
from ...framework.utils.print import print_red


class Provider(RTKProviderBase):
    '''
    RTK330LA UART provider
    '''

    def __init__(self, communicator, *args):
        super(Provider, self).__init__(communicator)
        self.type = 'RTKL'
        self.bootloader_baudrate = 115200
        self.config_file_name = 'RTK330L.json'
        self.device_category = 'RTK330LA'

    # override
    def after_bootloader_switch(self):
        self.communicator.serial_port.baudrate = self.bootloader_baudrate
        self.communicator.serial_port.reset_input_buffer()
        time.sleep(8)

    def thread_debug_port_receiver(self, *args, **kwargs):
        if self.debug_logf is None:
            return

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

    # override
    def append_to_upgrade_center(self, upgrade_center, rule, content):
        if rule == 'rtk':
            firmware_worker = FirmwareUpgradeWorker(
                self.communicator, self.bootloader_baudrate, content, 192)
            firmware_worker.on(
                FIRMWARE_EVENT_TYPE.FIRST_PACKET, lambda: time.sleep(26))
            upgrade_center.register(firmware_worker)
            return

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

            sdk_uart = serial.Serial(sdk_port, 115200, timeout=0.1)
            if not sdk_uart.isOpen():
                raise Exception('Cannot open SDK upgrade port')

            upgrade_center.register(
                SDKUpgradeWorker(self.communicator, self.bootloader_baudrate, content))
            return

    # command list
    # use base methods
