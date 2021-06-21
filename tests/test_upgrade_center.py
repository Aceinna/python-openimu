import sys
import unittest

try:
    from mocker.upgrade_workers.normal_worker import NormalWorker
    from mocker.upgrade_workers.error_worker import ErrorWorker
    from aceinna.devices.upgrade_center import UpgradeCenter
except:
    sys.path.append('./src')
    sys.path.append('./tests')
    from mocker.upgrade_workers.normal_worker import NormalWorker
    from mocker.upgrade_workers.error_worker import ErrorWorker
    from aceinna.devices.upgrade_center import UpgradeCenter


class TestUpgradeCenter(unittest.TestCase):
    def handle_done(self):
        self.assertTrue(True, 'all works done')

    def handle_progress(self, current, total):
        self.assertTrue(True, 'all works done')

    def handle_error(self, message):
        self.assertTrue(True, 'Encounter error')

    def test_one_worker(self):
        upgrade_center = UpgradeCenter()
        upgrade_center.register(NormalWorker())
        upgrade_center.on('finish', self.handle_done)
        upgrade_center.start()

    def test_start_2_times(self):
        upgrade_center = UpgradeCenter()
        upgrade_center.register(NormalWorker())
        _ = upgrade_center.start()
        second_result = upgrade_center.start()
        self.assertFalse(second_result, 'Cannot start 2 times')

    def test_normal_stop(self):
        upgrade_center = UpgradeCenter()
        normal_worker = NormalWorker()
        upgrade_center.register(normal_worker)
        upgrade_center.start()
        upgrade_center.stop()

        self.assertTrue(normal_worker.is_stopped, 'Worker is stopped')

    def test_more_workers(self):
        upgrade_center = UpgradeCenter()
        upgrade_center.register(NormalWorker())
        upgrade_center.register(NormalWorker())
        upgrade_center.on('finish', self.handle_done)
        upgrade_center.start()

    def test_more_workers_stop(self):
        upgrade_center = UpgradeCenter()
        normal_worker1 = NormalWorker()
        normal_worker2 = NormalWorker()
        upgrade_center.register(normal_worker1)
        upgrade_center.register(normal_worker2)
        upgrade_center.start()
        upgrade_center.stop()
        self.assertEqual(
            [normal_worker1.is_stopped, normal_worker2.is_stopped],
            [True, True])

    def test_with_error_worker(self):
        upgrade_center = UpgradeCenter()
        upgrade_center.register(ErrorWorker())
        upgrade_center.register(NormalWorker())
        upgrade_center.on('error', self.handle_error)
        upgrade_center.start()

    # TODO: test the firmware work with mock communicator
    def test_firmware_worker(self):
        pass


if __name__ == '__main__':
    unittest.main()
