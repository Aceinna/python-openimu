import socket
import time
import json
from ...framework.wrapper import SocketConnWrapper

class LanDataLogger:
    def __init__(self, properties, communicator, log_writer):
        self.host = communicator.host
        self.port = 2204
        self.log_writer = log_writer

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
        self.log_conn.write('get configuration\r\n'.encode())

        for _ in range(try_times): 
            data_buffer = self.log_conn.read(500)
            if len(data_buffer):
                try:
                    str_data = bytes.decode(data_buffer)
                    json_data= json.loads(str_data)
                    for key in json_data.keys():
                        if key =='openrtk configuration':
                            self.log_writer.write(conf_data)
                            break
                    break
                except Exception as e:
                    pass


        while True:
            read_data = self.log_conn.read(1024)
            self.log_writer.write(read_data)
