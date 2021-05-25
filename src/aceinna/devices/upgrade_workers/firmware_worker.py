import time
from ..base.upgrade_worker_base import UpgradeWorkerBase
from ...framework.utils import helper


class EVENT_TYPE:
    '''
    Event type of Device Message Center
    '''
    FIRST_PACKET = 'first_packet'
    BEFORE_WRITE = 'before_write'
    AFTER_WRITE = 'after_write'
    FINISH = 'finish'
    ERROR = 'error'
    PROGRESS = 'progress'


class FirmwareUpgradeWorker(UpgradeWorkerBase):
    '''Firmware upgrade worker
    '''

    def __init__(self, communicator, baudrate, file_content, block_size=240):
        super(FirmwareUpgradeWorker, self).__init__()
        self._file_content = file_content
        self._communicator = communicator
        self.current = 0
        self.total = len(file_content)
        self._baudrate = baudrate
        self.max_data_len = block_size  # custom
        # self._key = None
        # self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def get_upgrade_content_size(self):
        return self.total

    def write_block(self, data_len, current, data):
        '''
        Send block to bootloader
        '''
        # print(data_len, addr, time.time())
        command_line = helper.build_bootloader_input_packet(
            'WA', data_len, current, data)
        try:
            self._communicator.write(command_line, True)
        except Exception as ex:  # pylint: disable=broad-except
            return False

        # custom
        if current == 0:
            try:
                self.emit(EVENT_TYPE.FIRST_PACKET)
            except Exception as ex:
                self.emit(EVENT_TYPE.ERROR, self._key,
                          'Fail in first packet: {0}'.format(ex))
                return False

        response = helper.read_untils_have_data(
            self._communicator, 'WA', 50, 50)
        # wait WA end if cannot read response in defined retry times
        if response is None:
            time.sleep(0.1)
        return True

    def work(self):
        '''Upgrades firmware of connected device to file provided in argument
        '''
        if self._is_stopped:
            return
        print('I am working...firmware')
        if self.current == 0 and self.total == 0:
            self.emit(EVENT_TYPE.ERROR, self._key, 'Invalid file content')
            return

        self._communicator.serial_port.baudrate = self._baudrate
        self._communicator.serial_port.reset_input_buffer()
        try:
            self.emit(EVENT_TYPE.BEFORE_WRITE)
        except Exception as ex:
            self.emit(EVENT_TYPE.ERROR, self._key,
                      'Fail in before write: {0}'.format(ex))
            return
        while self.current < self.total:
            if self._is_stopped:
                return

            packet_data_len = self.max_data_len if (
                self.total - self.current) > self.max_data_len else (self.total - self.current)
            data = self._file_content[self.current: (
                self.current + packet_data_len)]
            write_result = self.write_block(
                packet_data_len, self.current, data)

            if not write_result:
                self.emit(EVENT_TYPE.ERROR, self._key,
                          'Write firmware operation failed')
                return

            self.current += packet_data_len
            self.emit(EVENT_TYPE.PROGRESS, self._key, self.current, self.total)

        try:
            self.emit(EVENT_TYPE.AFTER_WRITE)
        except Exception as ex:
            self.emit(EVENT_TYPE.ERROR, self._key,
                      'Fail in after write: {0}'.format(ex))
            return

        if self.total > 0 and self.current >= self.total:
            self.emit(EVENT_TYPE.FINISH, self._key)
