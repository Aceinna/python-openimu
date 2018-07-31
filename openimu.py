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
import math
import string
import time
import sys
import file_storage
import collections
import glob
import struct
import json
import threading
from pathlib import Path
from imu_input_packet import InputPacket
from bootloader_input_packet import BootloaderInputPacket
from azure.storage.blob import BlockBlobService

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

        with open('openimu.json') as json_data:
            self.imu_properties = json.load(json_data)

    def find_device(self):
        ''' Finds active ports and then autobauds units
        '''
        if self.try_last_port():
            self.set_connection_details()
            return True
        else:
            while not self.autobaud(self.find_ports()):
                time.sleep(0.1)
        return True
        
    def find_ports(self):
        ''' Lists serial port names. Code from
            https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
            Successfully tested on Windows 8.1 x64, Windows 10 x64, Mac OS X 10.9.x / 10.10.x / 10.11.x and Ubuntu 14.04 / 14.10 / 15.04 / 15.10 with both Python 2 and Python 3.
            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        '''
        print('scanning ports')
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            if "Bluetooth" in port:
                continue
            else:
                print('Testing port ' + port)
                try:
                    s = serial.Serial(port)
                    if s:
                        s.close()
                        result.append(port)
                except:
                    pass
        return result

    def autobaud(self, ports):
        '''Autobauds unit - first check for stream_mode / continuous data, then check by polling unit
           :returns: 
                true when successful
        ''' 
        
        for port in ports:
            self.open(port)
            # TODO: change this to intelligently use openimu.json.  even save the last configuration 
            for baud in [115200, 57600]:
                if self.ser:
                    self.ser.baudrate = baud
                    self.device_id = self.openimu_get_device_id()
                    if self.device_id:
                        self.set_connection_details()
                        if sys.platform.startswith('win'):
                            self.ser.set_buffer_size(rx_size = 128000, tx_size = 128000)
                        return True
        return False
    
    def set_connection_details(self):
        if "Bootloader" in self.device_id:
            print('BOOTLOADER MODE') 
            print('Connected ....{0}'.format(self.device_id))
            print('Please Upgrade FW with upgrade_fw function')
        elif self.device_id:
            print('Connected ....{0}'.format(self.device_id))
        self.save_last_port()

    def try_last_port(self):
        connection = None
        try:
            with open('connection.json') as json_data:
                connection = json.load(json_data)
            if connection:
                self.open(port=connection['port'], baud=connection['baud'])
                if self.ser:
                    self.device_id = self.openimu_get_device_id()
                    if self.device_id:
                        print('autoconnected')
                        return True
                    else:
                        print('no port')
                        return False
                else:
                    return False
        except:
            return False

    def save_last_port(self):
        connection = { "port" : self.ser.port, "baud" : self.ser.baudrate }
        with open('connection.json', 'w') as outfile:
            json.dump(connection, outfile)
    
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
        if self.ws == False: 
            if self.paused:
                self.connect()
            if self.odr_setting:
                print('Logging Started ...')
                self.logger = file_storage.OpenIMULog(self,data)
                self.logging = 1
        elif not self.paused and self.odr_setting:
            self.logger = file_storage.OpenIMULog(self,data)
            self.logging = 1
                
    def stop_log(self):
        '''Stops file or cloud logger
        '''
        self.pause()
        self.logging = 0
        self.logger.close()
        self.logger = None
        print('Logging Finished ...')

    def openimu_update_param(self, param, value):
        C = InputPacket(self.imu_properties, 'uP', param, value)
        self.write(C.bytes)
        #time.sleep(0.05)
        return self.openimu_get_packet('uP')  

    def openimu_get_param(self, param,):
        C = InputPacket(self.imu_properties, 'gP', param)
        self.write(C.bytes)
        #time.sleep(0.05)
        return self.openimu_get_packet('gP')  

    def openimu_save_config(self):
        C = InputPacket(self.imu_properties, 'sC')
        self.write(C.bytes)
        # this message currently does not return anything

    def openimu_get_all_param(self):
        C = InputPacket(self.imu_properties, 'gA')
        self.write(C.bytes)
        #time.sleep(0.05)
        return self.openimu_get_packet('gA')  

    def openimu_get_device_id(self):
        C = InputPacket(self.imu_properties, 'pG')
        self.write(C.bytes)
        #time.sleep(0.05)
        device_id = self.openimu_get_packet('pG')
        if device_id:
            device_id = device_id.decode()
            return device_id
        else: 
            return False

    def openimu_get_user_app_id(self): 
        C = InputPacket(self.imu_properties, 'gV')
        self.write(C.bytes)
        #time.sleep(0.05)
        return self.openimu_get_packet('gV')    

    def connect(self):
        '''Continous data collection loop to get and process data packets
        '''
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
        threading.Thread(target=self.start_collection_task).start()
    
    def pause(self):
        ''' Will End the data collection task and thread
        '''
        self.paused = 1 
        time.sleep(0.1)
        self.reset_buffer()
        
    def disconnect(self):
        '''Ends data collection loop and Reset settings
        '''
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
        payload = self.packet_buffer[3:self.packet_buffer[2]+3]   # extract the payload
        data = [] 

        # Find the packet in the imu_properties from unit's JSON description
        output_packet = next((x for x in self.imu_properties['userMessages']['outputPackets'] if x['name'] == self.packet_type), None)
        input_packet = next((x for x in self.imu_properties['userMessages']['inputPackets'] if x['name'] == self.packet_type), None)
        bootloader_packet = next((x for x in self.imu_properties['bootloaderMessages'] if x['name'] == self.packet_type), None)
      
        if output_packet != None:
            self.data = self.openimu_unpack_output_packet(output_packet, payload)
            if self.logging == 1 and self.logger is not None:
                self.logger.log(self, self.data)
              
        elif input_packet != None:
            
            data = self.openimu_unpack_input_packet(input_packet['responsePayload'], payload)

        elif bootloader_packet != None:

            data = self.openimu_unpack_bootloader_packet(bootloader_packet['responsePayload'], payload)

        return data

    def calc_crc(self,payload):
        '''Calculates CRC per 380 manual
        '''
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
        try:
            self.ser = serial.Serial(port, baud, timeout = 0.005)
        except Exception as e:
            print('serial port open exception' + port)
            self.ser = False

    def close(self):
        if self.ser:
            self.ser.reset_input_buffer()
            try: 
                self.ser.close()
            except:
                self.ser = False
    
    def read(self,n):
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
        try: 
            self.ser.write(n)
        except Exception as e:
            print(e)
            self.disconnect()   # sets connected to 0, and other related parameters to initial values  
            print('serial exception write')
            self.find_device() 

    def reset_buffer(self):
        try:
            self.ser.reset_input_buffer()
        except:
            self.ser = False

    def openimu_unpack_output_packet(self, output_message, payload):
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
        b = struct.pack(len_fmt, *payload)
        data = struct.unpack(pack_fmt, b)
        out = [(value['name'],data[idx]) for idx,value in enumerate(output_message['payload'])]
        data = collections.OrderedDict(out)
        return data
    
    def openimu_unpack_input_packet(self, input_message, payload):
        if input_message['type'] == 'userConfiguration':
            user_configuration = self.imu_properties['userConfiguration']
            params = []
            for parameter in user_configuration:
                id = parameter['paramId']
                type = parameter['type']
                name = parameter['name']
                value = self.openimu_unpack_one(type, payload[id*8:(id+1)*8])
                print('{0}: {1}'.format(name,value))
                params.append({ "paramId": id, "name": name, "value": value})
            return params
        elif input_message['type'] == 'userParameter':
            user_configuration = self.imu_properties['userConfiguration']
            param_id = self.openimu_unpack_one('uint32', payload[0:4]) 
            if param_id >= len(user_configuration):
                return False
            param = user_configuration[param_id]
            param_value = self.openimu_unpack_one(param['type'], payload[4:12])
            print('{0}: {1}'.format(param['name'], param_value))
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
        if bootloader_message['type'] == 'ack':
            print('Success')
            return { "error": 0 }

    def openimu_unpack_one(self, type, data):
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

    def openimu_start_bootloader(self):
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
        print(data_len, addr)
        packet = BootloaderInputPacket(self.imu_properties, 'WA', data_len, addr, data)
        self.write(packet.bytes)
        if addr == 0:
            time.sleep(5)
        self.openimu_get_packet('WA')    
       
    def openimu_upgrade_fw_prepare(self, file):
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
            self.block_blob_service = BlockBlobService(account_name='navview',
                                                    account_key='+roYuNmQbtLvq2Tn227ELmb6s1hzavh0qVQwhLORkUpM0DN7gxFc4j+DF/rEla1EsTN2goHEA1J92moOM/lfxg==',
                                                    protocol='http')
            self.block_blob_service.get_blob_to_path('apps', file, file)

        print('upgrade fw: %s' % file)
        self.max_data_len = 240
        self.addr = 0
        self.fs_len = len(self.fw)

        return True

    def openimu_finish_upgrade_fw(self):
        return self.addr >= self.fs_len

    def openimu_upgrade_fw(self, file):
        '''Upgrades firmware of connected 380 device to file provided in argument
        '''
        packet_data_len = self.max_data_len if (self.fs_len - self.addr) > self.max_data_len else (self.fs_len - self.addr)
        data = self.fw[self.addr : (self.addr + packet_data_len)]
        self.openimu_write_block(packet_data_len, self.addr, data)
        self.addr += packet_data_len

    def start_collection_task(self):
        while self.odr_setting and not self.paused:
            if self.odr_setting:
                self.openimu_get_packet(self.packet_type, True)     # get packet in stream mode
        print('End Collection Task')
        return False  # End Thread

    def openimu_get_packet(self,packet_type, stream = False):
        if not packet_type:
            return False
        data = False
        trys = 0
        while not data and trys < 200: 
            self.data_buffer = self.read(10000)
            if self.data_buffer:
                data = self.parse_buffer(packet_type, stream)
            trys += 1
        return data

    def parse_buffer(self, packet_type, stream = False):
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
                    packet_crc = 256 * self.packet_buffer[-2] + self.packet_buffer[-1]    
                    if packet_crc == self.calc_crc(self.packet_buffer[:-2]):
                        if not isinstance(packet_type, str) and not isinstance(packet_type, unicode):
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
         

 #####       

if __name__ == "__main__":
    imu = OpenIMU()
    imu.find_device()
    imu.openimu_get_all_param()
    imu.start_log()
    time.sleep(20)
    imu.stop_log()
  
	
    
