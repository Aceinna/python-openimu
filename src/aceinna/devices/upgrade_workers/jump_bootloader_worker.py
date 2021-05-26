import time
from ..base.upgrade_worker_base import UpgradeWorkerBase
from ...framework.utils import helper
from . import (UPGRADE_EVENT,UPGRADE_GROUP)


class JumpBootloaderWorker(UpgradeWorkerBase):
    '''Firmware upgrade worker
    '''

    def __init__(self, communicator):
        super(JumpBootloaderWorker, self).__init__()
        self._communicator = communicator
        self.current = 0
        self.total = 0
        self._group = UPGRADE_GROUP.FIRMWARE

    def stop(self):
        self._is_stopped = True

    def get_upgrade_content_size(self):
        return self.total

    def work(self):
        '''Send JI command
        '''
        if self._is_stopped:
            return

        # run command JI
        command_line = helper.build_bootloader_input_packet('JI')
        self._communicator.reset_buffer()  # clear input and output buffer
        self._communicator.write(command_line, True)
        time.sleep(3)  # waiting switch to bootloader

        # It is used to skip streaming data with size 1000 per read
        helper.read_untils_have_data(self._communicator, 'JI', 1000, 50)

        self.emit(UPGRADE_EVENT.FINISH, self._key)
