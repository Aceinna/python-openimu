import time
import threading
from .base import EventBase
from itertools import groupby
from .upgrade_workers import UPGRADE_EVENT

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
        self.workers[worker_key] = {
            'executor': worker,
            'group': worker.group,
            'current': 0
        }
        self.total += worker.get_upgrade_content_size()

    def register_workers(self, workers):
        for worker in workers:
            self.register(worker)

    def start(self):
        if self.is_processing:
            print('upgrade is in processing...')
            return False

        self.is_processing = True

        # group workers by group name if has
        all_workers = self.workers.values()
        worker_group = groupby(all_workers, key=lambda x: x['group'])
        for key, group in worker_group:
            if key:
                # start thread to run workers in a group
                self.start_workers_in_single_thread(list(group))
            else:
                # start multi thread to run workers in no named group
                self.start_workers_in_multi_thread(list(group))

        return True

    def stop(self):
        for worker in self.workers.values():
            worker['executor'].stop()

        self.is_processing = False

    def start_workers_in_single_thread(self, workers):
        def start_in_thread(workers):
            for worker in workers:
                executor = worker['executor']
                self.start_worker(executor)

        thead = threading.Thread(
            target=start_in_thread, args=(workers,))
        thead.start()

    def start_workers_in_multi_thread(self, workers):
        for worker in workers:
            '''start thread to invoke worker's work
            '''
            executor = worker['executor']

            thead = threading.Thread(
                target=self.start_worker, args=(executor,))
            thead.start()

    def start_worker(self, executor):
        executor.on(UPGRADE_EVENT.PROGRESS, self.handle_worker_progress)
        executor.on(UPGRADE_EVENT.ERROR, self.handle_worker_error)
        executor.on(UPGRADE_EVENT.FINISH, self.handle_worker_done)
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

        self.emit(UPGRADE_EVENT.PROGRESS, step, self.current, self.total)

    def handle_worker_error(self, worker_key, message):
        ''' on worker error
        '''
        # notifiy other workers to stop upgrade
        for worker in self.workers.values():
            worker['executor'].stop()

        self.emit(UPGRADE_EVENT.ERROR, message)

    def handle_worker_done(self, worker_key):
        ''' on worker progress
            should check if all workers is done
        '''
        self.run_status.append(worker_key)
        # print('{0} worker finished'.format(worker_key))

        if len(self.run_status) == len(self.workers):
            # wait a time, output data to client
            time.sleep(.5)
            self.emit(UPGRADE_EVENT.FINISH)
