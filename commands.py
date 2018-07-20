"""
Python command line interface
Date: 07-05-2018
Author:
"""

import serial
import string
import time
import json
import time
import threading
import math
import os
import sys
import tornado.websocket
import tornado.ioloop
import tornado.httpserver
import tornado.web
import psutil

from imu_input_packet import InputPacket
from server import WSHandler
from global_vars import imu
from os import getpid

class OpenIMU_CLI:
    def __init__(self):
        '''Initialize command line interface
        '''
        self.command = "help"         # set default command to help
        self.input_string = []        # define input_string
        self.cli_properties = [] 
        self.current_command =[]
        self.baud_rate = 0
        self.accel_lpf = 0
        self.rate_lpf = 0
        self.orien = 0
        self.thread = threading.Thread(target=self.start_tornado)
        self.http_server = None

    def help_handler(self):
        print("Usage: ")
        for x in self.cli_properties:
            print(x['name'] + " : " + x['description']) 
        
        return True

    def connect_handler(self):
        '''connect command is used to find OpenIMU device
        '''
        imu.find_device()

        return True

    def upgrade_handler(self):
        '''upgrade command is used for firmware upgrade and followed by file name
        '''
        input_args = len(self.input_string)
        if (input_args == 1):
            print("Usage:")
            print("upgrade file_name")
        else:
            imu.openimu_upgrade_fw(self.input_string[1])

        return True

    def record_handler(self):
        '''record command is used to save the outputs into local machine
        '''
        imu.ws = False
        imu.start_log()
        return True

    def stop_handler(self):
        '''record command is used to save the outputs into local machine
        '''
        imu.stop_log()
        return True

    def run_handler(self):
        '''used by customers
        '''
        print("Running...")

        return True

    def get_handler(self):
        '''get configuration or data from OpenIMU device
        '''
        input_args = len(self.input_string)
        param_properties = imu.imu_properties['userConfiguration']
 
        if (input_args == 1):
            print("Usage: get [options]")
            print("Option: ")
            i = 2
            while i < len(param_properties):
                print(param_properties[i]['argument'])
                i += 1
            return True
        else:
            i = 2
            while i < len(param_properties):
                x = param_properties[i]
                if (x['argument'] == self.input_string[1]):
                    break
                i += 1
                if (i == len(param_properties)):
                    return True
        
        param = imu.openimu_get_param(x['paramId'])
        if (x['argument'] == "rate"):
            try:
                imu.odr_setting = param['value']
            except:
                imu.odr_setting = 0
            print("get rate ")
            print(imu.odr_setting)
        elif (x['argument'] == "type"):
            try: 
                imu.packet_type = param['value'][0:2]    
            except:
                imu.packet_type = 0
        elif (x['argument'] == "baud_rate"):
            self.baud_rate = param    
        elif (x['argument'] == "xl_lpf"):
            self.accel_lpf = param    
            print(self.accel_lpf)
        elif (x['argument'] == "rate_lpf"):
            self.rate_lpf = param    
            print(self.rate_lpf)
        elif (x['argument'] == "orien"):
            self.orien = param    
        return True
   
    def set_param(self, command, value):
        if command == "baud_rate":
            baud_rate_param = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Baud Rate'), None)
            imu.openimu_update_param(baud_rate_param['paramId'], int(value))
        elif command == "rate":
            rate_param = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Packet Rate'), None)
            imu.openimu_update_param(rate_param['paramId'], int(value))
        elif command == "type":
            type_param = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Packet Type'), None)
            imu.openimu_update_param(type_param['paramId'], value) 
        elif command == "xl_lpf":
            xl_param = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Accel LPF'), None)
            imu.openimu_update_param(xl_param['paramId'], int(value))
        elif command == "rate_lpf":
            rate_param = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Rate LPF'), None)
            imu.openimu_update_param(rate_param['paramId'], int(value))
        elif command == "orien":
            orien_param = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Orientation'), None)
            imu.openimu_update_param(orien_param['paramId'], value)
        else:
            print("Usage: set [options] <value>") 
            
        return True
     
    def set_handler(self):
        '''set parameters' values
        '''
        input_args = len(self.input_string)
        param_properties = imu.imu_properties['userConfiguration']

        if (input_args < 3):
            print("Usage: set <options> <values>")
            i = 2
            while i < len(param_properties):
                x = param_properties[i] 
                print(x['argument'])
                i += 1
            return True
        else:
            i = 2
            while i < len(param_properties):
                x = param_properties[i] 
                if (x['argument'] == self.input_string[1]):
                    break
                i += 1

        if ((x['type'] == "char8" and self.input_string[2] not in x['options']) or 
            (x['type'] == "int64" and int(self.input_string[2]) not in x['options'])):
                print("Usage: set " + x['argument'] + " <values>")
                print("values: ") 
                print(x['options'])
                return True
        else:
            self.set_param(self.input_string[1], self.input_string[2])

        return True

    def save_handler(self):
        C = InputPacket(imu.imu_properties, 'sC')
        imu.write(C.bytes)
        return True
   
    def start_tornado(self):
        application = tornado.web.Application([(r'/', WSHandler)])
        self.http_server = tornado.httpserver.HTTPServer(application)
        self.http_server.listen(8000)
        tornado.ioloop.IOLoop.instance().start()
         
    def server_start_handler(self):
        imu.ws = True
        self.thread.start()
        return True

    def server_stop_handler(self):
        print("server stops")
        if self.http_server is not None:
           self.http_server.stop()
        ioloop = tornado.ioloop.IOLoop.instance() 
        ioloop.add_callback(ioloop.stop)
        time.sleep(1)
        imu.ws = False
        pid = getpid()
        p = psutil.Process(pid)
        p.kill() 

    def command_handler(self):
        '''main routine to handle input command
        '''       
        self.cli_properties = imu.imu_properties['CLICommands']

        while True:
            if sys.version_info[0] < 3:
                token = raw_input(">>")
            else:
                token = input(">>")
            self.input_string = token.split(" ")
             
            if token.strip() == 'exit':
                break
            for x in self.cli_properties:
                if x['name'] == self.input_string[0]:
                    self.current_command = x
                    eval('self.%s()'%(x['function']))
                    break
            else:
                self.help_handler()    

        return True 

if __name__ == "__main__":
    imu.find_device()
    cli = OpenIMU_CLI()
    cli.command_handler()
