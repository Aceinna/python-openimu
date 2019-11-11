import sys
import tornado.websocket
import tornado.ioloop
import tornado.httpserver
import tornado.web
import json
import time
import math
import os
import logging
from global_vars import imu
import binascii
import global_vars as gl


# note: version string update should follow the updating rule
server_version = '1.1.1'
callback_rate = 50
class WSHandler(tornado.websocket.WebSocketHandler):
    count = 0
    magProgress = 0

    def open(self):
        self.callback = tornado.ioloop.PeriodicCallback(self.send_data, callback_rate)
        self.callback.start()
        self.callback2 = tornado.ioloop.PeriodicCallback(self.detect_status, 500)
        self.callback2.start()

    def detect_status(self):        
        if not imu.read(200):
            self.write_message(json.dumps({ "messageType": "queryResponse","data": {"packetType": "DeviceStatus","packet": { "returnStatus":1}}}))

    def send_data(self):
        if not imu.device_id:            
            self.write_message(json.dumps({ "messageType": "queryResponse","data": {"packetType": "DeviceStatus","packet": { "returnStatus":1}}}))
            time.sleep(1)
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

            # Load the basic openimu.json(IMU application)
            with open('app_config/IMU/openimu.json') as json_data:
                imu.imu_properties = json.load(json_data)
            try:
                application_type = bytes.decode(imu.openimu_get_user_app_id())   
            except Exception as e:
                application_type = "get app id failed, no feedback! pls check your FW right or not"
                print("on_message,get app id error:",e)   
                logging.info("get app id failed, no feedback! pls check your FW right or not. excpetion is:{0}".format(e))        
            # application_type = imu.device_id
            for idx, item in enumerate(gl.app_str):
                if item in application_type:
                    folder_path = gl.string_folder_path.replace('APP_TYP',item)
                    break   
                            
            # load application type from firmware 
            try:
                if imu.paused == 1 and not imu.openimu_get_user_app_id() == None: 
                    with open(folder_path) as json_data:
                            imu.imu_properties = json.load(json_data)
                    js_version_str = imu.imu_properties['app_version'].split(' ')[2]
                    imu.openimu_version_compare(application_type,js_version_str)
                    # imu.imu_properties['userMessages']['outputPackets'][0]['name']
                    # len(imu.imu_properties['userMessages']['outputPackets'])

                    self.write_message(json.dumps({ 'messageType' : 'serverStatus', 'data' : { 'serverVersion' : server_version, 'serverUpdateRate' : callback_rate,  'packetType' : imu.packet_type,
                                                                                                'deviceProperties' : imu.imu_properties, 'deviceId' : imu.device_id, 'logging' : imu.logging, 'fileName' : fileName }}))
                else:
                    self.write_message(json.dumps({ "messageType": "queryResponse","data": {"packetType": "DeviceStatus","packet": { "returnStatus":2}}}))
                    imu.pause()
            except Exception as e:
                # print(e)                 
                self.write_message(json.dumps({ "messageType": "queryResponse","data": {"packetType": "DeviceStatus","packet": { "returnStatus":2}}}))
                logging.info("load JSON file exception:{0}".format(e))
                imu.pause()
        elif message['messageType'] == 'requestAction':
            if list(message['data'].keys())[0] == 'gA':                
                data = imu.openimu_get_all_param()

                # data[7]['value'] = data[3]['value'].strip(b'\x00'.decode())
                time.sleep(0.2)                
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "gA" : data }}))
                logging.debug('{0} feedback: {1}'.format(list(message['data'].keys())[0], data))
                # print('requesting ok ---------------{0}'.format(self.count))                
            elif list(message['data'].keys())[0] == 'uP':
                logging.debug("uP setting, parameter ID:{0}, value is:{1}".format(message['data']['uP']['paramId'], message['data']['uP']['value']))
                data = imu.openimu_update_param(message['data']['uP']['paramId'], message['data']['uP']['value'])
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "uP" : data }}))
            elif list(message['data'].keys())[0] == 'sC':
                logging.debug("sC setting")
                imu.openimu_save_config()
                time.sleep(0.5)
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "sC" : {} }}))
            # added by dave, for connect page to show version
            elif list(message['data'].keys())[0] == 'gV':
                data = imu.openimu_get_user_app_id()
                self.write_message(json.dumps({ "messageType" : "completeAction", "data" : { "gV" : str(data) }}))
                logging.debug('{0} feedback: {1}'.format(list(message['data'].keys())[0], data))

            elif list(message['data'].keys())[0] == 'startStream':  
                logging.debug("start the stream!")                              
                imu.connect()
                self.callback.start()  
                self.callback2.stop()
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "startStream" : {} }}))
            elif list(message['data'].keys())[0] == 'stopStream':
                logging.debug("stop the stream!")
                imu.pause()                
                self.callback2.start()
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "stopStream" : {} }}))
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
        elif message['messageType'] == 'magAction':
            if (list (message['data'].values())[0] == 'start'):
                logging.debug("start magalign") 
                imu.magneticAlignCmd('start')
                self.magProgress = 1
                # print ('mag align started')
                self.write_message(json.dumps({"messageType": "magAction", "data": {"start": {}}}))
            elif (list(message['data'].values())[0] == 'abort'):
                logging.debug("abort magalign") 
                time.sleep(2)
                imu.magneticAlignCmd('abort')
                self.magProgress = 0
                # print ('mag align aborted')
                self.write_message(json.dumps({"messageType": "magAction", "data": {"abort": {}}}))
                return

            elif (list(message['data'].values())[0] == 'status'):
                # status = openIMUMagneticAlign.status()
                logging.debug("status of magalign") 
                if (self.magProgress == 1):
                    status = imu.magneticAlignCmd('status')

                    if status == 1:
                        time.sleep(1)
                        storedValue = imu.magneticAlignCmd('stored')
                        self.write_message(
                            json.dumps({"messageType": "magAction", "data": {"status": "complete", "value": storedValue}}))
                        return
                    self.write_message(json.dumps({"messageType": "magAction", "data": {"status": "incomplete"}}))

            elif (list(message['data'].values())[0] == 'save'):
                logging.debug("save result of magalign") 
                imu.magneticAlignCmd('save')
                time.sleep(1)
                self.magProgress = 0
                data = imu.openimu_get_all_param()
                self.write_message(json.dumps({"messageType": "magAction", "data": {"status": "saved","value":data}}))
                return


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
        if(imu.logging == 1):
            imu.stop_log() 
        imu.pause()
        self.callback.stop()
        self.callback2.stop()
        time.sleep(1.2)
        
        
        # try:
        #     os._exit(0)
        # except:
        #    print('Program is off.')

        return False

    def check_origin(self, origin):
        return True

if __name__ == "__main__":
    # Create IMU
    print("server_version:",server_version)   
    try: 

        input_ret = imu.args_input()
        imu.find_device()    
        # Set up Websocket server on Port 8000
        # Port can be changed
        application = tornado.web.Application([(r'/', WSHandler)])
        http_server = tornado.httpserver.HTTPServer(application)
        # https server
        # http_server = tornado.httpserver.HTTPServer(application,ssl_options={
        #    "certfile": os.path.join(os.path.abspath("."), "./cert/ssl.cert"),
        #    "keyfile": os.path.join(os.path.abspath("."), "./cert/ssl.key"),
        # })
        http_server.listen(input_ret[1])        
        
        tornado.ioloop.IOLoop.instance().start()
    
    except KeyboardInterrupt:  # response for KeyboardInterrupt such as Ctrl+C
        print('User stop this program by KeyboardInterrupt! File:[{0}], Line:[{1}]'.format(__file__, sys._getframe().f_lineno))
        logging.info("User stop this program by KeyboardInterrupt!")
        os._exit(1)
    except Exception as e:
        logging.info("server main function exception:{0}".format(e))
        print(e)    

    
