from __future__ import print_function
"""
Driver for Aceinna OpenIMU
Based on PySerial https://github.com/pyserial/pyserial
Created on 2018-06-17
@author: m5horton
"""

"""
WS Master Connection 
connect         - finds device, gets device_id/odr_setting, and loops
                - run this in thread otherwise blocking
disconnect      - ends loop

Device Discovery
find_device     - entry point to find a serial connected IMU
find_ports
autobaud

Logging
start_log
stop_log

Syncing 
sync            - syncs to a unit continuously transmitting, or a specific packet response

Data Functions

Serial          - a tiny layer on top of Pyserial to handle exceptions as means of device detection
open
close
read
write
reset_buffer
"""
import serial
import serial.tools.list_ports
import math
import string
import time
import sys
import os
from .file_storage import OpenIMULog
import collections
import glob
import struct
import json
import threading
from pathlib import Path
from .imu_input_packet import InputPacket
from .bootloader_input_packet import BootloaderInputPacket
from azure.storage.blob import BlockBlobService
# import webbrowser # used for open ANS website by system browser
import requests
import binascii
import json
import argparse
import logging
from .predefine import (
    get_app_urls,
    get_app_names,
    app_str,
    string_folder_path
)
from .utils import (
    get_executor_path,
    get_content_from_bundle
)

ROOT_PATH = os.getcwd()

EXECUTOR_PATH = get_executor_path()
CONFIG_FILE_NAME ='openimu.json'
APP_CONFIG_FOLDER_NAME = 'app_config'
DATA_FOLDER_NAME = 'data'
CONNECTION_FILE_PATH = os.path.join(EXECUTOR_PATH,APP_CONFIG_FOLDER_NAME,'connection.json')

