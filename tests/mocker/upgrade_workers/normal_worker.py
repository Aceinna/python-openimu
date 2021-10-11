from aceinna.devices.base import UpgradeWorkerBase
from aceinna.devices.upgrade_workers import UPGRADE_GROUP


class NormalWorker(UpgradeWorkerBase):
    def __init__(self):
        super(NormalWorker, self).__init__()
        self._total = 1024*1024  # 1M size
        self._group = UPGRADE_GROUP.FIRMWARE

    def get_upgrade_content_size(self):
        return self._total

    def work(self):
        current = 0
        step = 1000
        while current < self._total:
            if self._is_stopped:
                break
            current += step
            self.emit('progress', self._key, current, self._total)

        if current >= step:
            self.emit('finish', self._key)

    def stop(self):
        self._is_stopped = True
