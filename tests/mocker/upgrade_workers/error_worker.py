from aceinna.devices.base import UpgradeWorkerBase


class ErrorWorker(UpgradeWorkerBase):
    def __init__(self):
        super(ErrorWorker, self).__init__()
        self._total = 1024*1024  # 1M size

    def get_upgrade_content_size(self):
        return self._total

    def work(self):
        current = 0
        step = 200
        while current < self._total:
            if self._is_stopped:
                break

            if current > 2000:
                self.emit('error', self._key, 'upgrade failed')
            current += step
            self.emit('progress', self._key, current, self._total)

        if current >= step:
            self.emit('finish', self._key)

    def stop(self):
        self._is_stopped = True
