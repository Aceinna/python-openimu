import time
import threading
from .base import EventBase


class UpgradeCenter(EventBase):
    def __init__(self):
        super(UpgradeCenter, self).__init__()
        self.workers = {}
        self.run_status = []
        self.is_processing = False
        self.is_error = False
        self.current = 0
        self.total = 0
        self.data_lock = threading.Lock()

    def register(self, worker):
        worker_key = 'worker-' + str(len(self.workers))
        worker.key = worker_key
        self.workers[worker_key] = {'executor': worker, 'current': 0}
        self.total += worker.get_upgrade_content_size()

    def register_workers(self, workers):
        for worker in workers:
            self.register(worker)

    def start(self):
        if self.is_processing:
            print('upgrade is in processing...')
            return False

        self.is_processing = True
        for worker in self.workers.values():
            '''start thread to invoke worker's work
            '''
            executor = worker['executor']

            thead = threading.Thread(
                target=self.thread_start_worker, args=(executor,))
            thead.start()
        return True

    def stop(self):
        for worker in self.workers.values():
            worker['executor'].stop()

        self.is_processing = False

    def thread_start_worker(self, executor):
        executor.on('progress', self.handle_worker_progress)
        executor.on('error', self.handle_worker_error)
        executor.on('finish', self.handle_worker_done)
        executor.work()

    def handle_worker_progress(self, worker_key, current, total):
        ''' on single worker progress
        '''
        last_current = self.current
        self.current = 0

        self.data_lock.acquire()

        self.workers[worker_key]['current'] = current
        for worker in self.workers.values():
            self.current += worker['current']

        self.data_lock.release()
        step = self.current-last_current

        self.emit('progress', step, self.current, self.total)

    def handle_worker_error(self, worker_key, message):
        ''' on worker error
        '''
        # notifiy other workers to stop upgrade
        for worker in self.workers.values():
            worker['executor'].stop()

        self.emit('error', message)

    def handle_worker_done(self, worker_key):
        ''' on worker progress
            should check if all workers is done
        '''
        self.run_status.append(worker_key)
        # print('{0} worker finished'.format(worker_key))

        if len(self.run_status) == len(self.workers):
            # wait a time, output data to client
            time.sleep(.5)
            self.emit('finish')
