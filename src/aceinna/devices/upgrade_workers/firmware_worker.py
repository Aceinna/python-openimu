import time
from ..base.upgrade_worker_base import UpgradeWorkerBase
from ...framework.utils import helper
from . import (UPGRADE_EVENT, UPGRADE_GROUP)


class FirmwareUpgradeWorker(UpgradeWorkerBase):
    '''Firmware upgrade worker
    '''

    def __init__(self, communicator, baudrate, file_content, block_size=240):
        super(FirmwareUpgradeWorker, self).__init__()
        self._communicator = communicator
        self.current = 0
        self._baudrate = baudrate
        self.max_data_len = block_size  # custom
        self._group = UPGRADE_GROUP.FIRMWARE

        if not callable(file_content):
            self._file_content = file_content
        else:
            self._file_content = file_content()
        self.total = len(self._file_content)
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
            #print('WA', command_line)
            self._communicator.write(command_line, True)
        except Exception as ex:  # pylint: disable=broad-except
            return False

        # custom
        if current == 0:
            try:
                self.emit(UPGRADE_EVENT.FIRST_PACKET)
            except Exception as ex:
                self.emit(UPGRADE_EVENT.ERROR, self._key,
                          'Fail in first packet: {0}'.format(ex))
                return False

        response = helper.read_untils_have_data(
            self._communicator, 'WA', 12, 10)
        # wait WA end if cannot read response in defined retry times
        if response is None:
            time.sleep(0.1)
        return True

    def work(self):
        '''Upgrades firmware of connected device to file provided in argument
        '''
        if self._is_stopped:
            return

        if self.current == 0 and self.total == 0:
            self.emit(UPGRADE_EVENT.ERROR, self._key, 'Invalid file content')
            return

        # # run command JI
        # command_line = helper.build_bootloader_input_packet('JI')
        # self._communicator.reset_buffer()  # clear input and output buffer
        # self._communicator.write(command_line, True)
        # time.sleep(3)

        # # It is used to skip streaming data with size 1000 per read
        # helper.read_untils_have_data(
        #     self._communicator, 'JI', 1000, 50)

        self._communicator.serial_port.baudrate = self._baudrate
        self._communicator.reset_buffer()

        try:
            self.emit(UPGRADE_EVENT.BEFORE_WRITE)
        except Exception as ex:
            self.emit(UPGRADE_EVENT.ERROR, self._key,
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
                self.emit(UPGRADE_EVENT.ERROR, self._key,
                          'Write firmware operation failed')
                return

            self.current += packet_data_len
            self.emit(UPGRADE_EVENT.PROGRESS, self._key,
                      self.current, self.total)

        # # run command JA
        # command_line = helper.build_bootloader_input_packet('JA')
        # self._communicator.write(command_line, True)
        # time.sleep(5)

        # # ping device
        # can_ping = False

        # while not can_ping:
        #     info = ping(self._communicator, None)
        #     if info:
        #         can_ping = True
        #     time.sleep(0.5)

        try:
            self.emit(UPGRADE_EVENT.AFTER_WRITE)
        except Exception as ex:
            self.emit(UPGRADE_EVENT.ERROR, self._key,
                      'Fail in after write: {0}'.format(ex))
            return

        if self.total > 0 and self.current >= self.total:
            self.emit(UPGRADE_EVENT.FINISH, self._key)
