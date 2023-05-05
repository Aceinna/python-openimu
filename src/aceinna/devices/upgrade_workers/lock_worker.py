from array import array
import time

from ..base.upgrade_worker_base import UpgradeWorkerBase
from ...framework.utils import helper
from ...framework.command import Command
from . import (UPGRADE_EVENT, UPGRADE_GROUP)
from ..parsers import dum_packet_parser


class LockWorker(UpgradeWorkerBase):
    '''Firmware upgrade worker
    '''
    __provider = None
    __commands = None
    _listen_packet = None
    _wait_timeout_after_command = 3

    def __init__(self, provider, *args, **kwargs):
        super(LockWorker, self).__init__()
        self.__provider = provider
        self.__communicator = provider.communicator
        self.current = 0
        self.total = 0
        self._group = UPGRADE_GROUP.FIRMWARE

        if kwargs.get('commands'):
            self.__commands = kwargs.get('commands')

    def stop(self):
        self._is_stopped = True

    def get_upgrade_content_size(self):
        return self.total

    def read_dmu_parameter(self, field_id):
        get_field_command = helper.build_packet(
            'GF', [1, 0, field_id])
        self.__communicator.reset_buffer()
        self.__communicator.write(get_field_command)
        response = helper.read_untils_have_data(
            self.__communicator, 'GF', 1000, 20)

        if response is None:
            return None

        get_param_result, error = dum_packet_parser.read_field_parser(
            response)

        if error:
            return None

        return get_param_result[0]['value']

    def work(self):
        if self._is_stopped:
            return

        # get field value from self.__commands
        if self.__commands:
            # check if the value equals after_value
            # if not, send command to field
            # get field value from self.__commands again, and check if the value equals after_value
            # if yes, continue to next field
            # else, raise error
            self.emit(UPGRADE_EVENT.BEFORE_COMMAND)

            for item in self.__commands:
                command = item['command']
                check = item['check']

                field_value = self.read_dmu_parameter(check['field'])
                if field_value is None:
                    # raise error
                    self.emit(UPGRADE_EVENT.ERROR, self._key,
                              'Read field {0} failed'.format(check['field']))

                if field_value == 65535 or field_value == check['after_value']:
                    continue

                self.__communicator.write(command)
                time.sleep(3)
                quiet_command = helper.build_packet('SF',[0x01, 0x0,0x1,0x0,0x0])
                self.__communicator.write(quiet_command)
                time.sleep(1)
                #print('after command')
                field_value = self.read_dmu_parameter(check['field'])
                if field_value is None:
                    # raise error
                    self.emit(UPGRADE_EVENT.ERROR, self._key,
                              'Read field {0} failed'.format(check['field']))
                    break

                if field_value != check['after_value']:
                    # raise error
                    self.emit(UPGRADE_EVENT.ERROR, self._key,
                              'Run lock command failed {0}, field:{1}, expect:{2}, actual:{3}'.format(command, check['field'], check['after_value'], field_value))
                    break

            self.emit(UPGRADE_EVENT.AFTER_COMMAND)

        self.emit(UPGRADE_EVENT.FINISH, self._key)
