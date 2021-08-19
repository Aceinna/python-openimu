import time
from ..base.upgrade_worker_base import UpgradeWorkerBase
from ...framework.utils import helper
from ...framework.command import Command
#from ..ping.open import ping
from . import (UPGRADE_EVENT, UPGRADE_GROUP)

#TODO may merge with jump bootloader worker
class JumpApplicationWorker(UpgradeWorkerBase):
    '''Firmware upgrade worker
    '''
    _command = None
    _listen_packet = None
    _wait_timeout_after_command = 3
    # bootloader_baudrate=115200

    def __init__(self, communicator, *args, **kwargs):
        super(JumpApplicationWorker, self).__init__()
        self._communicator = communicator
        self.current = 0
        self.total = 0
        #self._original_baudrate = communicator.serial_port.baudrate
        #self._bootloader_baudrate = bootloader_baudrate
        self._group = UPGRADE_GROUP.FIRMWARE

        if kwargs.get('command'):
            self._command = kwargs.get('command')

        if kwargs.get('listen_packet'):
            self._listen_packet = kwargs.get('listen_packet')

        if kwargs.get('wait_timeout_after_command'):
            self._wait_timeout_after_command = kwargs.get(
                'wait_timeout_after_command')

    def stop(self):
        self._is_stopped = True

    def get_upgrade_content_size(self):
        return self.total

    def work(self):
        '''Send JA and ping device
        '''
        # run command JA
        # command_line = helper.build_bootloader_input_packet('JA')
        # self._communicator.serial_port.baudrate = self._bootloader_baudrate

        if self._is_stopped:
            return

        if self._command:
            actual_command = None
            payload_length_format = 'B'

            if callable(self._command):
                self._command = self._command()

            if  isinstance(self._command, Command):
                actual_command = self._command.actual_command
                payload_length_format = self._command.payload_length_format

            if isinstance(self._command, list):
                actual_command = self._command

            self.emit(UPGRADE_EVENT.BEFORE_COMMAND)

            self._communicator.reset_buffer()
            self._communicator.write(actual_command)

            time.sleep(self._wait_timeout_after_command)

            helper.read_untils_have_data(
                self._communicator, self._listen_packet, 1000, 50, payload_length_format)

            self.emit(UPGRADE_EVENT.AFTER_COMMAND)

        # ping device
        # can_ping = False
        # self._communicator.serial_port.baudrate = self._original_baudrate

        # while not can_ping:
        #     self._communicator.reset_buffer()  # clear input and output buffer
        #     info = ping(self._communicator, None)
        #     if info:
        #         can_ping = True
        #     time.sleep(0.5)

        self.emit(UPGRADE_EVENT.FINISH, self._key)