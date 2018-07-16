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
import math
import os
import sys

from openimu import OpenIMU
from imu_input_packet import InputPacket

class OpenIMU_CLI:
    def __init__(self):
        '''Initialize command line interface
        '''
        self.command = "help"         # set default command to help
        self.input_string = []        # define input_string
        self.cli_properties = imu.imu_properties['CLICommands']
        self.current_command =[]
        self.baud_rate = 0
        self.accel_lpf = 0
        self.rate_lpf = 0
        self.orien = 0
        self.bit_status = 0

    def help_handler(self):
        print("Usage: help menu")
        for x in self.cli_properties:
            print(x['name'] + " : " + x['description']) 
        
        return True

    def connect_handler(self):
        '''connect command is used to find OpenIMU device
        '''
        print("Connecting...")

        imu.find_device()

        return True

    def upgrade_handler(self):
        '''upgrade command is used for firmware upgrade and followed by file name
        '''
        print("Upgrading...")
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
        print("Recording...")
        imu.start_log()
        return True

    def run_handler(self):
        '''used by customers
        '''
        print("Running...")

        return True

    def get_handler(self):
        '''get configuration or data from OpenIMU device
        '''
        print("Getting...")
        input_args = len(self.input_string)
        get_properties = self.current_command
 
        if (input_args == 1):
            print("Usage: get [options]")
            for x in get_properties['arguments']:
                print(x['parameter'] + " : " + x['description'])
            return True
        else:
            for x in get_properties['arguments']:
                if (x['parameter'] == self.input_string[1]):
                    break

        if (x['parameter'] == "dev_id"):
            imu.openimu_get_device_id()
        elif (x['parameter'] == "rate"):
            packet_rate = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Packet Rate'), None)
            odr_param = imu.openimu_get_param(packet_rate['paramId'])
            try:
                imu.odr_setting = odr_param['value']
            except:
                imu.odr_setting = 0
            print(imu.odr_setting)
        elif (x['parameter'] == "type"):
            packet_type = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Packet Type'), None)
            packet_type_param = imu.openimu_get_param(packet_type['paramId'])
            try: 
                imu.packet_type = packet_type_param['value'][0:2]    
            except:
                imu.packet_type = 0
            print(imu.packet_type)
        elif (x['parameter'] == "baud_rate"):
            baud_rate = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Baud Rate'), None)
            baud_rate_param = imu.openimu_get_param(baud_rate['paramId'])
            print(baud_rate_param)
            self.baud_rate = baud_rate_param    
            print(self.baud_rate)
        elif (x['parameter'] == "xl_lpf"):
            xl_lpf = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Accel LPF'), None)
            xl_lpf_param = imu.openimu_get_param(xl_lpf['paramId'])
            print(xl_lpf_param)
            self.accel_lpf = xl_lpf_param    
            print(self.accel_lpf)
        elif (x['parameter'] == "rate_lpf"):
            gyro_lpf = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Rate LPF'), None)
            gyro_lpf_param = imu.openimu_get_param(gyro_lpf['paramId'])
            print(gyro_lpf_param)
            self.rate_lpf = gyro_lpf_param    
            print(self.rate_lpf)
        elif (x['parameter'] == "orien"):
            orien = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Orientation'), None)
            orien_param = imu.openimu_get_param(orien['paramId'])
            self.orien = orien_param    
        elif (x['parameter'] == "bit_status"):
            bit_status = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Bit Status'), None)
            bit_status_param = imu.openimu_get_param(bit_status['paramId'])
            self.bit_status = 0 
        return True
   
    def set_packet(self, command, value):
        '''pack the configuration following up Aceinna's format
        ''' 
        if command == "baud_rate":
            field0 = 2
            field0Data = int(value)
        elif command == "type":
            field0 = 3
            if value == "s0":
                field0Data = ord('S') * 256
                field0Data += ord('0')
            elif value == "s1":
                field0Data = ord('S') * 256
                field0Data += ord('1')
            elif value == "a1":
                field0Data = ord('A') * 256
                field0Data += ord('1')
            elif value == "a2":
                field0Data = ord('A') * 256
                field0Data += ord('2')
            else:
                field0Data = ord('F') * 256
                field0Data += ord('1')
        elif command == "rate":
            field0 = 1
            field0Data = int(value)
        elif command == "xl_lpf":
            field0 = 6
            field0Data = int(value)
        elif command == "rate_lpf":
            field0 = 5
            field0Data = int(value)
        elif command == "orien":
            field0 = 7
            field0Data = int(value)
        else:
            print("Usage: set [options] <value>") 
            return True
        
        print(field0Data)    
        numFields = 1
        C = InputPacket(imu.imu_properties, 'uP', False, False)

        packet = [0x55, 0x55, 0x53, 0x46] + [5] + [numFields, field0, field0Data]
        C.bytes = packet + C.calc_crc(packet[2:8])
        imu.write(C.bytes)
        time.sleep(0.05)
        return True
   
    def set_param(self, command, value):
        if command == "baud_rate":
            baud_rate_param = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Baud Rate'), None)
            imu.openimu_update_param(baud_rate_param['paramId'], int(value))
        elif command == "rate":
            rate_param = next((x for x in imu.imu_properties['userConfiguration'] if x['name'] == 'Packet Rate'), None)
            imu.openimu_update_param(rate_param['paramId'], int(value))
        elif command == "type":
            if value == "z1":
                packet_id = ord('z') * 256
                packet_id += ord('1')
            elif value == "z2":
                packet_id = ord('z') * 256
                packet_id += ord('2')
            elif value == "a1":
                packet_id= ord('A') * 256
                packet_id += ord('1')
            elif value == "l1":
                packet_id = ord('l') * 256
                packet_id += ord('1')
            else:
                packet_id = ord('z') * 256
                packet_id += ord('2')
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
        print("Setting...")

        input_args = len(self.input_string)
        set_properties = self.current_command

        if (input_args < 3):
            print("Usage: set <options> <values>")
            for x in set_properties['arguments']:
                print(x['parameter'] + " : " + x['description'])
            return True
        else:
            for x in set_properties['arguments']:
                if (x['parameter'] == self.input_string[1]):
                    break

        if self.input_string[2] not in x['options']:
            print("Usage: set " + x['parameter'] + " <values>")
            print("values: ")
            print(' '.join(x['options']))
            return True
        else:
            self.set_param(self.input_string[1], self.input_string[2])

        return True

    def save_handler(self):
        C = InputPacket(imu.imu_properties, 'sC')
        imu.write(C.bytes)
    
    def command_handler(self):
        '''main routine to handle input command
        '''       
        while True:
            if sys.version_info[0] < 3:
                token = raw_input(">>")
            else:
                token = input(">>")
            self.input_string = token.split(" ")
             
            if token.strip() == 'exit':
                break;
            for x in self.cli_properties:
                if x['name'] == self.input_string[0]:
                    self.current_command = x
                    eval('self.%s()'%(x['function']))
                    break;
            else:
                self.help_handler()    

        return True 

if __name__ == "__main__":
    imu = OpenIMU(ws=False)
    cli = OpenIMU_CLI()
    cli.command_handler()
