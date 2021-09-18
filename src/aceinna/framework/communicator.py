"""
Communicator
"""
import os
from abc import ABCMeta, abstractmethod
from ..devices import DeviceManager
from .constants import (BAUDRATE_LIST, INTERFACES)
from .context import APP_CONTEXT
from .utils.resource import get_executor_path


class CommunicatorFactory:
    '''
    Communicator Factory
    '''
    @staticmethod
    def create(method, options):
        '''
        Initial communicator instance
        '''
        if method == INTERFACES.UART:
            from .communicators import SerialPort
            return SerialPort(options)
        elif method == INTERFACES.ETH:
            from .communicators import LAN
            return LAN(options)
        elif method == INTERFACES.ETH_100BASE_T1:
            from .communicators import Ethernet
            return Ethernet(options)
        else:
            raise Exception('no matched communicator')


class Communicator(object):
    '''Communicator base
    '''
    __metaclass__ = ABCMeta

    def __init__(self):
        executor_path = get_executor_path()
        setting_folder_name = 'setting'
        self.setting_folder_path = os.path.join(
            executor_path, setting_folder_name)
        self.connection_file_path = os.path.join(
            self.setting_folder_path, 'connection.json')
        self.read_size = 0
        self.device = None
        self.threadList = []
        self.type = 'Unknown'

    @abstractmethod
    def find_device(self, callback, retries=0, not_found_handler=None):
        '''
        find device, then invoke callback
        '''

    def open(self):
        '''
        open
        '''

    def close(self):
        '''
        close
        '''

    def write(self, data, is_flush=False):
        '''
        write
        '''

    def read(self, size):
        '''
        read
        '''

    def confirm_device(self, *args):
        '''
        validate the connected device
        '''
        device = None
        try:
            device = DeviceManager.ping(self, *args)
        except Exception as ex:
            APP_CONTEXT.get_logger().logger.info('Error while confirm device %s', ex)
            device = None
        if device and not self.device:
            self.device = device
            return True
        return False