class OpenIMU:
    def __init__(self, ws=False):
        '''Initialize and then start ports search and autobaud process
        '''
        self.ws = ws                # set to true if being run as a thread in a websocket server
        self.ser = None             # the active UART
        self.device_id = 0          # unit's id str
        self.odr_setting = 0        # units ODR rate
        self.paused = 1             # imu is successfully connected to a com port, kind of redundant with device_id property
        self.logging = 0            # logging on or off
        self.logger = None          # the file logger instance
        self.packet_size = 0        # expected size of packet 
        self.packet_type = 0        # expected type of packet
        self.data = {}              # placeholder imu measurements of last converted packeted
        self.data_buffer = []       # serial read buffer
        self.packet_buffer = []     # packet parsing buffer
        self.sync_state = 0
        self.sync_pattern = collections.deque(4*[0], 4)  # create 4 byte FIFO         
        self.input_tcpip_port = self.args_input().p[0] if isinstance(self.args_input().p, list) else self.args_input().p
        self.customer_baudrate = self.args_input().b[0] if isinstance(self.args_input().b, list) else self.args_input().b
        self.input_com_port = self.args_input().c[0] if isinstance(self.args_input().c, list) else self.args_input().c
        self.loglevel = self.args_input().l[0] if isinstance(self.args_input().l, list) else self.args_input().l
        self.imu_properties = None
        self.is_bootloader = False

        # log init
        logging.basicConfig(level=self.loglevel,
            format='%(asctime)-28s:%(msecs)-4dms %(filename)-20s[%(funcName)-40s][line:%(lineno)4d] %(levelname)5s     %(message)s',
            datefmt='%a, %d %b %Y %H:%M:%S',                
            filename= os.path.join(EXECUTOR_PATH,'webserver.log'),
            filemode='w')

        self.prepare_folders()
        self.load_properties()

    def get_file_flag(self):
        return self.local_jsonfile_flag

    def prepare_folders(self):
        '''
        Prepare folders for data storage and configuration
        '''
        data_folder_path = os.path.join(EXECUTOR_PATH, DATA_FOLDER_NAME)
        if not os.path.isdir(data_folder_path):
            os.makedirs(data_folder_path)
        
        #copy contents of app_config under executor path
        app_config_folder_path = os.path.join(EXECUTOR_PATH, APP_CONFIG_FOLDER_NAME)
        
        for app_name in get_app_names():
            app_name_path = os.path.join(app_config_folder_path, app_name)
            app_name_config_path = os.path.join(app_name_path, CONFIG_FILE_NAME)
            if not os.path.isfile(app_name_config_path):
                if not os.path.isdir(app_name_path):
                    os.makedirs(app_name_path)
                app_config_content = get_content_from_bundle(APP_CONFIG_FOLDER_NAME, os.path.join(app_name,CONFIG_FILE_NAME))
                if app_config_content is None:
                    continue

                with open(app_name_config_path, "wb") as code:
                    code.write(app_config_content) 


    def load_properties(self):
        '''
        Load properties from json file, the sequence should be
        1. Find in user working path, use json file if exists.
        2. If not exists, find in executor working path, check the app info, 
            then load matched json content
        '''
        is_loaded = False
        # Load config from user working path
        local_config_file_path = os.path.join(ROOT_PATH, CONFIG_FILE_NAME)
        if os.path.isfile(local_config_file_path):
            with open(local_config_file_path) as json_data:
                self.imu_properties = json.load(json_data)
                return

        # Load default config if there is no configuration
        if not is_loaded and not self.imu_properties:
            default_config_file_path = \
                os.path.join(EXECUTOR_PATH, APP_CONFIG_FOLDER_NAME, 'IMU', CONFIG_FILE_NAME)
            if os.path.isfile(default_config_file_path):
                with open(default_config_file_path) as json_data:
                    self.imu_properties = json.load(json_data)
                    return

        if self.is_bootloader: # Don't load app info if is in bootloader
            return

        app_info = bytes.decode(self.openimu_get_user_app_id())
        config_file_path_template = os.path.join(EXECUTOR_PATH, string_folder_path)
        for item in app_str:
            if item in app_info:
                folder_path = config_file_path_template.replace('APP_TYP',item)
                try:
                    with open(folder_path) as json_data:
                        self.imu_properties = json.load(json_data)
                except FileNotFoundError as ex:
                    print('Canont find setting file', folder_path)
                break

    def find_device(self):
        ''' Finds active ports and then autobauds units
        '''         
        logging.info('Find device,------------------------------------------------------------------------')    
        search_history, num_ports_ago = 0, len(list(serial.tools.list_ports.comports()))   
        while not self.device_id: 
            logging.debug('no device id, staring find device while loop')
            if sys.version_info[0] > 2:
                print('Find device {0} times'.format(search_history), end="\r", flush=True)
            else:
                print('Find device {0} times'.format(search_history))
            ports = self.find_ports()
            if len(ports) != num_ports_ago:
                time.sleep(4)            
            if len(ports):
                if self.try_last_port():
                    self.set_connection_details()
                    self.load_properties()
                    return True
                if self.autobaud(ports):
                    self.load_properties()
                    time.sleep(0.1)
                    return True
            else:
                time.sleep(0.5)    
            search_history += 1
            num_ports_ago = len(ports)

        
    def find_ports(self):
        ''' Lists serial port names. Code from
            https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
            Successfully tested on Windows 8.1 x64, Windows 10 x64, Mac OS X 10.9.x / 10.10.x / 10.11.x and Ubuntu 14.04 / 14.10 / 15.04 / 15.10 with both Python 2 and Python 3.
            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        '''
        #find system available ports
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        portList = list(serial.tools.list_ports.comports())          
        ports = [p.device for p in portList] 
        ports.sort()
        if len(ports):            
            print("\nsystem ports detected", ports)
            logging.info('system ports detected:{0}'.format(ports)) 
        else:            
            logging.info('no system ports detected') 
            time.sleep(0.5)
        # return ports
        result = []
        for port in ports:
            if "Bluetooth" in port:
                continue
            else:
                logging.debug('Testing port ' + port)
                s = None
                try:
                    s = serial.Serial(port)
                    if s:
                        s.close()
                        result.append(port)
                # except:
                except Exception as e:
                    print("testing port exception:", e)      
                    logging.debug(e)              
                    try:
                        if s:
                            s.close()
                    except Exception as ee:
                        logging.debug(ee)
                    pass
        logging.debug('result:{0}'.format(result))
        return result

    def autobaud(self, ports):
        '''Autobauds unit - first check for stream_mode / continuous data, then check by polling unit
           :returns: 
                true when successful
        ''' 
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        bandListFromOptions = self.imu_properties['userConfiguration'][2]['options']  if self.customer_baudrate == 0 else [self.customer_baudrate]    
        for port in ports:
            for baud in bandListFromOptions:
                logging.info("try {0}:{1}".format(port, baud))          
                self.open(port if self.input_com_port == 'COMX' else self.input_com_port,baud)   
                try:
                    if self.ser:                     
                        self.device_id = self.openimu_get_device_id()
                        if self.device_id:
                            self.set_connection_details()
                            logging.info('Connected in autobaud')
                            if sys.platform.startswith('win'):
                                self.ser.set_buffer_size(rx_size = 128000, tx_size = 128000)
                            return True
                        else:
                            self.ser.close()
                except Exception as e:
                    logging.info("self.ser.close and  get_device_id exist error:{error}".format(baudrate=baud, error=e))  
        return False
    
    def set_connection_details(self):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        if "Bootloader" in self.device_id:
            self.is_bootloader = True
            print('BOOTLOADER MODE') 
            print('Connected ....{0}'.format(self.device_id))
            print('Please Upgrade FW with upgrade_fw function')
        elif self.device_id:            
            self.is_bootloader = False
            print('Connected(port:{0} baudrate:{1}) ....{2}'.format(self.ser.name, self.ser.baudrate, self.device_id))
        self.save_last_port()   
        logging.info('Connected(port:{1} baudrate:{2}) ....{0}---------------------------------------------'.format(self.device_id,self.ser.name, self.ser.baudrate))               

        # open the webside ans automatically by system browser        
        # webbrowser.open("http://40.118.233.18:8080/record", new=0, autoraise=True) 

    def try_last_port(self):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        connection = None
        portList = list(serial.tools.list_ports.comports())
        ports = [ p.device for p in portList]

        try:
            with open(CONNECTION_FILE_PATH) as json_data:
                connection = json.load(json_data)
            if connection:
                if not connection['port'] in ports:
                    logging.debug('Port from app_config/connection.json not exist')
                    return False                             
                self.open(port=connection['port'], baud=connection['baud'] if self.customer_baudrate == 0 else self.customer_baudrate) 
                # self.open(port=connection['port'], baud=connection['baud'])               
                if self.ser:
                    self.device_id = self.openimu_get_device_id()
                    if self.device_id:
                        print('Autoconnected by last saved port')
                        logging.info('Autoconnected by last saved port')  
                        return True
                    else:   
                        self.ser.close()                     
                        logging.debug('Port from app_config/connection.json get_device_id failed!')
                        return False
                else:
                    return False
        except:
            logging.info("try last port exception")
            return False

    def save_last_port(self):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        connection = { "port" : self.ser.port, "baud" : self.ser.baudrate }

        setting_folder = os.path.join(EXECUTOR_PATH, APP_CONFIG_FOLDER_NAME)

        if not os.path.exists(setting_folder):
            try:
                os.makedirs(setting_folder)
            except:
                return
        try:
            with open(CONNECTION_FILE_PATH, 'w') as outfile:
                json.dump(connection, outfile)
        except:
            pass
    
    def get_latest(self):
        '''Get latest converted IMU readings in converted units
            :returns:
                data object or error message for web socket server to pass to app
        '''
        if not self.paused:
            return self.data
        else: 
            return { 'error' : 'not streaming' }
    
    def start_log(self, data = False):
        '''Creates file or cloud logger.  Autostarts log activity if ws (websocket) set to false
        '''
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        if self.ws == False: 
            if self.paused:
                self.connect()
            if self.odr_setting:
                data_folder_path = os.path.join(EXECUTOR_PATH, DATA_FOLDER_NAME)
                if not os.path.isdir(data_folder_path):
                    print("Create data/ ")
                    os.makedirs(data_folder_path)
                print('Logging Started ...')
                self.logger = OpenIMULog(self,data)
                self.logging = 1
        elif not self.paused and self.odr_setting:
            self.logger = OpenIMULog(self,data)
            self.logging = 1
            logging.info('Loging start,--------------------------------------------')            

                
    def stop_log(self):
        '''Stops file or cloud logger
        '''
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        self.pause()
        self.logging = 0
        self.logger.close()
        self.logger = None
        print('Logging Finished ...')
        logging.info('Logging finished,---------------------------------------------')            

    def openimu_update_param(self, param, value):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        if param == 2:
            connection = { "port" : self.ser.port, "baud" : value }
            with open(CONNECTION_FILE_PATH, 'w') as outfile:
                json.dump(connection, outfile)
        C = InputPacket(self.imu_properties, 'uP', param, value) 
        self.write(C.bytes)
        logging.debug("write message:{0}".format(C.bytes))
        #time.sleep(0.05)
        return self.openimu_get_packet('uP')  

    def openimu_get_param(self, param,):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        C = InputPacket(self.imu_properties, 'gP', param)
        self.write(C.bytes)
        #time.sleep(0.05)
        return self.openimu_get_packet('gP')

    def magneticAlignCmd(self,action):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        C = InputPacket(self.imu_properties, 'ma', action)
        self.write(C.bytes)

        if action == 'stored':
            time.sleep(1)
            returnedStatus = self.read(10000)

            decodedStatus = binascii.hexlify(returnedStatus)
            return self.decodeOutput(decodedStatus)

        if action == 'status':
            returnedStatus = self.ser.readline().strip()
            if sys.version_info[0] < 3:
                decodedStatus = binascii.hexlify(returnedStatus)
            else:
                decodedStatus = str(binascii.hexlify(returnedStatus), 'utf-8')

            # print (decodedStatus)
            if 'f12e' in decodedStatus:
                return 1

    def decodeOutput(self, value):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        hard_iron_x = dict()
        hard_iron_y = dict()
        soft_iron_ratio = dict()
        soft_iron_angle = dict()

        # output['hardIronX'] = self.hardIronCal(value[10:14], 'axis')
        # output['hardIronY'] = self.hardIronCal(value[14:18], 'axis')
        # output['SoftIronRatio'] = self.hardIronCal(value[18:22], 'ratio')
        # output['SoftIronAngle'] = self.hardIronCal(value[22:26], 'angle')

        hard_iron_x['value'] = self.hardIronCal(value[26:30], 'axis')
        hard_iron_x['name'] = 'Hard Iron X'
        hard_iron_x['argument'] = 'hard_iron_x'

        hard_iron_y['value'] = self.hardIronCal(value[30:34], 'axis')
        hard_iron_y['name'] = 'Hard Iron Y'
        hard_iron_y['argument'] = 'hard_iron_y'

        soft_iron_ratio['value'] = self.hardIronCal(value[34:38], 'ratio')
        soft_iron_ratio['name'] = 'Soft Iron Ratio'
        soft_iron_ratio['argument'] = 'soft_iron_ratio'

        soft_iron_angle['value'] = self.hardIronCal(value[38:42], 'angle')
        soft_iron_angle['name'] = 'Soft Iron Angle'
        soft_iron_angle['argument'] = 'soft_iron_angle'

        # output['hard_iron_y'] = self.hardIronCal(value[30:34], 'axis')
        # output['soft_iron_ratio'] = self.hardIronCal(value[34:38], 'ratio')
        # output['soft_iron_angle'] = self.hardIronCal(value[38:42], 'angle')

        output = [hard_iron_x,hard_iron_y,soft_iron_ratio,soft_iron_angle]

        return output

    def hardIronCal(self, value, type):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        decodedValue = int(value, 16)
        # print (decodedValue)
        if type == 'axis':
            if decodedValue > 2 ** 15:
                newDecodedValue = (decodedValue - 2 ** 16)
                return newDecodedValue / float(2 ** 15) * 8
            else:
                return decodedValue / float(2 ** 15) * 8

        if type == 'ratio':
            return decodedValue / float(2 ** 16 - 1)

        if type == 'angle':
            if decodedValue > 2 ** 15:
                decodedValue = decodedValue - 2 ** 16
                piValue = 2 ** 15 / math.pi
                return decodedValue / piValue

            piValue = 2 ** 15 / math.pi
            return decodedValue / piValue

    def openimu_save_config(self):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))          
        C = InputPacket(self.imu_properties, 'sC')
        self.write(C.bytes)
        # this message currently does not return anything

    def openimu_get_all_param(self):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        C = InputPacket(self.imu_properties, 'gA')
        self.write(C.bytes)
        #time.sleep(0.05)
        return self.openimu_get_packet('gA')  

    def openimu_get_device_id(self):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        C = InputPacket(self.imu_properties, 'pG')
        self.write(C.bytes)
        #time.sleep(0.05)
        device_id = self.openimu_get_packet('pG')
        if device_id:
            # print('git device id')
            try:
                logging.debug("decode id:{0}".format(device_id))
                device_id = device_id.decode()
            except Exception as e:                 
                logging.info("get_device_id decode error about:{0}, and exception is:{1}".format(device_id,e))
                return False
            return device_id
        else: 
            return False

    def openimu_get_user_app_id(self): 
        if self.is_bootloader:
            return 'Unknown'
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        C = InputPacket(self.imu_properties, 'gV')
        # print('get id--------------1')
        self.write(C.bytes)        
        #time.sleep(0.05)
        return self.openimu_get_packet('gV')
    
    def openimu_version_compare(self, fw_version, js_version):
        if js_version in fw_version:
            pass
            # print('fw & json version match')
        else:
            pass
            # print('fw & json version mismatch')

    def connect(self):
        '''Continous data collection loop to get and process data packets
        '''
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        if not self.device_id:
            self.find_device()
        packet_rate = next((x for x in self.imu_properties['userConfiguration'] if x['name'] == 'Packet Rate'), None)
        odr_param = self.openimu_get_param(packet_rate['paramId'])
        try:
            self.odr_setting = odr_param['value']
        except:
            self.ord_setting = 0
        packet_type = next((x for x in self.imu_properties['userConfiguration'] if x['name'] == 'Packet Type'), None)
        packet_type = self.openimu_get_param(packet_type['paramId'])
        try: 
            self.packet_type = packet_type['value'][0:2]    # Set the Actual High Rate Packet
        except:
            self.packet_type = 0
        self.paused = 0
        logging.debug("connect function ongoing: id-{0}; packet rate-{1}; odr-{2}; packet type-{3}".format(self.device_id, packet_rate, odr_param, packet_type))
        threading.Thread(target=self.start_collection_task).start()
            
    def pause(self):
        ''' Will End the data collection task and thread
        '''
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        self.paused = 1 
        time.sleep(0.1)
        self.reset_buffer()
        
    def disconnect(self):
        '''Ends data collection loop and Reset settings
        '''
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        if(self.logging == 1 ):
            self.stop_log() 
        self.pause()
        self.close()
        self.data = {}
        self.device_id = 0
        self.odr_setting = 0
        self.packet_size = 0        
        self.packet_type = 0
        
    def parse_payload(self, ws = False):
        '''Parses packet payload using openimu.json as reference
        '''
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        payload = self.packet_buffer[3:self.packet_buffer[2]+3]   # extract the payload
        data = [] 

        # Find the packet in the imu_properties from unit's JSON description
        output_packet = next((x for x in self.imu_properties['userMessages']['outputPackets'] if x['name'] == self.packet_type), None)
        input_packet = next((x for x in self.imu_properties['userMessages']['inputPackets'] if x['name'] == self.packet_type), None)
        bootloader_packet = next((x for x in self.imu_properties['bootloaderMessages'] if x['name'] == self.packet_type), None)

        logging.debug("start to parse_payload:\n{0}".format([hex(x) for x in payload]))
        if output_packet != None:
            self.data = self.openimu_unpack_output_packet(output_packet, payload)
            if self.logging == 1 and self.logger is not None:
                self.logger.log(self, self.data)
                # print(self.data['lat'])
                logging.debug("parse_payload, output_packet data:{0}".format(self.data))

        elif input_packet != None:
            logging.debug("parse_payload, input_packet data:\n{0}".format([hex(x) for x in payload]))
            data = self.openimu_unpack_input_packet(input_packet['responsePayload'], payload)

        elif bootloader_packet != None:
            logging.debug("parse_payload, bootloader_packet data:{0}".format(payload))
            data = self.openimu_unpack_bootloader_packet(bootloader_packet['responsePayload'], payload)

        return data

    def calc_crc(self,payload):
        '''Calculates CRC per 380 manual
        '''
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        crc = 0x1D0F
        for bytedata in payload:
           crc = crc^(bytedata << 8) 
           for i in range(0,8):
                if crc & 0x8000:
                    crc = (crc << 1)^0x1021
                else:
                    crc = crc << 1

        crc = crc & 0xffff
        return crc

    def open(self, port = False, baud = 57600):
        # simple open
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        try:              
            self.ser = serial.Serial(port, baud, timeout = 0.005)
        except Exception as e:
            print('{0}:{1} open failed'.format(port, baud), end='\r')
            logging.debug("Port open exception: {0}-{1}, exception is: {2}, pls restart IMU/change port/disconnect other ports".format(port, baud,e))
            if self.ser is not None:
                if self.ser.isOpen():
                    self.ser.close()
                self.ser = None                           

    def close(self):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        if self.ser:
            self.ser.reset_input_buffer()
            try: 
                self.ser.close()
            except:
                self.ser = False
                logging.debug("happened exception when close ser:{0}".format(self.ser))
    
    def read(self,n):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        bytes = []
        if self.ser:
            try: 
                bytes = self.ser.read(n)
                return bytearray(bytes)
            except serial.SerialException as e:
                if 'returned no data' in str(e):
                    return bytearray(bytes)
                else:
                    self.disconnect()    # sets connected to 0, and other related parameters to initial values
                    print('serial exception read') 
                    self.find_device() 
        
    def write(self,n):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        try: 
            self.ser.write(n)
        except Exception as e:
            print(e)
            self.disconnect()   # sets connected to 0, and other related parameters to initial values  
            print('serial exception write')
            self.find_device() 

    def reset_buffer(self):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        try:
            self.ser.reset_input_buffer()
        except:
            self.ser = False

    def openimu_unpack_output_packet(self, output_message, payload):         
        logging.debug("unpack_output_packet, payload is:\n{0}".format([hex(x) for x in payload]))
        length = 0
        pack_fmt = '<'
        for value in output_message['payload']:
            if value['type'] == 'float':
                pack_fmt += 'f'
                length += 4
            elif value['type'] == 'uint32':
                pack_fmt += 'I'
                length += 4
            elif value['type'] == 'int32':
                pack_fmt += 'i'
                length += 4
            elif value['type'] == 'int16':
                pack_fmt += 'h'
                length += 2
            elif value['type'] == 'uint16':
                pack_fmt += 'H'
                length += 2
            elif value['type'] == 'double':
                pack_fmt += 'd'
                length += 8
            elif value['type'] == 'int64':
                pack_fmt += 'q'
                length += 8
            elif value['type'] == 'uint64':
                pack_fmt += 'Q'
                length += 8
            elif value['type'] == 'char':
                pack_fmt += 'c'
                length += 1
            elif value['type'] == 'uchar':
                pack_fmt += 'B'
                length += 1
            elif value['type'] == 'uint8':
                pack_fmt += 'B'
                length += 1
        len_fmt = '{0}B'.format(length)
        try:
            b = struct.pack(len_fmt, *payload)
            data = struct.unpack(pack_fmt, b)
            out = [(value['name'],data[idx]) for idx,value in enumerate(output_message['payload'])]
            data = collections.OrderedDict(out)
            logging.debug("unpack_output_packet, data of payload is:\n{0}".format(data))
            return data
        except Exception as e:
            print("error happened when decode the payload of packets, pls restart IMU: {0}".format(e)) 
            logging.debug("decode payload of packets exception:{0}".format(e))   
    
    def openimu_unpack_input_packet(self, input_message, payload):
        logging.debug("unpack_input_packet: {0}  payload:\n{1}".format(input_message['type'], [hex(x) for x in payload]))
        if input_message['type'] == 'userConfiguration':
            user_configuration = self.imu_properties['userConfiguration']
            params = []
            for parameter in user_configuration:
                id = parameter['paramId']
                type = parameter['type']
                name = parameter['name']
                value = self.openimu_unpack_one(type, payload[id*8:(id+1)*8])
                # print('{0}: {1}'.format(name,value))
                params.append({ "paramId": id, "name": name, "value": value})
            return params
        elif input_message['type'] == 'userParameter':
            user_configuration = self.imu_properties['userConfiguration']
            param_id = self.openimu_unpack_one('uint32', payload[0:4]) 
            if param_id >= len(user_configuration):
                return False
            param = user_configuration[param_id]
            param_value = self.openimu_unpack_one(param['type'], payload[4:12])
            # print('{0}: {1}'.format(param['name'], param_value))
            return { "paramId": param_id, "name": param['name'], "value": param_value }
        elif input_message['type'] == 'paramId':
            user_configuration = self.imu_properties['userConfiguration']
            error = self.openimu_unpack_one('uint32', payload[0:4]) 
            if not error:
                print("Successfully Updated")
            return { "error": error }
        elif input_message['type'] == 'string':
            text_string = self.openimu_unpack_one('string', payload)
            return text_string

    def openimu_unpack_bootloader_packet(self, bootloader_message, payload):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        if bootloader_message['type'] == 'ack':
            #print('Success')
            return { "error": 0 }

    def openimu_unpack_one(self, type, data):
        logging.debug("unpack_one, type:{0}, data:\n{1}".format(type, [hex(x) for x in data]))
        if type == 'uint64':
            try:
                b = struct.pack('8B', *data)
            except:
                return False
            return struct.unpack('<Q', b)[0]
        elif type == 'int64':
            try:
                b = struct.pack('8B', *data)
            except:
                return False
            return struct.unpack('<q', b)[0]
        elif type == 'uint32':
            try: 
                b = struct.pack('4B', *data)
            except:
                return False
            return struct.unpack('<L', b)[0]
        elif type == 'char8':
            try:
                b = struct.pack('8B', *data)
                # print('unpack one---------0000')
                return b.decode()    
            except:
                return False 
        elif type == 'string':
            try:
                fmt_str = '{0}B'.format(len(data))
                b = struct.pack(fmt_str, *data)
                return b
            except:
                return False
        elif type == 'double':
            try:
                b = struct.pack('8B', *data)
            except:
                return False
            return struct.unpack('d', b)[0]

    def openimu_start_bootloader(self):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))
        packet = BootloaderInputPacket(self.imu_properties, 'JI')
        self.write(packet.bytes)
        self.openimu_get_packet('JI')    
        self.ser.baudrate = 57600   # Force baud rate to 57600
        bootloader_id = self.openimu_get_device_id()
        print(bootloader_id)
        return True
          
    def openimu_start_app(self):
        '''Starts app
        '''
        packet = BootloaderInputPacket(self.imu_properties, 'JA')
        self.write(packet.bytes)
        print('Restarting app ...')
        time.sleep(5)
        self.disconnect()
        self.reset_buffer()
        self.close()
        self.find_device()      # Must go thru reconnect process because baud rate may have changed during firmware load
        return True

    def openimu_write_block(self, data_len, addr, data):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        # print(data_len, addr)
        packet = BootloaderInputPacket(self.imu_properties, 'WA', data_len, addr, data)
        self.write(packet.bytes)
        if addr == 0:
            time.sleep(5)
        self.openimu_get_packet('WA')    
       
    def openimu_upgrade_fw_prepare(self, file):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        if self.ws == False:
            fw_file = Path(file)

            if fw_file.is_file():
                self.fw = open(file, 'rb').read()
            else:
                return False

        if not self.openimu_start_bootloader():
            print('Bootloader Start Failed')
            return False

        if self.ws == True:
            self.block_blob_service = BlockBlobService(account_name='navview', protocol='https')
            self.block_blob_service.get_blob_to_path('apps', file, file)
            self.fw = open(file, 'rb').read()

        print('upgrade fw: %s' % file)
        self.max_data_len = 240
        self.addr = 0
        self.fs_len = len(self.fw)

        return True

    def openimu_finish_upgrade_fw(self):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))  
        return self.addr >= self.fs_len

    def openimu_upgrade_fw(self, file):
        '''Upgrades firmware of connected 380 device to file provided in argument
        '''
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))
        packet_data_len = self.max_data_len if (self.fs_len - self.addr) > self.max_data_len else (self.fs_len - self.addr)
        data = self.fw[self.addr : (self.addr + packet_data_len)]
        self.openimu_write_block(packet_data_len, self.addr, data)
        self.addr += packet_data_len

    def start_collection_task(self):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))
        while self.odr_setting and not self.paused:
            if self.odr_setting:
                self.openimu_get_packet(self.packet_type, True)     # get packet in stream mode
        print('End Collection Task')
        return False  # End Thread

    def openimu_get_packet(self,packet_type, stream = False):
        logging.debug("get_packet of {0}".format(packet_type))
        if not packet_type:
            return False
        data = False
        trys = 0
        if self.device_id == 0:
            trys_limit = 60
        else:
            trys_limit = 200
        while not data and trys < trys_limit:
            self.data_buffer = self.read(10000)

            if self.data_buffer:
                data = self.parse_buffer(packet_type, stream)
            trys += 1
        return data

    def parse_buffer(self, packet_type, stream = False):
        logging.debug("at {0}".format(sys._getframe().f_code.co_name))
        if (sys.version_info > (3, 0)) and not isinstance(packet_type, str):
            packet_type_0 = packet_type[0]  
            packet_type_1 = packet_type[1]
        else:
            packet_type_0 = ord(packet_type[0])
            packet_type_1 = ord(packet_type[1])
        for i,new_byte in enumerate(self.data_buffer):
            self.sync_pattern.append(new_byte)
            if list(self.sync_pattern) == [85, 85, packet_type_0, packet_type_1]:
                self.packet_buffer = [packet_type_0, packet_type_1]
                self.sync_state = 1
            elif self.sync_state == 1:
                self.packet_buffer.append(new_byte)
                if len(self.packet_buffer) == self.packet_buffer[2] + 5:
                    logging.debug("parse_buffer {2} packet:\n{0} {1}".format([hex(x) for x in [85, 85, packet_type_0, packet_type_1]], [hex(x) for x in self.packet_buffer], packet_type))
                    packet_crc = 256 * self.packet_buffer[-2] + self.packet_buffer[-1]    
                    if packet_crc == self.calc_crc(self.packet_buffer[:-2]):
                        if not isinstance(packet_type, str) and not isinstance(packet_type, unicode):
                            # print('parse buffer---------')
                            self.packet_type = bytearray(packet_type).decode()
                        else:
                            self.packet_type = packet_type
                        data = self.parse_payload()
                        if not stream:
                            return data
                        else:
                            self.packet_buffer = []
                            self.sync_state = 0
                    else:
                        self.sync_state = 0  # CRC did not match
                        # print("crc error***************************************")

    def args_input(self):        
        parser = argparse.ArgumentParser(description='OpenIMU input args command:', usage='%(prog)s -b [baudrate] -p [http_port] -l [log_level] -c [serial_COM_port]' )
        parser.add_argument('-p', type=int, default=8123, metavar='http_port', nargs=1,help='input the http port')
        parser.add_argument('-b', type=int, default=0, metavar='baudrate', nargs=1,help='input the baudrate',choices=[38400,57600,115200,230400])
        parser.add_argument('-c', type=str, default='COMX', metavar='com_port', nargs=1,help='import the serial com port')
        parser.add_argument('-l', type=int, default=20, metavar='log_level', nargs=1,help='log record level', choices=[0, 10, 20, 30, 40, 50])
        return parser.parse_args()        
#####       


	
    
