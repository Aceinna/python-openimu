from abc import ABCMeta, abstractmethod


class DeviceBase(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        self._params = None

    @abstractmethod
    def handle_command(self, cli):
        '''handle command line, and response'''

    @abstractmethod
    def gen_sensor_data(self):
        '''a generator to prepare sensor packet data'''

    def _find_parameter(self, name):
        params_values = self._params.values()
        for item in params_values:
            if item.name == name:
                return item

        return None
