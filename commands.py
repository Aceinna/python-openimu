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
        self.http_server_running = False

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
            file_name = self.input_string[1]
            imu.ws = False
            if file_name is not " ":
                if imu.openimu_upgrade_fw_prepare(file_name) == True:
                    while not imu.openimu_finish_upgrade_fw():
                        imu.openimu_upgrade_fw(file_name)
                    imu.openimu_start_app()
                else:
                    print("Error: file doesn't exist")  
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
        time.sleep(2)
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
                    print("Usage: get [options]")
                    print("Option: ")
                    i = 2
                    while i < len(param_properties):
                        print(param_properties[i]['argument'])
                        i += 1
                    return True
        
        param = imu.openimu_get_param(x['paramId'])
        return True
   
    def set_param(self, command, value):
        param_properties = imu.imu_properties['userConfiguration']
        i = 2
        while i < len(param_properties):
            x = param_properties[i] 
            if (x['argument'] == command):
               break
            i += 1

        if i < len(param_properties):
            if command == "type" or command == "orien":
                imu.openimu_update_param(x['paramId'], value)
            else:
                imu.openimu_update_param(x['paramId'], int(value))
        else:
            print("Usage: set [options] <value>") 
            
        return True
     
    def set_handler(self):
        '''set parameters' values
        '''
        input_args = len(self.input_string)
        param_properties = imu.imu_properties['userConfiguration']

        if input_args == 1:
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

        if input_args == 2:
            if i == len(param_properties):
                print("Usage: set <options> <values>")
                i = 2
                while i < len(param_properties):
                    x = param_properties[i] 
                    print(x['argument'])
                    i += 1
            else:
                print("Usage: set " + x['argument'] + " <values>")
                print("values: ") 
                print(x['options'])
            return True

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
        if sys.version_info[0] > 2:
            import asyncio
            asyncio.set_event_loop(asyncio.new_event_loop())
        self.http_server.listen(8000)
        tornado.ioloop.IOLoop.instance().start()
         
    def server_start_handler(self):
        imu.ws = True
        self.thread.start()
        self.http_server_running = True
        return True

    def server_stop(self):
        print("server stops")
        if self.http_server is not None:
           self.http_server.stop()
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
                if self.http_server_running == True:
                    self.http_server_running = False
                    self.server_stop()
                else:
                    break
            if self.http_server_running == True:
                print("server is on-going, please stop it")
                continue

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
