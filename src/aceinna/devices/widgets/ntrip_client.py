from socket import *
import concurrent.futures as futures
import time
import base64

class NTRIPClient:
    def __init__(self, properties, communicator):
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
        while True:
            while True:
                self.isConnected = self.doConnect()
                if self.isConnected == 0:
                    time.sleep(3)
                else:
                    break
            recvData = self.recvResponse()
            # print(recvData)
            if recvData != None and recvData.find('ICY 200 OK') != -1:
                print('NTRIP:[request] ok')
                self.recv()
            else:
                self.tcpClientSocket.close()
                
    def doConnect(self):
        self.isConnected = 0
        self.tcpClientSocket = socket(AF_INET, SOCK_STREAM)
        try:
            print('NTRIP:[connect] {0}:{1} start...'.format(self.ip, self.port))
            self.tcpClientSocket.connect((self.ip, self.port))
            print('NTRIP:[connect] ok')
            self.isConnected = 1
        except Exception as e:
            print('NTRIP:[connect] {0}'.format(e))
        if self.isConnected == 1:
            # send ntrip request
            ntripRequestStr = 'GET /' + self.mountPoint + ' HTTP/1.1\r\n'
            ntripRequestStr = ntripRequestStr + 'User-Agent: NTRIP Aceinna/0.1\r\n'
            ntripRequestStr = ntripRequestStr + 'Authorization: Basic '
            apikey = self.username + ':' + self.password
            apikeyBytes = apikey.encode("utf-8")
            ntripRequestStr = ntripRequestStr + base64.b64encode(apikeyBytes).decode("utf-8")
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
        else:
            return

    def recv(self):
        self.tcpClientSocket.settimeout(None)
        while True:
            try:
                data = self.tcpClientSocket.recv(1024)
                if data:
                    self.communicator.write(data)
            except Exception as e:
                print('NTRIP:[recv] error occur {0}'.format(e))
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
                    return
            except Exception as e:
                print('NTRIP:[recv] error occur {0}'.format(e))
                return
                