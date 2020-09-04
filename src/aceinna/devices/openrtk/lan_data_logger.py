import socket
import time
import json
from ...framework.wrapper import SocketConnWrapper


class LanDataLogger:
    def __init__(self, properties, communicator, log_writer):
        self.host = communicator.host
        self.port = 2204
        self.log_writer = log_writer
        self.log_conn = None
        self.sock = None

    def run(self):
        ''' start to log data from lan port '''
        self._connect()
        self._read_and_write()

    def _connect(self):
        # establish TCP Server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)

        # wait for client
        conn, addr = self.sock.accept()
        self.log_conn = SocketConnWrapper(conn)

    def _read_and_write(self):
        # send get configuration
        if self.log_conn is None:
            return

        self.log_conn.write('get configuration\r\n'.encode())
        try_times = 20
        for _ in range(try_times):
            data_buffer = self.log_conn.read(500)
            if data_buffer is not None:
                try:
                    str_data = bytes.decode(data_buffer)
                    json_data = json.loads(str_data)
                    for key in json_data.keys():
                        if key == 'openrtk configuration':
                            self.log_writer.write(data_buffer)
                            break
                    break
                except Exception as e:
                    pass
        
        self.log_conn.write('log debug on\r\n'.encode())
        while True:
            try:
                read_data = self.log_conn.read(1024)
                self.log_writer.write(read_data)
            except Exception as e:
                print('Data Log Failed, exit')
