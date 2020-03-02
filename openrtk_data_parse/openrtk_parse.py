import os
import sys
import argparse
import time
from time import sleep
import datetime
import collections
import struct
import json

is_windows = sys.platform.__contains__(
    'win32') or sys.platform.__contains__('win64')
is_later_py_38 = sys.version_info > (3, 8)
is_later_py_3 = sys.version_info > (3, 0)

class UserRawParse:
    def __init__(self, data_file, path):
        self.rawdata = []
        if is_later_py_3:
            self.rawdata = data_file.read()
        else:
            self.filedata = data_file.read()
            for c in self.filedata:
                self.rawdata.append(ord(c))
        self.path = path

        self.packet_buffer = []   
        self.sync_state = 0
        self.sync_pattern = collections.deque(4*[0], 4)
        self.userPacketsTypeList = []

        self.log_files = {}

        with open('openrtk_packets.json') as json_data:
            self.rtk_properties = json.load(json_data)

    def start_pasre(self):
        self.userPacketsTypeList = self.rtk_properties['userPacketsTypeList']
        packet_type = ''
        for i,new_byte in enumerate(self.rawdata):
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
                        print('user data crc err!')
                        self.sync_state = 0  # CRC did not match
            else:
                for packet_type in self.userPacketsTypeList:
                    packet_type_0 = ord(packet_type[0])
                    packet_type_1 = ord(packet_type[1])
                    if list(self.sync_pattern) == [0x55, 0x55, packet_type_0, packet_type_1]: # packet type 
                        self.packet_buffer = [packet_type_0, packet_type_1]
                        self.sync_state = 1
                        break
        for i, (k, v) in enumerate(self.log_files.items()):
            v.close()
        self.log_files.clear()

    def start_log(self, output):
        if output['name'] not in self.log_files.keys():
            self.log_files[output['name']] = open(self.path + output['name'] + '.csv', 'w')
            self.write_titlebar(self.log_files[output['name']], output)

    def log(self, name, data):
        for i in range(len(data)):
            self.log_files[name].write(data[i].__str__())
            self.log_files[name].write(",")
        self.log_files[name].write("\n")

    def parse_output_packet_payload(self, packet_type):
        payload_lenth = self.packet_buffer[2]
        payload = self.packet_buffer[3:payload_lenth+3]
        output = next((x for x in self.rtk_properties['userOutputPackets'] if x['name'] == packet_type), None)

        if output != None:
            self.start_log(output)
            self.openrtk_unpack_output_packet(output, payload, payload_lenth)
        else:
            print('no packet type {0} in json'.format(packet_type))

    def openrtk_unpack_output_packet(self, output, payload, payload_lenth):
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
        len_fmt = '{0}B'.format(length)

        packet_num = payload_lenth // length

        if output['isList']:
            for i in range(packet_num):
                payload_c = payload[i*length:(i+1)*length]
                try:
                    b = struct.pack(len_fmt, *payload_c)
                    data = struct.unpack(pack_fmt, b)
                    self.log(output['name'], data)
                except Exception as e:
                    print("error happened when decode the payload {0}".format(e))
        else:
            try:
                b = struct.pack(len_fmt, *payload)
                data = struct.unpack(pack_fmt, b)
                self.log(output['name'], data)
            except Exception as e:
                print("error happened when decode the payload, pls restart IMU firmware: {0}".format(e))    
    
    def write_titlebar(self, file, output):
        for value in output['payload']:
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


