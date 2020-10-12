import sys
import unittest
import threading
import time

try:
    from aceinna.devices import DeviceManager
    from aceinna.framework.communicator import SerialPort
except:  # pylint: disable=bare-except
    sys.path.append('./src')
    from aceinna.devices import DeviceManager
    from aceinna.framework.communicator import SerialPort


# pylint: disable=missing-class-docstring
class TestDeviceManager(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_ping(self):
        pass
        # communicator = SerialPort()
        # DeviceManager.ping(connection)

    # def test_cancel_while_find(self):
    #     self.assertTrue(True, 'Cancel find')

    # def test_create_with_params(self):
    #     self.assertTrue(True, 'Create with parameters')


if __name__ == '__main__':
    unittest.main()
