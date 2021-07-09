import time
import json

class EthernetDataLogger:
    def __init__(self, properties, communicator, log_writer):
        self.log_writer = log_writer
        self.log_conn = None


    def run(self):
        ''' start to log data from lan port '''
        self._read_and_write()

    def _read_and_write(self):
        if self.log_conn is None:
            return
        while True:
            read_data = self.communicator.read(1024)
            if read_data:
                self.communicator.write(read_data)
        pass

class EthernetDebugDataLogger:
    def __init__(self, properties, communicator, log_writer):
        self.log_writer = log_writer
        self.log_conn = None

    def run(self):
        ''' start to log data from lan port '''
        self._read_and_write()

    def _read_and_write(self):
        # send get configuration
        if self.log_conn is None:
            return
        while True:
            read_data = self.communicator.read(1024)
            if read_data:
                self.communicator.write(read_data)
        pass


class EthernetRTCMDataLogger:
    def __init__(self, properties, communicator, log_writer):
        self.log_writer = log_writer

    def run(self):
        #print('start to log data from lan port')
        self._read_and_write()

    def _read_and_write(self):
        # send get configuration
        print('------------------------------------------------------------')
        while True:
            read_data = self.communicator.read(1024)
            if read_data:
                self.communicator.write(read_data)
        pass