class DebugRawParse:
    def __init__(self, data_file, path):
        self.rawdata = []
        if is_later_py_3:
            self.rawdata = data_file.read()
        else:
            self.filedata = data_file.read()
            for c in self.filedata:
                self.rawdata.append(ord(c))
        self.path = path

        self.packet_buffer = []   
        self.sync_state = 0
        self.sync_pattern = collections.deque(6*[0], 6)  
        self.debugPacketsTypeList = []

        self.log_files = {}
        self.fp_all = None

        self.time_tag = None # in packet's head

        with open('openrtk_packets.json') as json_data:
            self.rtk_properties = json.load(json_data)
    
    def start_pasre(self):
        self.debugPacketsTypeList = self.rtk_properties['debugPacketsTypeList']
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
                            print('debug data crc err!')
                            self.sync_state = 0  # CRC did not match
            else:
                for message_id in self.debugPacketsTypeList:
                    message_id_LSB = message_id & 0xff
                    message_id_MSB = (message_id >> 8) & 0xff
                    if list(self.sync_pattern) == [0xAA, 0x44, 0x12, 0x1C, message_id_LSB, message_id_MSB]: # packet type
                        packet_type = message_id
                        self.packet_buffer = [0xAA, 0x44, 0x12, 0x1C, message_id_LSB, message_id_MSB]
                        self.sync_state = 1
                        break
        for i, (k, v) in enumerate(self.log_files.items()):
            v.close()
        self.log_files.clear()
        if self.fp_all is not None:
            self.fp_all.close()

    def start_log(self, output):
        if self.fp_all is None:
            self.fp_all = open(self.path + "all.txt", 'w')
        if output['name'] not in self.log_files.keys():
            self.log_files[output['name']] = open(self.path + output['name'] + '.csv', 'w')
            self.write_titlebar(self.log_files[output['name']], output)
    
    def log(self, name, data):
        if name == 'imu':
            self.fp_all.write("$GPIMU,")
            for i in range(len(data)):
                if i == 1:
                    self.log_files[name].write(format((data[i]/1000), '11.4f'))
                    self.fp_all.write(format((data[i]/1000), '11.4f'))
                elif i == 2:
                    self.log_files[name].write(format(data[i], '10.4f'))
                    self.fp_all.write(format(data[i], '10.4f'))
                elif i == 3:
                    self.log_files[name].write(format(data[5]*9.7803267714e0, '14.10f'))
                    self.fp_all.write(format(data[5]*9.7803267714e0, '14.10f'))
                elif i == 5:
                    self.log_files[name].write(format(data[3]*9.7803267714e0, '14.10f'))
                    self.fp_all.write(format(data[3]*9.7803267714e0, '14.10f'))
                elif i == 6:
                    self.log_files[name].write(format(data[8]*9.7803267714e0, '14.10f'))
                    self.fp_all.write(format(data[8]*9.7803267714e0, '14.10f'))
                elif i == 8:
                    self.log_files[name].write(format(data[6]*9.7803267714e0, '14.10f'))
                    self.fp_all.write(format(data[6]*9.7803267714e0, '14.10f'))
                elif i == 4 or i == 7:
                    self.log_files[name].write(format(data[i]*9.7803267714e0, '14.10f'))
                    self.fp_all.write(format(data[i]*9.7803267714e0, '14.10f'))
                else:
                    self.log_files[name].write(data[i].__str__())
                    self.fp_all.write(data[i].__str__())
                if i < len(data)-1:
                    self.log_files[name].write(",")
                    self.fp_all.write(",")
            self.log_files[name].write("\n")
            self.fp_all.write("\n")
        elif name == 'pos':
            self.fp_all.write("$GPGNSS,")
            for i in range(len(self.time_tag)):
                if i == 1:
                    self.log_files[name].write(format((float(self.time_tag[i])/1000), '11.4f'))
                    self.fp_all.write(format((float(self.time_tag[i])/1000), '11.4f'))
                else:
                    self.log_files[name].write(self.time_tag[i].__str__())
                    self.fp_all.write(self.time_tag[i].__str__())
                self.log_files[name].write(",")
                self.fp_all.write(",")
            for i in range(len(data)):
                if i == 0 or i == 1:
                    self.log_files[name].write(format(data[i], '3.0f'))
                    self.fp_all.write(format(data[i], '3.0f'))
                elif i == 2 or i == 3:
                    self.log_files[name].write(format(data[i], '14.9f'))
                    self.fp_all.write(format(data[i], '14.9f'))
                elif i >= 4:
                    self.log_files[name].write(format(data[i], '10.4f'))
                    self.fp_all.write(format(data[i], '10.4f'))
                else:
                    self.log_files[name].write(data[i].__str__())
                    self.fp_all.write(data[i].__str__())
                if i < len(data)-1:
                    self.log_files[name].write(",")
                    self.fp_all.write(",")
            self.log_files[name].write("\n")
            self.fp_all.write("\n")
        elif name == 'vel':
            self.fp_all.write("$GPVEL,")
            for i in range(len(self.time_tag)):
                if i == 1:
                    self.log_files[name].write(format((float(self.time_tag[i])/1000), '11.4f'))
                    self.fp_all.write(format((float(self.time_tag[i])/1000), '11.4f'))
                else:
                    self.log_files[name].write(self.time_tag[i].__str__())
                    self.fp_all.write(self.time_tag[i].__str__())
                self.log_files[name].write(",")
                self.fp_all.write(",")
            for i in range(len(data)):
                if i == 0 or i == 1:
                    self.log_files[name].write(format(data[i], '3.0f'))
                    self.fp_all.write(format(data[i], '3.0f'))
                elif i == 2 or i == 3:
                    self.log_files[name].write(format(data[i], '10.4f'))
                    self.fp_all.write(format(data[i], '10.4f'))
                elif i >= 4 and i <= 6:
                    self.log_files[name].write(format(data[i], '14.9f'))
                    self.fp_all.write(format(data[i], '14.9f'))
                else:
                    self.log_files[name].write(data[i].__str__())
                    self.fp_all.write(data[i].__str__())
                if i < len(data)-1:
                    self.log_files[name].write(",")
                    self.fp_all.write(",")
            self.log_files[name].write("\n")
            self.fp_all.write("\n")
        elif name == 'ins':
            self.fp_all.write("$GPINS,")
            for i in range(len(data)):
                if i == 1:
                    self.log_files[name].write(format((data[i]/1000), '11.4f'))
                    self.fp_all.write(format((data[i]/1000), '11.4f'))
                elif i == 2 or i == 3:
                    self.log_files[name].write(format(data[i], '14.9f'))
                    self.fp_all.write(format(data[i], '14.9f'))
                elif i >= 4 and i <=7:
                    self.log_files[name].write(format(data[i], '10.4f'))
                    self.fp_all.write(format(data[i], '10.4f'))
                elif i >= 8 and i <=10:
                    self.log_files[name].write(format(data[i], '14.9f'))
                    self.fp_all.write(format(data[i], '14.9f'))
                else:
                    self.log_files[name].write(data[i].__str__())
                    self.fp_all.write(data[i].__str__())
                if i < len(data)-1:
                    self.log_files[name].write(",")
                    self.fp_all.write(",")
            self.log_files[name].write("\n")
            self.fp_all.write("\n")

    def parse_output_packet_payload(self, message_id):
        head_lenth = self.packet_buffer[3]
        payload_lenth = self.packet_buffer[8] + (self.packet_buffer[9] << 8)
        payload = self.packet_buffer[head_lenth:payload_lenth+head_lenth]
        output = next((x for x in self.rtk_properties['debugOutputPackets'] if x['messageId'] == str(message_id)), None)

        if output != None:
            self.start_log(output)
            data = self.openrtk_unpack_output_packet(output, payload)
            if data != None:
                self.log(output['name'], data)
        else:
            print('no packet type {0} in json'.format(str(message_id)))

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
    
    def write_titlebar(self, file, output):
        if output['needHeadTime']:
            file.write('gps_week')
            file.write(",")
            file.write('gps_millisecs')
            file.write(",")
        for value in output['payload']:
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


