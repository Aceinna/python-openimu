import time
from ..base.upgrade_worker_base import UpgradeWorkerBase
from ...framework.utils import helper
from ...framework.command import Command
from . import (UPGRADE_EVENT, UPGRADE_GROUP)


class FirmwareUpgradeWorker(UpgradeWorkerBase):
    '''Firmware upgrade worker
    '''

    def __init__(self, communicator, file_content, command_generator, block_size=240):
        super(FirmwareUpgradeWorker, self).__init__()
        self._communicator = communicator
        self.current = 0
        #self._baudrate = baudrate
        self.max_data_len = block_size  # custom
        self._group = UPGRADE_GROUP.FIRMWARE

        self._command_generator = command_generator
        if not callable(file_content):
            self._file_content = file_content
        else:
            self._file_content = file_content()
        self.total = len(self._file_content)

    def stop(self):
        self._is_stopped = True

    def get_upgrade_content_size(self):
        return self.total

    def write_block(self, data_len, current, data):
        '''
        Send block to bootloader
        '''
        if not callable(self._command_generator):
            self.emit(UPGRADE_EVENT.ERROR, self._key,
                      'There is no command generator for Firmware upgrade worker.')
            return False

        command = self._command_generator(data_len, current, data)

        actual_command = None
        payload_length_format = 'B'
        listen_packet = 'WA'

        if isinstance(command, Command):
            actual_command = command.actual_command
            payload_length_format = command.payload_length_format
            listen_packet = command.packet_type

        if isinstance(command, list):
            actual_command = command

        # helper.build_bootloader_input_packet(
        #     'WA', data_len, current, data)
        try:
            self._communicator.write(actual_command, True)
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
            self._communicator, listen_packet, 12, 200, payload_length_format)

        # response = helper.read_untils_have_data(
        #     self._communicator, 'WA', 12, 10)
        # wait WA end if cannot read response in defined retry times
        if response is None:
            self.emit(UPGRADE_EVENT.ERROR, self._key,
                      'Fail in write block data')
        return True

    def work(self):
        '''Upgrades firmware of connected device to file provided in argument
        '''
        if self._is_stopped:
            return
        if self.current == 0 and self.total == 0:
            self.emit(UPGRADE_EVENT.ERROR, self._key, 'Invalid file content')
            return

        # TODO: move to before write
        # self._communicator.serial_port.baudrate = self._baudrate
        # self._communicator.serial_port.reset_input_buffer()
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

        try:
            self.emit(UPGRADE_EVENT.AFTER_WRITE)
        except Exception as ex:
            self.emit(UPGRADE_EVENT.ERROR, self._key,
                      'Fail in after write: {0}'.format(ex))
            return

        if self.total > 0 and self.current >= self.total:
            self.emit(UPGRADE_EVENT.FINISH, self._key)
