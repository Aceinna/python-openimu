class SocketConnWrapper:
    def __init__(self, socket_conn):
        self.socket_conn = socket_conn
        # self.timeout = 0.01

    def write(self, data):
        if isinstance(data, str):
            self.socket_conn.send(data.encode('utf-8'))
        else:
            self.socket_conn.send(bytes(data))

    def read(self, size):
        # TODO: should have a timeout policy
        return self.socket_conn.recv(size)