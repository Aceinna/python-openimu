from socket import *
import concurrent.futures as futures
import time
import base64

from ...framework.utils import print as print_helper
from ...framework.constants import APP_TYPE
from ...framework.context import APP_CONTEXT
from ...core.gnss import RTCMParser
from ...core.event_base import EventBase


class NTRIPClient(EventBase):
    def __init__(self, properties):
        super(NTRIPClient, self).__init__()

        self.parser = RTCMParser()
        self.parser.on('parsed', self.handle_parsed_data)
        self.is_connected = 0
        self.tcp_client_socket = None
        self.is_close = False
        self.append_header_string= None

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
            if self.is_close:
                if self.tcp_client_socket:
                    self.tcp_client_socket.close()
                self.is_connected = 0
                return

            while True:
                # if self.communicator.can_write():
                time.sleep(3)
                self.is_connected = self.doConnect()
                if self.is_connected == 0:
                    time.sleep(3)
                else:
                    break
                # else:
                #    time.sleep(1)
            recvData = self.recvResponse()

            if recvData != None and recvData.find(b'ICY 200 OK') != -1:
                print_helper.print_on_console('NTRIP:[request] ok', skip_modes=[APP_TYPE.CLI])
                APP_CONTEXT.get_print_logger().info('NTRIP:[request] ok')
                self.recv()
            else:
                print_helper.print_on_console('NTRIP:[request] fail', skip_modes=[APP_TYPE.CLI])
                APP_CONTEXT.get_print_logger().info('NTRIP:[request] fail')
                self.tcp_client_socket.close()

    def set_connect_headers(self, headers:dict):
        self.append_header_string = ''
        for key in headers.keys():
            self.append_header_string += '{0}: {1}\r\n'.format(key, headers[key])

    def clear_connect_headers(self):
        self.append_header_string = None


    def doConnect(self):
        self.is_connected = 0
        self.tcp_client_socket = socket(AF_INET, SOCK_STREAM)
        try:
            print_helper.print_on_console('NTRIP:[connect] {0}:{1} start...'.format(
                self.ip, self.port), skip_modes=[APP_TYPE.CLI])
            APP_CONTEXT.get_print_logger().info(
                'NTRIP:[connect] {0}:{1} start...'.format(self.ip, self.port))

            self.tcp_client_socket.connect((self.ip, self.port))
            print_helper.print_on_console('NTRIP:[connect] ok', skip_modes=[APP_TYPE.CLI])
            APP_CONTEXT.get_print_logger().info('NTRIP:[connect] ok')

            self.is_connected = 1
        except Exception as e:
            print_helper.print_on_console('NTRIP:[connect] {0}'.format(e), skip_modes=[APP_TYPE.CLI])
            APP_CONTEXT.get_print_logger().info(
                'NTRIP:[connect] {0}'.format(e))

        if self.is_connected == 1:
            # send ntrip request
            ntripRequestStr = 'GET /' + self.mountPoint + ' HTTP/1.1\r\n'
            ntripRequestStr += 'User-Agent: NTRIP PythonDriver/0.1\r\n'

            if self.append_header_string:
                ntripRequestStr += self.append_header_string

            ntripRequestStr += 'Authorization: Basic '
            apikey = self.username + ':' + self.password
            apikeyBytes = apikey.encode("utf-8")
            ntripRequestStr += base64.b64encode(apikeyBytes).decode("utf-8")+'\r\n'
            ntripRequestStr += '\r\n'
            # print(ntripRequestStr)
            self.send(ntripRequestStr)
        return self.is_connected

    def send(self, data):
        if self.is_connected:
            try:
                if isinstance(data, str):
                    self.tcp_client_socket.send(data.encode('utf-8'))
                else:
                    self.tcp_client_socket.send(bytes(data))
            except Exception as e:
                print_helper.print_on_console('NTRIP:[send] error occur {0}'.format(e), skip_modes=[APP_TYPE.CLI])
                APP_CONTEXT.get_print_logger().info(
                    'NTRIP:[send] {0}'.format(e))

    def recv(self):
        self.tcp_client_socket.settimeout(10)
        while True:
            if self.is_close:
                return
            try:
                data = self.tcp_client_socket.recv(1024)
                if data:
                    APP_CONTEXT.get_print_logger().info(
                        'NTRIP:[recv] rxdata {0}'.format(len(data)))
                    # print('NTRIP:[recv] rxdata {0}'.format(len(data)))
                    self.parser.receive(data)
                else:
                    print_helper.print_on_console('NTRIP:[recv] no data error', skip_modes=[APP_TYPE.CLI])
                    APP_CONTEXT.get_print_logger().info(
                        'NTRIP:[recv] no data error')
                    self.tcp_client_socket.close()
                    return

            except Exception as e:
                print_helper.print_on_console('NTRIP:[recv] error occur {0}'.format(e), skip_modes=[APP_TYPE.CLI])
                APP_CONTEXT.get_print_logger().info(
                    'NTRIP:[recv] error occur {0}'.format(e))
                self.tcp_client_socket.close()
                return

    def recvResponse(self):
        self.tcp_client_socket.settimeout(3)
        while True:
            try:
                data = self.tcp_client_socket.recv(1024)
                if not data or len(data) == 0:
                    print_helper.print_on_console('NTRIP:[recvR] no data', skip_modes=[APP_TYPE.CLI])
                    return None

                return data
            except Exception as e:
                APP_CONTEXT.get_print_logger().info(
                    'NTRIP:[recvR] error occur {0}'.format(e))
                return None

    def close(self):
        self.append_header_string = None
        self.is_close = True


    def handle_parsed_data(self, data):
        combined_data = []
        for item in data:
            combined_data += item
        self.emit('parsed', combined_data)
