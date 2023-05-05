import sys
import unittest
import threading
import time

try:
    from aceinna.devices.upgrade_workers import (LockWorker)
    from aceinna.tools.detector import (Detector)
    from aceinna.framework.utils import helper
except:
    sys.path.append('./src')
    from aceinna.devices.upgrade_workers import (LockWorker)
    from aceinna.tools.detector import (Detector)
    from aceinna.framework.utils import helper


class TestLockWorker(unittest.TestCase):
    def _on_find_device_for_unlock(self, provider):
        provider.setup(None)
        provider._message_center.pause()
        time.sleep(1)
        unlock_application_command = helper.build_packet('UA', [0x92,0x33,0x62,0x19,0x64,0x27,0x42,0x85])
        unlock_worker = LockWorker(provider=provider, commands=[
            {'command':unlock_application_command, 'check':{'field': 0x22, 'after_value': 0}}
        ])
        unlock_worker.work()
        provider.close()

    def _start_find_device_for_unlock(self):
        detector = Detector(
            device_type='DMU',
            baudrate=115200
        )
        detector.find(self._on_find_device_for_unlock)

    def test_unlock(self):
        threading.Thread(target=self._start_find_device_for_unlock).start()
        #self.assertTrue(isinstance(instance, DefaultApp))


if __name__ == '__main__':
    unittest.main()
