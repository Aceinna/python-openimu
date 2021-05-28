import time
from ..base.upgrade_worker_base import UpgradeWorkerBase
from ...framework.utils import helper
from ..ping.open import ping
from . import (UPGRADE_EVENT, UPGRADE_GROUP)


class JumpApplicationWorker(UpgradeWorkerBase):
    '''Firmware upgrade worker
    '''

    def __init__(self, communicator):
        super(JumpApplicationWorker, self).__init__()
        self._communicator = communicator
        self.current = 0
        self.total = 0
        self._group = UPGRADE_GROUP.FIRMWARE

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
        command_line = helper.build_bootloader_input_packet('JA')
        self._communicator.serial_port.baudrate = 115200
        self._communicator.reset_buffer()  # clear input and output buffer
        self._communicator.write(command_line, True)
        time.sleep(5)

        # ping device
        can_ping = False

        while not can_ping:
            info = ping(self._communicator, None)
            if info:
                can_ping = True
            time.sleep(0.5)

        self.emit(UPGRADE_EVENT.FINISH, self._key)
