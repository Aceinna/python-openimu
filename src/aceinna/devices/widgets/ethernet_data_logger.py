import time
import json

class EthernetDataLogger:
    def __init__(self, properties, communicator, log_writer):
        self.log_writer = log_writer
        self.communicator = communicator

    def run(self):
        ''' start to log data from Ethernet '''
        print('start to log data from Ethernet\n')
        self._read_and_write()

    def _read_and_write(self):
        while True:
            read_data = self.communicator.read()
            if read_data:
                self.log_writer.write(read_data)
        pass

class EthernetDebugDataLogger:
    def __init__(self, properties, communicator, log_writer):
        self.log_writer = log_writer
        self.communicator = communicator

    def run(self):
        ''' start to log data from lan port '''
        print('start to log debug data from Ethernet\n')
        self._read_and_write()

    def _read_and_write(self):
        # send get configuration
        while True:
            try:
                read_data = self.communicator.read()
                if read_data:
                    self.log_writer.write(read_data)
            except Exception as e:
                print('Data Log Failed, exit')
        pass


class EthernetRTCMDataLogger:
    def __init__(self, properties, communicator, log_writer):
        self.log_writer = log_writer
        self.communicator = communicator

    def run(self):
        print('start to log RTCM data from Ethernet\n')
        self._read_and_write()

    def _read_and_write(self):
        # send get configuration
        print('------------------------------------------------------------')
        while True:
            try:
                read_data = self.communicator.read()
                if read_data:
                    self.log_writer.write(read_data)
            except Exception as e:
                print('Data Log Failed, exit')
        pass
