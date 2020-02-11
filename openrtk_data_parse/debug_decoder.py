import os
import sys
import time
from time import sleep
import datetime
import collections
import struct
import json

class P1Parse:
    def __init__(self, data_file, path):
        self.rawdata = data_file.read()
        self.path = path

        self.packet_buffer = []   
        self.sync_state = 0
        self.sync_pattern = collections.deque(6*[0], 6)  
        self.messageIdList = [268, 42, 99, 507]

        self.all_flag = 0
        self.rawimu_flag = 0
        self.position_flag = 0
        self.velocity_flag = 0
        self.inspva_flag = 0

        self.fp_all = None
        self.fp_imu = None
        self.fp_pos = None
        self.fp_vel = None
        self.fp_ins = None

        self.time_tag = None

        with open('openrtk_debug.json') as json_data:
            self.rtk_properties = json.load(json_data)
    
    def start_pasre(self):
        for i,new_byte in enumerate(self.rawdata):
            self.sync_pattern.append(new_byte)
            if self.sync_state == 1:
                self.packet_buffer.append(new_byte)
                if len(self.packet_buffer) >= self.packet_buffer[3]:
                    if len(self.packet_buffer) == self.packet_buffer[3] + self.packet_buffer[8] + (self.packet_buffer[9] << 8) + 4: # all packet len
                        packet_crc = (self.packet_buffer[-1]<<24) + (self.packet_buffer[-2]<<16) + (self.packet_buffer[-3]<<8) + self.packet_buffer[-4]
                        if packet_crc == self.calc_block_crc32(self.packet_buffer[:-4]): # crc
                            
                            head_time = self.packet_buffer[14:20]
                            len_fmt = '{0}B'.format(6)
                            pack_fmt = '<HI'
                            b = struct.pack(len_fmt, *head_time)
                            self.time_tag = struct.unpack(pack_fmt, b)

                            self.parse_output_packet_payload(packet_type)
                            self.packet_buffer = []
                            self.sync_state = 0
                        else:
                            print('crc err!')
                            self.sync_state = 0  # CRC did not match
            else:
                for message_id in self.messageIdList:
                    message_id_LSB = message_id & 0xff
                    message_id_MSB = (message_id >> 8) & 0xff
                    if list(self.sync_pattern) == [0xAA, 0x44, 0x12, 0x1C, message_id_LSB, message_id_MSB]: # packet type
                        packet_type = message_id
                        self.packet_buffer = [0xAA, 0x44, 0x12, 0x1C, message_id_LSB, message_id_MSB]
                        self.sync_state = 1
                        break
        if self.all_flag != 0:
            self.fp_all.close
        if self.rawimu_flag != 0:
            self.fp_imu.close
        if self.position_flag != 0:
            self.fp_pos.close
        if self.velocity_flag != 0:
            self.fp_vel.close
        if self.inspva_flag != 0:
            self.fp_ins.close
                    
    def parse_output_packet_payload(self, message_id):
        head_lenth = self.packet_buffer[3]
        payload_lenth = self.packet_buffer[8] + (self.packet_buffer[9] << 8)
        payload = self.packet_buffer[head_lenth:payload_lenth+head_lenth]
        output = next((x for x in self.rtk_properties['outputPackets'] if x['messageId'] == str(message_id)), None)

        if self.all_flag == 0:
            self.fp_all = open("./"+self.path+"/"+"all.txt", 'w')
            self.all_flag = 1

        if message_id == 268:
            if self.rawimu_flag == 0:
                self.fp_imu = open("./"+self.path+"/"+"imu.csv", 'w')
                self.write_titlebar(self.fp_imu, next((x for x in self.rtk_properties['outputPackets'] if x['name'] == 'RawImu'), None))
                self.rawimu_flag = 1
        elif message_id == 42:
            if self.position_flag == 0:
                self.fp_pos = open("./"+self.path+"/"+"pos.csv", 'w')
                self.fp_pos.write('gps_week')
                self.fp_pos.write(",")
                self.fp_pos.write('gps_millisecs')
                self.fp_pos.write(",")
                self.write_titlebar(self.fp_pos, next((x for x in self.rtk_properties['outputPackets'] if x['name'] == 'Position'), None))
                self.position_flag = 1
        elif message_id == 99:
            if self.velocity_flag == 0:
                self.fp_vel = open("./"+self.path+"/"+"vel.csv", 'w')
                self.fp_vel.write('gps_week')
                self.fp_vel.write(",")
                self.fp_vel.write('gps_millisecs')
                self.fp_vel.write(",")
                self.write_titlebar(self.fp_vel, next((x for x in self.rtk_properties['outputPackets'] if x['name'] == 'Velocity'), None))
                self.velocity_flag = 1
        elif message_id == 507:
            if self.inspva_flag == 0:
                self.fp_ins = open("./"+self.path+"/"+"ins.csv", 'w')
                self.write_titlebar(self.fp_ins, next((x for x in self.rtk_properties['outputPackets'] if x['name'] == 'InsPVA'), None))
                self.inspva_flag = 1

        if output != None:
            data = self.openrtk_unpack_output_packet(output, payload)
            if data != None:
                if message_id == 268:
                    self.fp_all.write("$GPIMU,")
                    for i in range(len(data)):
                        if i == 1:
                            self.fp_imu.write(format((data[i]/1000), '11.4f'))
                            self.fp_all.write(format((data[i]/1000), '11.4f'))
                        elif i == 2:
                            self.fp_imu.write(format(data[i], '10.4f'))
                            self.fp_all.write(format(data[i], '10.4f'))
                        elif i >= 3 and i <=8:
                            self.fp_imu.write(format(data[i]*9.7803267714e0, '14.10f'))
                            self.fp_all.write(format(data[i]*9.7803267714e0, '14.10f'))
                        else:
                            self.fp_imu.write(data[i].__str__())
                            self.fp_all.write(data[i].__str__())
                        if i < len(data)-1:
                            self.fp_imu.write(",")
                            self.fp_all.write(",")
                    self.fp_imu.write("\n")
                    self.fp_all.write("\n")
                elif message_id == 42:
                    self.fp_all.write("$GPGNSS,")
                    for i in range(len(self.time_tag)):
                        if i == 1:
                            self.fp_pos.write(format((self.time_tag[i]/1000), '11.4f'))
                            self.fp_all.write(format((self.time_tag[i]/1000), '11.4f'))
                        else:
                            self.fp_pos.write(self.time_tag[i].__str__())
                            self.fp_all.write(self.time_tag[i].__str__())
                        self.fp_pos.write(",")
                        self.fp_all.write(",")
                    for i in range(len(data)):
                        if i == 0 or i == 1:
                            self.fp_pos.write(format(data[i], '3.0f'))
                            self.fp_all.write(format(data[i], '3.0f'))
                        elif i == 2 or i == 3:
                            self.fp_pos.write(format(data[i], '14.9f'))
                            self.fp_all.write(format(data[i], '14.9f'))
                        elif i >= 4:
                            self.fp_pos.write(format(data[i], '10.4f'))
                            self.fp_all.write(format(data[i], '10.4f'))
                        else:
                            self.fp_pos.write(data[i].__str__())
                            self.fp_all.write(data[i].__str__())
                        if i < len(data)-1:
                            self.fp_pos.write(",")
                            self.fp_all.write(",")
                    self.fp_pos.write("\n")
                    self.fp_all.write("\n")
                elif message_id == 99:
                    self.fp_all.write("$GPVEL,")
                    for i in range(len(self.time_tag)):
                        if i == 1:
                            self.fp_vel.write(format((self.time_tag[i]/1000), '11.4f'))
                            self.fp_all.write(format((self.time_tag[i]/1000), '11.4f'))
                        else:
                            self.fp_vel.write(self.time_tag[i].__str__())
                            self.fp_all.write(self.time_tag[i].__str__())
                        self.fp_vel.write(",")
                        self.fp_all.write(",")
                    for i in range(len(data)):
                        if i == 0 or i == 1:
                            self.fp_vel.write(format(data[i], '3.0f'))
                            self.fp_all.write(format(data[i], '3.0f'))
                        elif i == 2 or i == 3:
                            self.fp_vel.write(format(data[i], '10.4f'))
                            self.fp_all.write(format(data[i], '10.4f'))
                        elif i >= 4 and i <= 6:
                            self.fp_vel.write(format(data[i], '14.9f'))
                            self.fp_all.write(format(data[i], '14.9f'))
                        else:
                            self.fp_vel.write(data[i].__str__())
                            self.fp_all.write(data[i].__str__())
                        if i < len(data)-1:
                            self.fp_vel.write(",")
                            self.fp_all.write(",")
                    self.fp_vel.write("\n")
                    self.fp_all.write("\n")
                elif message_id == 507:
                    self.fp_all.write("$GPINS,")
                    for i in range(len(data)):
                        if i == 1:
                            self.fp_ins.write(format((data[i]/1000), '11.4f'))
                            self.fp_all.write(format((data[i]/1000), '11.4f'))
                        elif i == 2 or i == 3:
                            self.fp_ins.write(format(data[i], '14.9f'))
                            self.fp_all.write(format(data[i], '14.9f'))
                        elif i >= 4 and i <=7:
                            self.fp_ins.write(format(data[i], '10.4f'))
                            self.fp_all.write(format(data[i], '10.4f'))
                        elif i >= 8 and i <=10:
                            self.fp_ins.write(format(data[i], '14.9f'))
                            self.fp_all.write(format(data[i], '14.9f'))
                        else:
                            self.fp_ins.write(data[i].__str__())
                            self.fp_all.write(data[i].__str__())
                        if i < len(data)-1:
                            self.fp_ins.write(",")
                            self.fp_all.write(",")
                    self.fp_ins.write("\n")
                    self.fp_all.write("\n")
        else:
            print('no packet type in json')

    def openrtk_unpack_output_packet(self, output, payload):
        length = 0
        pack_fmt = '<'
        for value in output['payload']:
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
            elif value['type'] == 'int8':
                pack_fmt += 'b'
                length += 1
        len_fmt = '{0}B'.format(length)

        try:
            b = struct.pack(len_fmt, *payload)
            data = struct.unpack(pack_fmt, b)
            return data
        except Exception as e:
            print("error happened when decode the payload, pls restart IMU firmware: {0}".format(e))    
    
    def write_titlebar(self, file, output_message):
        for value in output_message['payload']:
            file.write(value['name'])
            file.write(",")
        file.write("\n")

    def calc_32value(self, value):
        ulCRC = value
        for j in range(0,8):
            if (ulCRC & 1):
                ulCRC = (ulCRC >> 1) ^ 0xEDB88320
            else:
                ulCRC = ulCRC >> 1
        return ulCRC

    def calc_block_crc32(self, payload):
        ulCRC = 0
        for bytedata in payload:
            ulTemp1 = (ulCRC >> 8) & 0x00FFFFFF
            ulTemp2 = self.calc_32value((ulCRC ^ bytedata) & 0xff)
            ulCRC = ulTemp1 ^ ulTemp2
        return ulCRC

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
        rawdata_filepath = str(sys.argv[1])
        try:
            with open(rawdata_filepath, 'rb') as fp_rawdata:
                path = mkdir() # create dir

                parse = P1Parse(fp_rawdata, path)
                parse.start_pasre()

                fp_rawdata.close
        except FileNotFoundError:
            print("can't find this file")
    else:
        print("USAGE: python .\debug_decoder.py [file path]")

