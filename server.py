import tornado.websocket
import tornado.ioloop
import tornado.httpserver
import tornado.web
import json
import time
import math
import os
from global_vars import imu 

server_version = '1.0 Beta'

callback_rate = 50

class WSHandler(tornado.websocket.WebSocketHandler):
        
    def open(self):
        self.callback = tornado.ioloop.PeriodicCallback(self.send_data, callback_rate)
        self.callback.start()
        
    def send_data(self):
        if not imu.paused:
            d = imu.get_latest()
            self.write_message(json.dumps({ 'messageType' : 'event',  'data' : { 'newOutput' : d }}))
        else:
            return False

    def on_message(self, message):
        global imu
        message = json.loads(message)
        # Except for a few exceptions stop the automatic message transmission if a message is received
        if message['messageType'] != 'serverStatus' and list(message['data'].keys())[0] != 'startLog' and list(message['data'].keys())[0] != 'stopLog':
            self.callback.stop()
            imu.pause()
        if message['messageType'] == 'serverStatus':
            if imu.logging:
                fileName = imu.logger.user['fileName']
            else:
                fileName = ''
            # Load the openimu.json on each request to support dynamic debugging
            with open('openimu.json') as json_data:
                imu.imu_properties = json.load(json_data)
            self.write_message(json.dumps({ 'messageType' : 'serverStatus', 'data' : { 'serverVersion' : server_version, 'serverUpdateRate' : callback_rate,  'packetType' : imu.packet_type,
                                                                                        'deviceProperties' : imu.imu_properties, 'deviceId' : imu.device_id, 'logging' : imu.logging, 'fileName' : fileName }}))
        elif message['messageType'] == 'requestAction':
            if list(message['data'].keys())[0] == 'gA':
                print('requesting')
                data = imu.openimu_get_all_param()
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "gA" : data }}))
            elif list(message['data'].keys())[0] == 'uP':
                data = imu.openimu_update_param(message['data']['uP']['paramId'], message['data']['uP']['value'])
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "uP" : data }}))
            elif list(message['data'].keys())[0] == 'sC':
                imu.openimu_save_config()
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "sC" : {} }}))
            # added by dave, for connect page to show version
            elif list(message['data'].keys())[0] == 'gV':
                data = imu.openimu_get_user_app_id()
                self.write_message(json.dumps({ "messageType" : "completeAction", "data" : { "gV" : str(data) }}))
            elif list(message['data'].keys())[0] == 'startStream':
                imu.connect()
                self.callback.start()  
            elif list(message['data'].keys())[0] == 'stopStream':
                imu.pause()
            elif list(message['data'].keys())[0] == 'startLog' and imu.logging == 0: 
                data = message['data']['startLog']
                imu.start_log(data)
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "logfile" : imu.logger.name }}))
            elif list(message['data'].keys())[0] == 'stopLog' and imu.logging == 1: 
                imu.stop_log()                
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "logfile" : '' }}))
            # added by Dave, app download page
            elif list(message['data'].keys())[0] == 'upgradeFramework':
                fileName = message['data']['upgradeFramework']
                if imu.openimu_upgrade_fw_prepare(fileName):
                    while not imu.openimu_finish_upgrade_fw():
                        imu.openimu_upgrade_fw(fileName)
                        self.write_message(json.dumps({ "messageType" : "processAction", "data" : { "addr" : imu.addr, "fs_len": imu.fs_len }}))
                    imu.openimu_start_app()
                self.write_message(json.dumps({ "messageType" : "completeAction", "data" : { "upgradeFramework" : fileName }}))

        # OLD CODE REVIEW FOR DELETION
        elif  0 and message['messageType'] == 'requestAction':
            # Send and receive file list from local server
            if list(message['data'].keys())[0] == 'listFiles':
                logfiles = [f for f in os.listdir('data') if os.path.isfile(os.path.join('data', f)) and f.endswith(".csv")]
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "listFiles" : logfiles }}))
            elif list(message['data'].keys())[0] == 'loadFile':
                print(message['data']['loadFile']['graph_id'])
                f = open("data/" + message['data']['loadFile']['graph_id'],"r")
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "loadFile" :  f.read() }}))

    def on_close(self):
        self.callback.stop()
        return False

    def check_origin(self, origin):
        return True
 
if __name__ == "__main__":
    # Create IMU
    imu.find_device()    
    # Set up Websocket server on Port 8000
    # Port can be changed
    application = tornado.web.Application([(r'/', WSHandler)])
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8000)
    tornado.ioloop.IOLoop.instance().start()
    