def mkdir(file_path):
    path = file_path.strip()
    path = path.rstrip("\\")
    path = path.rstrip(".bin")
    # if is_later_py_3:
    #     path = path + '_p3'
    # else:
    #     path = path + '_p2'
    path = path + '_p'
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def receive_args():
    parser = argparse.ArgumentParser()
    parser.description = argparse.ArgumentParser(
        description='Aceinna OpenRTK python parse input args command:')
    parser.add_argument("-p", type=str, help="folder path", default='.')
    parser.add_argument("-f", type=str, help="bin file", default='*')
    parser.add_argument("-c", type=int, help="0:user and debug | 1:user | 2:debug", default='0')
    return parser.parse_args()

if __name__ == '__main__':
    # compatible code for windows python 3.8
    if is_windows and is_later_py_38:
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    args = receive_args()
    if args.c > 2:
        args.c = 0

    for file_name in os.listdir(args.p):
        file_path = args.p + '/' + file_name
        if os.path.isfile(file_path):
            if file_name.startswith('user') or file_name.startswith('debug'):
                path = mkdir(file_path)
                try:
                    with open(file_path, 'rb') as fp_rawdata:
                        if file_name.startswith('user'):
                            parse = UserRawParse(fp_rawdata, path + '/' + file_name.rstrip(".bin") + '_')
                        elif file_name.startswith('debug'):
                            parse = DebugRawParse(fp_rawdata, path + '/' + file_name.rstrip(".bin") + '_')
                        parse.start_pasre()
                        fp_rawdata.close
                except Exception as e:
                    print(e)
                
