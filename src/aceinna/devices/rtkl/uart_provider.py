import time
import serial
import struct

from ..base.rtk_provider_base import RTKProviderBase
from ..upgrade_workers import (
    FirmwareUpgradeWorker,
    FIRMWARE_EVENT_TYPE,
    SDK9100UpgradeWorker
)
from ...framework.utils import (
    helper
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
        self.port_index_define = {
            'user': 0,
            'rtcm': 3,
            'debug': 2,
        }

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

    def before_write_content(self, core, content_len):
        message_bytes = [ord('C'), ord(core)]
        message_bytes.extend(struct.pack('>I', content_len))

        command_line = helper.build_packet('CS', message_bytes)
        # self.communicator.reset_buffer()  # clear input and output buffer
        self.communicator.write(command_line, True)
        time.sleep(2)
        result = helper.read_untils_have_data(
            self.communicator, 'CS', 1000, 50)

        if not result:
            raise Exception('Cannot run set core command')

    # override
    def build_worker(self, rule, content):
        if rule == 'rtk':
            rtk_upgrade_worker = FirmwareUpgradeWorker(
                self.communicator, self.bootloader_baudrate, content, 192)
            rtk_upgrade_worker.on(
                FIRMWARE_EVENT_TYPE.FIRST_PACKET, lambda: time.sleep(15))
            rtk_upgrade_worker.on(FIRMWARE_EVENT_TYPE.BEFORE_WRITE,
                                  lambda: self.before_write_content('0', len(content)))
            rtk_upgrade_worker.group = 'firmware'
            return

        if rule == 'ins':
            ins_upgrade_worker = FirmwareUpgradeWorker(
                self.communicator, self.bootloader_baudrate, content, 192)
            ins_upgrade_worker.on(
                FIRMWARE_EVENT_TYPE.FIRST_PACKET, lambda: time.sleep(15))
            ins_upgrade_worker.on(FIRMWARE_EVENT_TYPE.BEFORE_WRITE,
                                  lambda: self.before_write_content('1', len(content)))
            ins_upgrade_worker.group = 'firmware'
            return ins_upgrade_worker

        if rule == 'sdk':
            sdk_upgrade_worker = SDK9100UpgradeWorker(
                self.communicator, self.bootloader_baudrate, content)
            sdk_upgrade_worker.on(FIRMWARE_EVENT_TYPE.ERROR,
                                  self.reopen_rtcm_serial_port)
            sdk_upgrade_worker.on(FIRMWARE_EVENT_TYPE.FINISH,
                                  self.reopen_rtcm_serial_port)
            sdk_upgrade_worker.group = 'firmware'
            return sdk_upgrade_worker

    # command list
    # use base methods
