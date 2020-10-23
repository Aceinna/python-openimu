from abc import ABCMeta, abstractmethod


class DeviceBase(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def handle_command(self, cli):
        '''handle command line, and response'''

    @abstractmethod
    def gen_sensor_data(self):
        '''a generator to prepare sensor packet data'''
