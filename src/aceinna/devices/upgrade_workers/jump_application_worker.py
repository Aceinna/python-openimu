import time
from ..base.upgrade_worker_base import UpgradeWorkerBase
from ...framework.utils import helper
from ..ping.open import ping
from . import (UPGRADE_EVENT, UPGRADE_GROUP)


class JumpApplicationWorker(UpgradeWorkerBase):
    '''Firmware upgrade worker
    '''
    _command = None
    _listen_packet = None
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
            self._listen_packet = kwargs.get('command')

    def stop(self):
        self._is_stopped = True

    def get_upgrade_content_size(self):
        return self.total

    def work(self):
        '''Send JA and ping device
        '''
        if self._is_stopped:
            return

        # run command JA
        # command_line = helper.build_bootloader_input_packet('JA')
        # self._communicator.serial_port.baudrate = self._bootloader_baudrate

        self.emit('before_command')

        self._communicator.reset_buffer()  # clear input and output buffer
        self._communicator.write(self._command, True)
        time.sleep(5)

        self.emit('after_command')

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