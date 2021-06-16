from socket import *
import concurrent.futures as futures
import time
import base64
from ...framework.context import APP_CONTEXT
from ...core.gnss import RTCMParser
from ...core.event_base import EventBase


class NTRIPClient(EventBase):
    def __init__(self, properties, communicator):
        super(NTRIPClient, self).__init__()

        self.parser = RTCMParser()
        self.parser.on('parsed', self.handle_parsed_data)
        self.communicator = communicator
        self.isConnected = 0
        for x in properties["initial"]["ntrip"]:
            if x['name'] == 'ip':
                self.ip = x["value"]
            elif x['name'] == 'port':
                self.port = x["value"]
            elif x['name'] == 'mountPoint':
                self.mountPoint = x["value"]
            elif x['name'] == 'username':
                self.username = x["value"]
            elif x['name'] == 'password':
                self.password = x["value"]

    def run(self):
        APP_CONTEXT.get_print_logger().info('NTRIP run..')
        while True:
            while True:
                if self.communicator.can_write():
                    time.sleep(3)
                    self.isConnected = self.doConnect()
                    if self.isConnected == 0:
                        time.sleep(3)
                    else:
                        break
                else:
                    time.sleep(1)
            recvData = self.recvResponse()
            # print(recvData)
            if recvData != None and recvData.find('ICY 200 OK') != -1:
                print('NTRIP:[request] ok')
                APP_CONTEXT.get_print_logger().info('NTRIP:[request] ok')
                self.recv()
            else:
                print('NTRIP:[request] fail')
                APP_CONTEXT.get_print_logger().info('NTRIP:[request] fail')
                self.tcpClientSocket.close()

    def doConnect(self):
        self.isConnected = 0
        self.tcpClientSocket = socket(AF_INET, SOCK_STREAM)
        try:
            print('NTRIP:[connect] {0}:{1} start...'.format(
                self.ip, self.port))
            APP_CONTEXT.get_print_logger().info(
                'NTRIP:[connect] {0}:{1} start...'.format(self.ip, self.port))

            self.tcpClientSocket.connect((self.ip, self.port))
            print('NTRIP:[connect] ok')
            APP_CONTEXT.get_print_logger().info('NTRIP:[connect] ok')

            self.isConnected = 1
        except Exception as e:
            print('NTRIP:[connect] {0}'.format(e))
            APP_CONTEXT.get_print_logger().info(
                'NTRIP:[connect] {0}'.format(e))

        if self.isConnected == 1:
            # send ntrip request
            ntripRequestStr = 'GET /' + self.mountPoint + ' HTTP/1.1\r\n'
            ntripRequestStr = ntripRequestStr + 'User-Agent: NTRIP PythonDriver/0.1\r\n'
            ntripRequestStr = ntripRequestStr + 'Authorization: Basic '
            apikey = self.username + ':' + self.password
            apikeyBytes = apikey.encode("utf-8")
            ntripRequestStr = ntripRequestStr + \
                base64.b64encode(apikeyBytes).decode("utf-8")
            ntripRequestStr = ntripRequestStr + '\r\n\r\n'
            # print(ntripRequestStr)
            self.send(ntripRequestStr)
        return self.isConnected

    def send(self, data):
        if self.isConnected:
            try:
                if isinstance(data, str):
                    self.tcpClientSocket.send(data.encode('utf-8'))
                else:
                    self.tcpClientSocket.send(bytes(data))
            except Exception as e:
                print('NTRIP:[send] error occur {0}'.format(e))

                APP_CONTEXT.get_print_logger().info(
                    'NTRIP:[send] {0}'.format(e))

        else:
            return

    def recv(self):
        self.tcpClientSocket.settimeout(10)
        while True:
            try:
                data = self.tcpClientSocket.recv(1024)
                if data:
                    APP_CONTEXT.get_print_logger().info(
                        'NTRIP:[recv] rxdata {0}'.format(len(data)))
                    # print('NTRIP:[recv] rxdata {0}'.format(len(data)))
                    self.parser.receive(data)
                    # if self.communicator.can_write():
                    #     self.communicator.write(data)
                    # else:
                    #     print('NTRIP:[recv] uart error occur')
                    #     APP_CONTEXT.get_print_logger().info('NTRIP:[recv] uart error occur')
                    #     self.tcpClientSocket.close()
                    #     return
                else:
                    print('NTRIP:[recv] no data error')
                    APP_CONTEXT.get_print_logger().info(
                        'NTRIP:[recv] no data error')
                    self.tcpClientSocket.close()
                    return

            except Exception as e:
                print('NTRIP:[recv] error occur {0}'.format(e))
                APP_CONTEXT.get_print_logger().info(
                    'NTRIP:[recv] error occur {0}'.format(e))
                self.tcpClientSocket.close()
                return

    def recvResponse(self):
        self.tcpClientSocket.settimeout(3)
        while True:
            try:
                data = self.tcpClientSocket.recv(1024)
                if data:
                    return data.decode('utf-8')
                else:
                    print('NTRIP:[recvR] no data')
                    return
            except Exception as e:
                print('NTRIP:[recvR] error occur {0}'.format(e))
                APP_CONTEXT.get_print_logger().info(
                    'NTRIP:[recvR] error occur {0}'.format(e))
                return

    def handle_parsed_data(self, data):
        combined_data = []
        for item in data:
            combined_data += item
        self.emit('parsed', combined_data)
