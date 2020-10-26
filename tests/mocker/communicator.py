import sys
import time

from aceinna.framework.communicator import Communicator
from aceinna.framework.utils.helper import dict_to_object
from .device_access import DeviceAccess


class MockCommunicator(Communicator):
    def __init__(self, options=None):
        super(MockCommunicator, self).__init__()
        self.type = 'uart'

        converted_options = dict_to_object(options)
        device_name = getattr(converted_options, 'device', 'IMU')

        self._device_access = DeviceAccess(device_name)
        self._device_access.start()

    @property
    def device_access(self):
        return self._device_access

    def find_device(self, callback):
        # confirm device
        self.confirm_device(self._device_access, None)

        if self.device:
            callback(self.device)

    def open(self):
        pass

    def close(self):
        self._device_access.stop()

    def write(self, data, is_flush=False):
        self._device_access.write(data)

    def read(self, size=100):
        return self._device_access.read(size)
