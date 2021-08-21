import sys
import unittest
import threading
import time
from websocket import create_connection

try:
    from aceinna.framework.communicators import SerialPort
except:  # pylint: disable=bare-except
    sys.path.append('./src')
    from aceinna.framework.communicators import SerialPort


# pylint: disable=missing-class-docstring
@unittest.skip
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


if __name__ == '__main__':
    unittest.main()
