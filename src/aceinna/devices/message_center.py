# import asyncio
import sys
import uuid
import threading
import datetime
import time
from .base import EventBase
from ..framework.utils import helper
if sys.version_info[0] > 2:
    from queue import Queue
else:
    from Queue import Queue


class EVENT_TYPE:
    '''
    Event type of Device Message Center
    '''
    ERROR = 'error'
    READ_BLOCK = 'read_block'
    CONTINUOUS_MESSAGE = 'continuous_message'
    CRC_FAILURE = 'crc_failure'


class DeviceMessage(EventBase):
    def __init__(self, message_center, command, timeout=1):
        super(DeviceMessage, self).__init__()
        self.message_id = None
        self.result = None
        self._message_center = message_center
        self._command = command
        # self._packet_type = packet_type
        self._status = ''
        self._start_time = None
        self._timeout = timeout
        self._is_finished = False

    def send(self):
        self._message_center.request_run(self)

    def finish(self, **kwargs):
        if not self._is_finished:
            self._is_finished = True
            self.emit('finished', **kwargs)

    def set_status(self, status):
        self._status = status

    def set_start_time(self, start_time):
        self._start_time = start_time

    def get_start_time(self):
        return self._start_time

    def get_command(self):
        return self._command

    def get_timeout(self):
        return self._timeout

    def get_finished(self):
        return self._is_finished


class DeviceMessageCenter(EventBase):
    '''
    Device message center, it handles status of message, and also work as a message factory
    '''

    def __init__(self, communicator):
        super(DeviceMessageCenter, self).__init__()
        self.threads = []
        self._communicator = communicator
        self._is_stop = False
        self._is_pause = False
        self._has_exception = False
        self.data_queue = Queue()  # data container
        self.data_lock = threading.Lock()
        self.exception_lock = threading.Lock()
        self._is_running = False
        self.prerun_queue = Queue()
        self._parser = None
        self._running_message = None
        self._is_ready = False
        self._has_running_checker = False
        self._last_timeout_command = None
        self._run_id = None
        self.loop = None

    def is_ready(self):
        '''Check if message center is setuped
        '''
        return self._is_ready

    def set_parser(self, parser):
        self._parser = parser
        self._parser.on('crc_failure', self.on_crc_failure)
        self._parser.on('command', self.on_command_receive)
        self._parser.on('continuous_message',
                        self.on_continuous_messageReceive)

    def get_parser(self):
        return self._parser

    def build(self, command, timeout=3):
        return DeviceMessage(self, command, timeout)

    def request_run(self, message):
        if self._is_running:
            self.prerun_queue.put(message)
        else:
            self.run(message)

    def run(self, message):
        if not self._is_running:
            self._run_id = str(uuid.uuid1())

        self._is_running = True
        self._running_message = message
        message.set_start_time(datetime.datetime.now())

        self._parser.set_run_command(message.get_command())
        self._communicator.write(message.get_command())
        # print('run command', message.get_command())

    def run_post(self):
        if self.prerun_queue.empty():
            self._is_running = False
            self._run_id = None
        else:
            next_message = self.prerun_queue.get()
            self.run(next_message)
        # print('post')

    def setup(self):
        if not self._has_running_checker:
            thread = threading.Thread(target=self.thread_running_checker)
            thread.start()
            self._has_running_checker = True

        # setup receiver, parser
        funcs = [self.thread_receiver, self.thread_parser]
        for func in funcs:
            thread = threading.Thread(target=func)
            thread.start()
            self.threads.append(thread)

        self._is_ready = True

    def pause(self):
        self._is_pause = True

    def resume(self):
        self._has_exception = False
        self._is_pause = False
        helper.clear_elements(self.threads)

    def stop(self):
        self._is_stop = True
        # if self.loop:
        #     self.loop.close()

    def timeout_check(self):
        if self._is_running:
            timeout = self._running_message.get_timeout()
            start_time = self._running_message.get_start_time()
            current_time = datetime.datetime.now()

            span = current_time - start_time
            if span.total_seconds() > timeout and not \
                    self._running_message.get_finished():
                timeout_command = self._running_message.get_command()
                print('command timeout',
                      timeout_command,
                      timeout, start_time, current_time)
                packet_info = self._parser.get_packet_info(
                    timeout_command)
                self._last_timeout_command = packet_info
                self._last_timeout_command['run_id'] = self._run_id
                self._running_message.finish(
                    error='Timeout', **packet_info)
                # print('timeout')
                self.run_post()

    def thread_running_checker(self):
        '''
        Check running status
        '''
        # if sys.version_info[0] > 2:
        #     import asyncio
        #     self.loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(self.loop)

        while True:
            self.exception_lock.acquire()
            if self._has_exception:
                self.emit(EVENT_TYPE.ERROR, 'app', 'communicator read error')
            self.exception_lock.release()

            # Exit running checker
            if self._is_stop:
                return

            self.timeout_check()

            try:
                time.sleep(0.1)
            except KeyboardInterrupt:  # response for KeyboardInterrupt such as Ctrl+C
                return True

    def thread_receiver(self, *args, **kwargs):
        ''' receive data and push data into data_queue.
            return when occur Exception or set as stop
        '''
        while True:
            if self._has_exception or self._is_stop:
                return

            if self._is_pause:
                time.sleep(0.1)
                continue

            data = None
            try:
                data = self._communicator.read(1000)
            except Exception as ex:  # pylint: disable=broad-except
                print('Thread:receiver error:', ex)
                self.exception_lock.acquire()
                self._has_exception = True  # Notice thread paser to exit.
                self.exception_lock.release()
                return  # exit thread receiver

            if data and len(data) > 0:
                self.emit(EVENT_TYPE.READ_BLOCK, data)
                self.data_lock.acquire()
                for data_byte in data:
                    self.data_queue.put(data_byte)
                self.data_lock.release()
            else:
                time.sleep(0.001)

    def thread_parser(self, *args, **kwargs):
        ''' get data from data_queue and parse data into one whole frame.
            return when occur Exception or set as stop.
        '''
        # if sys.version_info[0] > 2:
        #     import asyncio
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)
        while True:
            if self._has_exception or self._is_stop:
                return

            self.exception_lock.acquire()
            if self._has_exception:
                self.exception_lock.release()
                return  # exit thread parser
            self.exception_lock.release()

            if self._is_pause:
                time.sleep(0.1)
                continue

            self.data_lock.acquire()
            if self.data_queue.empty():
                self.data_lock.release()
                time.sleep(0.001)
                continue
            else:
                data = self.data_queue.get()
                self.data_lock.release()

            if self._parser:
                if sys.version_info[0] < 3:
                    data = ord(data)
                self._parser.analyse(data)

    def on_command_receive(self, *args, **kwargs):
        # TODO: should do timeout command check
        if self._running_message:
            self._running_message.finish(**kwargs)
        self.run_post()

    def on_continuous_messageReceive(self, *args, **kwargs):
        # save data
        self.emit(EVENT_TYPE.CONTINUOUS_MESSAGE, **kwargs)

    def on_crc_failure(self, *args, **kwargs):
        self.emit(EVENT_TYPE.CRC_FAILURE, **kwargs)
