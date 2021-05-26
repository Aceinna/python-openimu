import time
from ..base.upgrade_worker_base import UpgradeWorkerBase
from ...framework.utils import helper
from . import FIRMWARE_EVENT_TYPE


class JumpBootloaderWorker(UpgradeWorkerBase):
    '''Firmware upgrade worker
    '''

    def __init__(self, communicator):
        super(JumpBootloaderWorker, self).__init__()
        self._communicator = communicator
        self.current = 0
        self.total = 0

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
        time.sleep(3)

        # It is used to skip streaming data with size 1000 per read
        JI_result = helper.read_untils_have_data(
            self._communicator, 'JI', 1000, 50)

        if not JI_result:
            self.emit(FIRMWARE_EVENT_TYPE.ERROR, self._key, 'Cannot jump to bootloader')
            return


        self.emit(FIRMWARE_EVENT_TYPE.FINISH, self._key)
