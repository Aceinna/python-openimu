import sys
import unittest
import threading
import time
from websocket import create_connection

try:
    from aceinna.framework.communicator import SerialPort
except:  # pylint: disable=bare-except
    sys.path.append('./src')
    from aceinna.framework.communicator import SerialPort


# pylint: disable=missing-class-docstring
class TestUARTCommunicator(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_cancel_while_find(self):
        communicator = SerialPort()

        def do_find_device():
            communicator.find_device(lambda provider: {})

        thread = threading.Thread(
            target=do_find_device, args=())
        thread.start()

        time.sleep(1)
        communicator.close()
        self.assertTrue(True, 'Find device')

    # def test_cancel_while_find(self):
    #     self.assertTrue(True, 'Cancel find')

    # def test_create_with_params(self):
    #     self.assertTrue(True, 'Create with parameters')


if __name__ == '__main__':
    unittest.main()
