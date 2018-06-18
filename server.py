import tornado.websocket
import tornado.ioloop
import tornado.httpserver
import tornado.web
import json
import time
import math
import threading
import os
from openimu import OpenIMU

server_version = '1.0 Beta'

callback_rate = 50

class WSHandler(tornado.websocket.WebSocketHandler):
            
    def open(self):
        self.__time = 1
        self.callback = tornado.ioloop.PeriodicCallback(self.send_data, callback_rate)
        self.callback.start()
        
    def send_data(self):
        if imu.connect and imu.stream_mode:
            d = imu.get_latest()
            self.write_message(json.dumps({ 'messageType' : 'event',  'data' : { 'newOutput' : d }}))

    def on_message(self, message):
        global imu
        message = json.loads(message)
        # Except for a few exceptions stop the automatic message transmission if a message is received
        if message['messageType'] != 'serverStatus' and list(message['data'].keys())[0] != 'startLog' and list(message['data'].keys())[0] != 'stopLog':
            self.callback.stop()
            time.sleep(1)
        if message['messageType'] == 'serverStatus':
            if imu.logging:
                fileName = imu.logger.user['fileName']
            else:
                fileName = ''
            if 1:
            #if imu.device_id:
                self.write_message(json.dumps({ 'messageType' : 'serverStatus', 'data' : { 'serverVersion' : server_version, 'serverUpdateRate' : callback_rate, 'packetType' : imu.packet_type,
                                                                                            'deviceId' : imu.device_id, 'deviceProperties' : imu.imu_properties, 'logging' : imu.logging, 'fileName' : fileName }}))
            else:
                self.write_message(json.dumps({ 'messageType' : 'serverStatus', 'data' : { 'serverVersion' : server_version, 'serverUpdateRate' : callback_rate,
                                                                                            'deviceId' : imu.device_id, 'logging' : imu.logging, 'fileName' : fileName }}))
        elif message['messageType'] == 'requestAction':
            if list(message['data'].keys())[0] == 'getFields':
                data = imu.get_fields(list(map(int,message['data']['getFields'].keys())), True)
                print('get fields new')
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "getFields" : data }}))
                print(data)
                imu.restore_odr()
            elif list(message['data'].keys())[0] == 'readFields':
                data = imu.read_fields(list(map(int,message['data']['readFields'].keys())), True)
                print('read fields new')
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "readFields" : data }}))
                print(data)
                imu.restore_odr()
            elif list(message['data'].keys())[0] == 'setFields':
                setData = zip(list(map(int,message['data']['setFields'].keys())), list(map(int,message['data']['setFields'].values())))
                print('set fields new')
                print(setData)
                data = imu.set_fields(setData, True)
                # should be improved to really use data readback in UART protocol, and cross check values set correctly
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "setFields" : setData }}))
                imu.restore_odr()
            elif list(message['data'].keys())[0] == 'writeFields':
                setData = zip(list(map(int,message['data']['writeFields'].keys())), list(map(int,message['data']['writeFields'].values())))
                print('write fields new')
                print(setData)
                data = imu.write_fields(setData, True)
                # should be improved to really use data readback in UART protocol, and cross check values set correctly
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "writeFields" : setData }}))
                imu.restore_odr()
            elif list(message['data'].keys())[0] == 'startStream':
                imu.restore_odr()
                self.callback.start()  
            elif list(message['data'].keys())[0] == 'stopStream':
                imu.set_quiet()
            elif list(message['data'].keys())[0] == 'startLog' and imu.logging == 0: 
                data = message['data']['startLog']
                imu.start_log(data) 
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "logfile" : imu.logger.name }}))
            elif list(message['data'].keys())[0] == 'stopLog' and imu.logging == 1: 
                imu.stop_log()                
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "logfile" : '' }}))
            elif list(message['data'].keys())[0] == 'listFiles':
                logfiles = [f for f in os.listdir('data') if os.path.isfile(os.path.join('data', f)) and f.endswith(".csv")]
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "listFiles" : logfiles }}))
            elif list(message['data'].keys())[0] == 'loadFile':
                print(message['data']['loadFile']['graph_id'])
                f = open("data/" + message['data']['loadFile']['graph_id'],"r")
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "loadFile" :  f.read() }}))


    def on_close(self):
        self.callback.stop()

    def check_origin(self, origin):
        return True
 
if __name__ == "__main__":
    # Create IMU
    imu = OpenIMU(ws=True)
    # Place IMU in thread and ask it to connect itself 
    threading.Thread(target=imu.connect).start()
    
    # Set up Websocket server on Port 8000
    # Port can be changed
    application = tornado.web.Application([(r'/', WSHandler)])
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8000)
    tornado.ioloop.IOLoop.instance().start()
    