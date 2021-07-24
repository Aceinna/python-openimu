import time

from ..base.upgrade_worker_base import UpgradeWorkerBase
from ...framework.utils import helper
from ...framework.communicator import Communicator
from ...framework.constants import INTERFACES
from . import (UPGRADE_EVENT, UPGRADE_GROUP)


class JumpBootloaderWorker(UpgradeWorkerBase):
    '''Firmware upgrade worker
    '''
    _command = None
    _listen_packet = None

    def __init__(self, communicator: Communicator, *args, **kwargs):
        super(JumpBootloaderWorker, self).__init__()
        self._communicator = communicator
        self.current = 0
        self.total = 0
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
        '''Send JI command
        '''
        if self._is_stopped:
            return

        if self._command:
            self._communicator.reset_buffer()
            self._communicator.write(self._command)

            time.sleep(3)

            helper.read_untils_have_data(
                self._communicator, self._listen_packet, 1000, 50)

        # if self._communicator.type == INTERFACES.UART:
        #     # run command JI
        #     command_line = helper.build_bootloader_input_packet('JI')
        #     self._communicator.reset_buffer()  # clear input and output buffer
        #     self._communicator.write(command_line, True)
        #     time.sleep(3)  # waiting switch to bootloader

        #     # It is used to skip streaming data with size 1000 per read
        #     helper.read_untils_have_data(self._communicator, 'JI', 1000, 50)

        # if self._communicator.type == INTERFACES.ETH_100BASE_T1:

        # time.sleep(6)

        self.emit(UPGRADE_EVENT.FINISH, self._key)
