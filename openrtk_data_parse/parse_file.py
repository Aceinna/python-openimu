import os
import sys
import time
from time import sleep
import datetime
import collections
import struct
import json

class UartParse:
    def __init__(self, data_file, data_type):
        self.data_buffer = []
        self.packet_buffer = []   
        self.sync_state = 0
        self.sync_pattern = collections.deque(4*[0], 4)  
        self.packetTypeListFromOptions = []
        self.data_type = data_type
        self.first = 0

        self.data_buffer = data_file.read()
        with open('openrtk.json') as json_data:
            self.rtk_properties = json.load(json_data)

        if data_type == 'user':
            self.packetTypeListFromOptions = {'pS', 'sR', 'sK'}
        elif data_type == 'debug':
            self.packetTypeListFromOptions = {'e1', 'e2'}

    def start_pasre(self):
        # packetTypeListFromOptions = []
        # for x in self.rtk_properties['userConfiguration']:
        #     if x['paramId'] == 3:
        #         packetTypeListFromOptions = x['options'] # get packet type list in rtk_properties
        #         break

        packet_type = 0
        for i,new_byte in enumerate(self.data_buffer):
            self.sync_pattern.append(new_byte)
            if self.sync_state == 1:
                self.packet_buffer.append(new_byte)
                if len(self.packet_buffer) == self.packet_buffer[2] + 5: # packet len
                    packet_crc = 256 * self.packet_buffer[-2] + self.packet_buffer[-1]    
                    if packet_crc == self.calc_crc(self.packet_buffer[:-2]): # packet crc
                        self.parse_output_packet_payload(packet_type) 
                        self.packet_buffer = []
                        self.sync_state = 0
                    else:
                        print('crc err!')
                        self.sync_state = 0  # CRC did not match
            else:
                for packet_type in self.packetTypeListFromOptions:
                    packet_type_0 = ord(packet_type[0])
                    packet_type_1 = ord(packet_type[1])
                    if list(self.sync_pattern) == [85, 85, packet_type_0, packet_type_1]: # packet type 
                        self.packet_buffer = [packet_type_0, packet_type_1]
                        self.sync_state = 1
                        break
    
    def parse_output_packet_payload(self, packet_type):
        payload_lenth = self.packet_buffer[2]
        payload = self.packet_buffer[3:payload_lenth+3]
        output_packet = next((x for x in self.rtk_properties['userMessages']['outputPackets'] if x['name'] == packet_type), None)

        if self.first == 0:
            if self.data_type == 'user':
                self.write_titlebar(pos_file, 'pS', next((x for x in self.rtk_properties['userMessages']['outputPackets'] if x['name'] == 'pS'), None))
                self.write_titlebar(sky_file, 'sK', next((x for x in self.rtk_properties['userMessages']['outputPackets'] if x['name'] == 'sK'), None))
            elif self.data_type == 'debug':
                self.write_titlebar(imu_file, packet_type, output_packet)
            self.first = 1

        if output_packet != None:
            if packet_type == 'sR' or packet_type == 'sK':
                self.openrtk_unpack_output_packet(output_packet, payload, payload_lenth, True)
            else :
                self.openrtk_unpack_output_packet(output_packet, payload, payload_lenth)
        else:
            print('no packet type in json')

    def openrtk_unpack_output_packet(self, output_message, payload, payload_lenth, is_list = False):
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

        packet_num = payload_lenth // length
        # if packet_num > 1:
        if is_list:
            for i in range(packet_num):
                payload_c = payload[i*length:(i+1)*length]
                try:
                    b = struct.pack(len_fmt, *payload_c)
                    data = struct.unpack(pack_fmt, b)
                    for i in range(len(data)):
                        sky_file.write(data[i].__str__())
                        sky_file.write(",")
                    sky_file.write("\n")
                except Exception as e:
                    print("error happened when decode the payload, pls restart IMU firmware: {0}".format(e))
        else:
            try:
                b = struct.pack(len_fmt, *payload)
                data = struct.unpack(pack_fmt, b)
                if self.data_type == 'debug':
                    for i in range(len(data)):
                        imu_file.write(data[i].__str__())
                        imu_file.write(",")
                    imu_file.write("\n")
                elif self.data_type == 'user':
                    for i in range(len(data)):
                        pos_file.write(data[i].__str__())
                        pos_file.write(",")
                    pos_file.write("\n")
            except Exception as e:
                print("error happened when decode the payload, pls restart IMU firmware: {0}".format(e))    
    
    def write_titlebar(self, file, packet_type, output_message):
        for value in output_message['payload']:
            file.write(value['name'])
            file.write(",")
        file.write("\n")

    def calc_crc(self, payload):
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

def mkdir():
    path='./' + time.strftime("%Y-%m-%d_%H-%M-%S")
    path=path.strip()
    path=path.rstrip("\\")
    isExists=os.path.exists(path)
    if not isExists:
        os.makedirs(path)
    return path

if __name__ == "__main__":
    if len(sys.argv) == 2:
        data_file_name = str(sys.argv[1])
        try:
            with open(data_file_name, 'rb') as data_file:
                data_type = 'user'

                path = mkdir() # create dir
                file_name = data_file_name.split('\\')[-1]

                if data_type == 'user' :
                    pos_file = open('./'+ path +'/'+ file_name + '_pos.csv', 'w')
                    sky_file = open('./'+ path +'/'+ file_name + '_sky.csv', 'w')

                    parse = UartParse(data_file, data_type)
                    parse.start_pasre()

                    pos_file.close
                    sky_file.close
                elif data_type == 'debug':
                    imu_file = open(data_file_name+'_imu.csv', 'w')

                    parse = UartParse(data_file, data_type)
                    parse.start_pasre()

                    imu_file.close
                else:
                    printf("data type err!")
                
                data_file.close
        except FileNotFoundError:
            print("can't find data file")
    else:
        print("USAGE: python .\parse_file.py [file path]")
    
