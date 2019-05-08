import sys
import tornado.websocket
import tornado.ioloop
import tornado.httpserver
import tornado.web
import json
import time
import math
import os
from global_vars import imu 
#123

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

            # load application type from firmware 
            datatype_custimze = imu.openimu_get_user_app_id()
            divide_list = imu.imu_properties['userConfiguration']
            application_type = datatype_custimze[0:7]
            # load package type from json file
            package_type_ListFromOptions = []
            for x in imu.imu_properties['userConfiguration']:
                if x['paramId'] == 3:
                    package_type_ListFromOptions = x['options']
            divide_list[3]['options'] = package_type_ListFromOptions
            # VG-AHRS application
            if bytes.decode(application_type) == 'VG_AHRS':
                divide_list[3]['options'] = ['zT','z1','a1','a2','s1','e1']
            # Compass application
            elif bytes.decode(application_type) == 'Compass':
                divide_list[3]['options'] = ['zT','z1','s1','c1']
            # Framework application
            elif bytes.decode(application_type) == 'OpenIMU':
                divide_list[3]['options'] = ['zT','z1','z2']
            # IMU application
            elif bytes.decode(application_type) == 'IMU 1.0':
                divide_list[3]['options'] = ['zT','z1','z2','s1']
            # INS application
            elif bytes.decode(application_type) == 'INS 1.0':
                divide_list[3]['options'] = ['zT','z1','a1','a2','s1','e1','e2']
            # Lever application    
            elif bytes.decode(application_type) == 'StaticL':
                divide_list[3]['options'] = ['zT','z1','s1','l1']    
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

    def on_close(self):  #
        self.callback.stop()

        # try:
        #     os._exit(0)
        # except:
        #    print('Program is off.')

        return False

    def check_origin(self, origin):
        return True
 
if __name__ == "__main__":
    # Create IMU
    try: 
        imu.find_device()    
        # Set up Websocket server on Port 8000
        # Port can be changed
        application = tornado.web.Application([(r'/', WSHandler)])
        http_server = tornado.httpserver.HTTPServer(application)
        http_server.listen(8000)
        
        tornado.ioloop.IOLoop.instance().start()
    
    except KeyboardInterrupt:  # response for KeyboardInterrupt such as Ctrl+C
        print('User stop this program by KeyboardInterrupt! File:[{0}], Line:[{1}]'.format(__file__, sys._getframe().f_lineno))
        os._exit(1)
    except Exception as e:
        print(e)    

    
