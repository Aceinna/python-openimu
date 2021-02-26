import os
import sys
import argparse
import time
from time import sleep
import datetime
import collections
import struct
import json
import math

is_windows = sys.platform.__contains__(
    'win32') or sys.platform.__contains__('win64')
is_later_py_38 = sys.version_info > (3, 8)
is_later_py_3 = sys.version_info > (3, 0)



class ZouParse:
	def __init__(self, data_file, path):
		self.zoudata = []
		if is_later_py_3:
			self.zoudata = data_file.read()
		else:
			self.filedata = data_file.read()
			for c in self.filedata:
				self.zoudata.append(ord(c))
		self.path = path

		self.packet_buffer = []   
		self.sync_state = 0
		self.sync_pattern = collections.deque(4*[0], 4)  
		self.zouPacketsTypeList = []

		self.log_files = {}
		self.fp_all = None

		self.time_tag = None # in packet's head

		self.err_count = 0

		with open('openrtk_packets.json') as json_data:
			self.rtk_properties = json.load(json_data)

	def start_pasre(self):
		self.zouPacketsTypeList = self.rtk_properties['zouPacketsTypeList']
		for i,new_byte in enumerate(self.zoudata):
			self.sync_pattern.append(new_byte)
			if self.sync_state == 1:
				self.packet_buffer.append(new_byte)
				if (self.cur_message_id == 'fmim' and len(self.packet_buffer) == 52) or\
				(self.cur_message_id == 'fmig' and len(self.packet_buffer) == 95) or\
				(self.cur_message_id == 'fmin' and len(self.packet_buffer) == 100):
					if (self.packet_buffer[-1]) == ord('d') and self.packet_buffer[-2] == ord('e'):
						head_time = self.packet_buffer[5:13]
						len_fmt = '{0}B'.format(8)
						pack_fmt = 'd'
						b = struct.pack(len_fmt, *head_time)
						self.time_tag = struct.unpack(pack_fmt, b)
						self.parse_output_packet_payload(packet_type)
						
						self.packet_buffer = []
						self.sync_state = 0
					else:
						self.err_count = self.err_count + 1
						#print('debug data crc err. type {0} count{1}'.format(packet_type, self.err_count))
						self.sync_state = 0  # CRC did not match
			else:
				for message_id in self.zouPacketsTypeList:
					message_id_list = []				
					message_id_list = list(message_id)
					self.cur_message_id = message_id
					message_id_list_int = []
					for ele in message_id_list:
						message_id_list_int.append(ord(ele))
					if list(self.sync_pattern) == message_id_list_int: # packet type
						packet_type = message_id
						self.packet_buffer = message_id_list_int
						self.sync_state = 1
						break
					#test = input()
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

	def write_data(self, name, data):
		self.log_files[name].write(data.__str__())
		self.fp_all.write(data.__str__())

	def write_data_fm(self, name, data, fm):
		self.log_files[name].write(format(data, fm))
		self.fp_all.write(format(data, fm))

	def write_data_output(self, name, data):
		pass

	def log(self, output, data):
		name = output['name']
		payload = output['payload']

		if name == 'imu':
			self.fp_all.write("$imu,")
			for i in range(len(data)):
				if payload[i]['need']:
					if i == 1:
						self.write_data_fm(name, data[i], payload[i]['format'])
					elif payload[i]['name'] == 'time':
						time_ms = data[i] - int(data[i])
						time_h = int(int(data[i]) / 10000)
						time_m = int((int(data[i]) - time_h*10000) / 100)
						time_s = (int(data[i]) - time_h*10000 - time_m*100)
						time_useful = time_h*3600 + time_m*60 + time_s + time_ms
						self.write_data_fm(name, time_useful, payload[i]['format'])
					else:
						self.write_data_fm(name, data[i], payload[i]['format'])
					if payload[i]['need'] == 1:
						self.write_data(name, ",")
		elif name == 'gnss':
			self.fp_all.write("$gnss,")
			for i in range(len(data)):
				if payload[i]['need']:
					if (payload[i]['name'] == 'latitude') or (payload[i]['name'] == 'longitude'):
						value_int = int(data[i])
						value_float = data[i] - value_int
						value_two_float = int(value_float*100)
						value_rest_float = (data[i] - value_int - value_two_float/100) * 10000
						value_useful = value_int + value_two_float/60 + value_rest_float/3600

						self.write_data_fm(name, value_useful, payload[i]['format'])
					elif payload[i]['name'] == 'time':
						time_ms = data[i] - int(data[i])
						time_h = int(int(data[i]) / 10000)
						time_m = int((int(data[i]) - time_h*10000) / 100)
						time_s = (int(data[i]) - time_h*10000 - time_m*100)
						time_useful = time_h*3600 + time_m*60 + time_s + time_ms
						self.write_data_fm(name, time_useful, payload[i]['format'])
					else:
						self.write_data_fm(name, data[i], payload[i]['format'])
					if payload[i]['need'] == 1:
						self.write_data(name, ",")
		elif name == 'navi':
			self.fp_all.write("$gnss,")
			for i in range(len(data)):
				if payload[i]['need']:
					if (payload[i]['name'] == 'latitude') or (payload[i]['name'] == 'longitude'):
						value_int = int(data[i])
						value_float = data[i] - value_int
						value_two_float = int(value_float*100)
						value_rest_float = (data[i] - value_int - value_two_float/100) * 10000
						value_useful = value_int + value_two_float/60 + value_rest_float/3600
						
						self.write_data_fm(name, value_useful, payload[i]['format'])
					elif payload[i]['name'] == 'time':
						time_ms = data[i] - int(data[i])
						time_h = int(int(data[i]) / 10000)
						time_m = int((int(data[i]) - time_h*10000) / 100)
						time_s = (int(data[i]) - time_h*10000 - time_m*100)
						time_useful = time_h*3600 + time_m*60 + time_s + time_ms
						self.write_data_fm(name, time_useful, payload[i]['format'])
					else:
						self.write_data_fm(name, data[i], payload[i]['format'])
					if payload[i]['need'] == 1:
						self.write_data(name, ",")
			pass

		self.write_data(name, "\n")

	def parse_output_packet_payload(self, message_id):
		'''zou packet'''
		if message_id == 'fmim':
			payload = self.packet_buffer[len(message_id):48]
		elif message_id == 'fmig':
			#print('het fmig')
			payload = self.packet_buffer[len(message_id):91]
		elif message_id == "fmin":
			#print('get fmin')
			payload = self.packet_buffer[len(message_id):96]			
		output = next((x for x in self.rtk_properties['zouOutputPackets'] if x['messageId'] == str(message_id)), None)
		if output != None:
			self.start_log(output)
			data = self.openrtk_unpack_output_packet(output, payload)

			if data != None:
				self.log(output, data)
		else:
			print('no packet type {0} in json'.format(str(message_id)))

	def openrtk_unpack_output_packet(self, output, payload):
		length = 0
		pack_fmt = '<'
		if self.cur_message_id == "fmim":
			for value in output['payload']:
				if value['type'] == 'double':
					pack_fmt += 'd'
					length += 8
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
		elif self.cur_message_id == "fmig":
			for value in output['payload']:
				if value['type'] == 'double':
					pack_fmt += 'd'
					length += 8
				elif value['type'] == 'double':
					pack_fmt += 'd'
					length += 8
				elif value['type'] == 'double':
					pack_fmt += 'd'
					length += 8
				elif value['type'] == 'double':
					pack_fmt += 'd'
					length += 8
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'uint8':
					pack_fmt += 'B'
					length += 1	
				elif value['type'] == 'uint8':
					pack_fmt += 'B'
					length += 1		
				elif value['type'] == 'uint8':
					pack_fmt += 'B'
					length += 1
		elif self.cur_message_id == "fmin":
			for value in output['payload']:
				if value['type'] == 'double':
					pack_fmt += 'd'
					length += 8
				elif value['type'] == 'double':
					pack_fmt += 'd'
					length += 8
				elif value['type'] == 'double':
					pack_fmt += 'd'
					length += 8
				elif value['type'] == 'double':
					pack_fmt += 'd'
					length += 8
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'float':
					pack_fmt += 'f'
					length += 4		
				elif value['type'] == 'uint32':
					pack_fmt += 'I'
					length += 4	
		len_fmt = '{0}B'.format(length)

		try:
			b = struct.pack(len_fmt, *payload)
			data = struct.unpack(pack_fmt, b)
			return data
		except Exception as e:
			print("error happened when decode the payload, pls restart IMU firmware: {0}".format(e))    

	def write_titlebar(self, file, output):
		if output['name'] == 'gnss':
			for value in output['payload']:
				if value['need'] and value['name'] != 'position_type':
					file.write(value['name'])
					file.write(",")
			file.write(",")
		elif output['name'] == 'imu':
			for value in output['payload']:
				if value['need']:
					file.write(value['name'])
					file.write(",")
		elif output['name'] == 'navi':
			for value in output['payload']:
				if value['need']:
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

class UserRawParse:
    def __init__(self, data_file, path, json_setting, inskml_rate):
        self.rawdata = []
        if is_later_py_3:
            self.rawdata = data_file.read()
        else:
            self.filedata = data_file.read()
            for c in self.filedata:
                self.rawdata.append(ord(c))
        self.path = path
        self.inskml_rate = 1/inskml_rate
        self.packet_buffer = []   
        self.sync_state = 0
        self.sync_pattern = collections.deque(4*[0], 4)
        self.userPacketsTypeList = []
        self.userNMEAList = []
        self.nmea_pattern = collections.deque(6*[0], 6)
        self.nmea_buffer = []
        self.nmea_sync = 0
        self.log_files = {}
        self.f_nmea = None
        self.f_process = None
        self.f_imu = None
        self.f_odo = None
        self.f_gnssposvel = None
        self.f_ins = None
        self.f_gnss_kml = None
        self.f_ins_kml = None
        self.gnssdata = []
        self.insdata = []
        self.pkfmt = {}
        self.last_time = 0

        with open(json_setting) as json_data:
            self.rtk_properties = json.load(json_data)

    def start_pasre(self):
        self.userPacketsTypeList = self.rtk_properties['userPacketsTypeList']
        self.userNMEAList = self.rtk_properties['userNMEAList']
        for x in self.rtk_properties['userOutputPackets']:
            length = 0
            pack_fmt = '<'
            for value in x['payload']:
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
            fmt_dic = collections.OrderedDict()
            fmt_dic['len'] = length
            fmt_dic['len_b'] = len_fmt
            fmt_dic['pack'] = pack_fmt
            self.pkfmt[x['name']] = fmt_dic
        
        self.f_process = open(self.path[0:-1] + '-process', 'w')
        self.f_gnssposvel = open(self.path[0:-1] + '-gnssposvel.txt', 'w')
        self.f_imu = open(self.path[0:-1] + '-imu.txt', 'w')
        self.f_odo = open(self.path[0:-1] + '-odo.txt', 'w')
        self.f_ins = open(self.path[0:-1] + '-ins.txt', 'w')
        self.f_nmea = open(self.path[0:-1] + '-nmea', 'wb')
        self.f_gnss_kml = open(self.path[0:-1] + '-gnss.kml', 'w')
        self.f_ins_kml = open(self.path[0:-1] + '-ins.kml', 'w')

        packet_type = ''
        nmea_header_len = 0
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
                        #print('user data crc err!')
                        self.sync_state = 0  # CRC did not match
            else:
                for packet_type in self.userPacketsTypeList:
                    packet_type_0 = ord(packet_type[0])
                    packet_type_1 = ord(packet_type[1])
                    if list(self.sync_pattern) == [0x55, 0x55, packet_type_0, packet_type_1]: # packet type 
                        self.packet_buffer = [packet_type_0, packet_type_1]
                        self.sync_state = 1
                        break
                # nmea detect
                if self.nmea_sync == 0:
                    if new_byte == 0x24:
                        self.nmea_buffer = []
                        self.nmea_pattern = []
                        self.nmea_sync = 1
                        self.nmea_buffer.append(new_byte)
                        self.nmea_pattern.append(new_byte)
                        nmea_header_len = 1
                elif self.nmea_sync == 1:
                    self.nmea_buffer.append(new_byte)
                    self.nmea_pattern.append(new_byte)
                    nmea_header_len = nmea_header_len + 1
                    if nmea_header_len == 6:
                        for nmea_type in self.userNMEAList:
                            nmea_type_0 = ord(nmea_type[0])
                            nmea_type_1 = ord(nmea_type[1])
                            nmea_type_2 = ord(nmea_type[2])
                            nmea_type_3 = ord(nmea_type[3])
                            nmea_type_4 = ord(nmea_type[4])
                            nmea_type_5 = ord(nmea_type[5])
                            if list(self.nmea_pattern) == [nmea_type_0, nmea_type_1, nmea_type_2, nmea_type_3, nmea_type_4, nmea_type_5]:
                                self.nmea_sync = 2
                                break
                        if self.nmea_sync != 2:
                            self.nmea_sync = 0
                elif self.nmea_sync == 2:
                    self.nmea_buffer.append(new_byte)
                    if self.nmea_buffer[-1] == 0x0A and self.nmea_buffer[-2] == 0x0D:
                        self.f_nmea.write(bytes(self.nmea_buffer))
                        self.nmea_sync = 0
        self.save_gnss_kml()
        self.save_ins_kml()
        self.close_files()

    def weeksecondstoutc(self,gpsweek,gpsseconds,leapseconds):
        import datetime, calendar
        datetimeformat = "%Y-%m-%d %H:%M:%S"
        epoch = datetime.datetime.strptime("1980-01-06 00:00:00",datetimeformat)
        elapsed = datetime.timedelta(days=(gpsweek*7),seconds=(gpsseconds+leapseconds))
        return datetime.datetime.strftime(epoch + elapsed,datetimeformat)

    def save_gnss_kml(self):
        color = ["ffffffff","ff0000ff","ffff00ff","50FF78F0","ff00ff00","ff00aaff"]
        kml_header = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"\
                + "<kml xmlns=\"http://www.opengis.net/kml/2.2\">\n"\
                + "<Document>\n"
        for i in range(6):
            kml_header += "<Style id=\"P" + str(i) + "\">\r\n"\
                + "<IconStyle>\r\n"\
                + "<color>" + color[i] + "</color>\n"\
                + "<scale>0.3</scale>\n"\
                + "<Icon><href>http://maps.google.com/mapfiles/kml/shapes/track.png</href></Icon>\n"\
                + "</IconStyle>\n"\
                + "</Style>\n"
        self.f_gnss_kml.write(kml_header)

        gnss_track = "<Placemark>\n"\
                + "<name>Rover Track</name>\n"\
                + "<Style>\n"\
                + "<LineStyle>\n"\
                + "<color>ffffffff</color>\n"\
                + "</LineStyle>\n"\
                + "</Style>\n"\
                + "<LineString>\n"\
                + "<coordinates>\n"

        for pos in self.gnssdata:
            if pos[2] == 0:
                continue

            gnss_track += format(pos[4], ".9f") + ',' + format(pos[3], ".9f") + ',' + format(pos[5], ".3f") + '\n'

        gnss_track += "</coordinates>\n"\
                + "</LineString>\n"\
                + "</Placemark>\n"

        gnss_track += "<Folder>\n"\
                + "<name>Rover Position</name>\n"

        for i, pos in enumerate(self.gnssdata):
            ep = self.weeksecondstoutc(pos[0], pos[1]/1000, -18)
            ep_sp = time.strptime(ep, "%Y-%m-%d %H:%M:%S")
            
            if pos[2] == 0:
                pass
            else:
                track_ground = math.atan2(pos[14], pos[13]) * (57.295779513082320)

                gnss_track += "<Placemark>\n"
                if i <= 1:
                    gnss_track += "<name>Start</name>\n"
                elif i == len(self.gnssdata)-1:
                    gnss_track += "<name>End</name>\n"
                else:
                    if math.fmod(ep_sp[5]+(pos[1]%1000)/1000+0.025, 30) < 0.05:
                        gnss_track += "<name>"\
                            + "%02d" % ep_sp[3] + "%02d" % ep_sp[4] + "%02d" % ep_sp[5]\
                            + "</name>\n"

                gnss_track += "<TimeStamp><when>"\
                        + time.strftime("%Y-%m-%dT%H:%M:%S.", ep_sp)\
                        + "%02dZ" % ((pos[1]%1000)/10)\
                        + "</when></TimeStamp>\n"

                gnss_track += "<description><![CDATA[\n"\
                    + "<TABLE border=\"1\" width=\"100%\" Align=\"center\">\n"\
                    + "<TR ALIGN=RIGHT>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Time:</TD><TD>"\
                    + str(pos[0]) + "</TD><TD>" + "%.3f" % (pos[1]/1000) + "</TD><TD>"\
                    + "%2d:%2d:%7.4f" % (ep_sp[3],ep_sp[4],ep_sp[5]+(pos[1]%1000)/1000) + "</TD><TD>"\
                    + "%4d/%2d/%2d" % (ep_sp[0], ep_sp[1], ep_sp[2]) + "</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Position:</TD><TD>"\
                    + "%.8f" % pos[3] + "</TD><TD>" + "%.8f" % pos[4] + "</TD><TD>" + "%.4f" % pos[5] + "</TD><TD>(DMS,m)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Vel(N,E,D):</TD><TD>"\
                    + "%.4f" % pos[13] + "</TD><TD>" + "%.4f" % pos[14] + "</TD><TD>" + "%.4f" % (-pos[15]) + "</TD><TD>(m/s)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Att(r,p,h):</TD><TD>"\
                    + "0" + "</TD><TD>" + "0" + "</TD><TD>" + "%.4f" % track_ground + "</TD><TD>(deg,approx)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Mode:</TD><TD>"\
                    + "0" + "</TD><TD>" + str(pos[2]) + "</TD><TR>\n"\
                    + "</TABLE>\n"\
                    + "]]></description>\n"
                
                gnss_track += "<styleUrl>#P" + str(pos[2]) + "</styleUrl>\n"\
                        + "<Style>\n"\
                        + "<IconStyle>\n"\
                        + "<heading>" + "%.4f" % track_ground + "</heading>\n"\
                        + "</IconStyle>\n"\
                        + "</Style>\n"

                gnss_track += "<Point>\n"\
                        + "<coordinates>" + "%.9f,%.9f,%.3f" % (pos[4], pos[3], pos[5]) + "</coordinates>\n"\
                        + "</Point>\n"

                gnss_track += "</Placemark>\n"

        gnss_track += "</Folder>\n"\
                + "</Document>\n"\
                + "</kml>\n"

        self.f_gnss_kml.write(gnss_track)
        

    def save_ins_kml(self):
        '''
        '''
        # white-cyan, red, purple, light-yellow, green, yellow
        color = ["ffffffff","ff0000ff","ffff00ff","50FF78F0","ff00ff00","ff00aaff"]
        kml_header = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"\
                + "<kml xmlns=\"http://www.opengis.net/kml/2.2\">\n"\
                + "<Document>\n"
        for i in range(6):
            kml_header += "<Style id=\"P" + str(i) + "\">\r\n"\
                + "<IconStyle>\r\n"\
                + "<color>" + color[i] + "</color>\n"\
                + "<scale>0.3</scale>\n"\
                + "<Icon><href>http://maps.google.com/mapfiles/kml/shapes/track.png</href></Icon>\n"\
                + "</IconStyle>\n"\
                + "</Style>\n"
        self.f_ins_kml.write(kml_header)

        ins_track = "<Placemark>\n"\
                + "<name>Rover Track</name>\n"\
                + "<Style>\n"\
                + "<LineStyle>\n"\
                + "<color>ff0000ff</color>\n"\
                + "</LineStyle>\n"\
                + "</Style>\n"\
                + "<LineString>\n"\
                + "<coordinates>\n"

        for ins in self.insdata:
            ep = self.weeksecondstoutc(ins[0], ins[1]/1000, -18)
            ep_sp = time.strptime(ep, "%Y-%m-%d %H:%M:%S")

            if math.fmod(ep_sp[5]+(ins[1]%1000)/1000+0.0005, self.inskml_rate) < 0.005:
                if abs(ins[5]*ins[4]) < 0.00000001:
                    continue
                
                ins_track += format(ins[5], ".9f") + ',' + format(ins[4], ".9f") + ',' + format(ins[6], ".3f") + '\n'

        ins_track += "</coordinates>\n"\
                + "</LineString>\n"\
                + "</Placemark>\n"
        
        ins_track += "<Folder>\n"\
                + "<name>Rover Position</name>\n"
        
        for i, ins in enumerate(self.insdata):
            ep = self.weeksecondstoutc(ins[0], ins[1]/1000, -18)
            ep_sp = time.strptime(ep, "%Y-%m-%d %H:%M:%S")

            if i == 0 or i == len(self.insdata)-1 or math.fmod(ins[1]/1000 + 0.0005, self.inskml_rate) < 0.005:
                ins_track += "<Placemark>\n"
                if i <= 1:
                    ins_track += "<name>Start</name>\n"
                elif i == len(self.insdata)-1:
                    ins_track += "<name>End</name>\n"
                else:
                    if math.fmod(ep_sp[5]+(ins[1]%1000)/1000+0.025, 30) < 0.05:
                        ins_track += "<name>"\
                            + "%02d" % ep_sp[3] + "%02d" % ep_sp[4] + "%02d" % ep_sp[5]\
                            + "</name>\n"

                ins_track += "<TimeStamp><when>"\
                        + time.strftime("%Y-%m-%dT%H:%M:%S.", ep_sp)\
                        + "%02dZ" % ((ins[1]%1000)/10)\
                        + "</when></TimeStamp>\n"

                ins_track += "<description><![CDATA[\n"\
                    + "<TABLE border=\"1\" width=\"100%\" Align=\"center\">\n"\
                    + "<TR ALIGN=RIGHT>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Time:</TD><TD>"\
                    + str(ins[0]) + "</TD><TD>" + "%.3f" % (ins[1]/1000) + "</TD><TD>"\
                    + "%2d:%2d:%7.4f" % (ep_sp[3],ep_sp[4],ep_sp[5]+(ins[1]%1000)/1000) + "</TD><TD>"\
                    + "%4d/%2d/%2d" % (ep_sp[0], ep_sp[1], ep_sp[2]) + "</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Position:</TD><TD>"\
                    + "%.8f" % ins[4] + "</TD><TD>" + "%.8f" % ins[5] + "</TD><TD>" + "%.4f" % ins[6] + "</TD><TD>(DMS,m)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Vel(N,E,D):</TD><TD>"\
                    + "%.4f" % ins[7] + "</TD><TD>" + "%.4f" % ins[8] + "</TD><TD>" + "%.4f" % (-ins[9]) + "</TD><TD>(m/s)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Att(r,p,h):</TD><TD>"\
                    + "%.4f" % ins[10] + "</TD><TD>" + "%.4f" % ins[11] + "</TD><TD>" + "%.4f" % ins[12] + "</TD><TD>(deg,approx)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Mode:</TD><TD>"\
                    + str(ins[2]) + "</TD><TD>" + str(ins[3]) + "</TD><TR>\n"\
                    + "</TABLE>\n"\
                    + "]]></description>\n"
                
                pcolor = 0
                if ins[3] == 0:     # "INS_INACTIVE"
                    pcolor = 0
                elif ins[3] == 1:   # "SPP/INS_SPP"
                    pcolor = 1
                elif ins[3] == 2:   # "PSRDIFF/INS_PSRDIFF (RTD)"
                    pcolor = 2
                elif ins[3] == 3:   # "INS_DR"
                    pcolor = 3
                elif ins[3] == 4:   # "RTK_FIX/INS_RTKFIXED"
                    pcolor = 4
                elif ins[3] == 5:   # "RTK_FLOAT/INS_RTKFLOAT"
                    pcolor = 5
                # pcolor = 4

                ins_track += "<styleUrl>#P" + str(pcolor) + "</styleUrl>\n"\
                        + "<Style>\n"\
                        + "<IconStyle>\n"\
                        + "<heading>" + "%.4f" % ins[12] + "</heading>\n"\
                        + "</IconStyle>\n"\
                        + "</Style>\n"

                ins_track += "<Point>\n"\
                        + "<coordinates>" + "%.9f,%.9f,%.3f" % (ins[5], ins[4], ins[6]) + "</coordinates>\n"\
                        + "</Point>\n"

                ins_track += "</Placemark>\n"

        ins_track += "</Folder>\n"\
                + "</Document>\n"\
                + "</kml>\n"
        
        self.f_ins_kml.write(ins_track)

    def close_files(self):
        for i, (k, v) in enumerate(self.log_files.items()):
            v.close()
        self.f_nmea.close()
        self.f_process.close()
        self.f_gnssposvel.close()
        self.f_imu.close()
        self.f_odo.close()
        self.f_ins.close()
        self.f_gnss_kml.close()
        self.f_ins_kml.close()
        self.log_files.clear()

    def log(self, output, data):
        if output['name'] not in self.log_files.keys():
            self.log_files[output['name']] = open(self.path + output['name'] + '.csv', 'w')
            self.write_titlebar(self.log_files[output['name']], output)
        buffer = ''
        for i in range(len(data)):
            if i == 1:
                buffer = buffer + format(data[i]/1000, output['payload'][i]['format'])
            else:
                buffer = buffer + format(data[i], output['payload'][i]['format'])
            if i < len(data)-1:
                buffer = buffer + ","
        buffer = buffer + "\n"
        self.log_files[output['name']].write(buffer)

        if output['name'] == 's1':
            buffer = '$GPIMU,'
            buffer = buffer + format(data[0], output['payload'][0]['format']) + ","
            buffer = buffer + format(data[1]/1000, output['payload'][1]['format']) + "," + "    ,"
            buffer = buffer + format(data[2], output['payload'][2]['format']) + ","
            buffer = buffer + format(data[3], output['payload'][3]['format']) + ","
            buffer = buffer + format(data[4], output['payload'][4]['format']) + ","
            buffer = buffer + format(data[5], output['payload'][5]['format']) + ","
            buffer = buffer + format(data[6], output['payload'][6]['format']) + ","
            buffer = buffer + format(data[7], output['payload'][7]['format']) + "\n"
            self.f_process.write(buffer)

            buffer = ''
            buffer = buffer + format(data[0], output['payload'][0]['format']) + ","
            buffer = buffer + format(data[1]/1000, output['payload'][1]['format']) + "," + "    ,"
            buffer = buffer + format(data[2], output['payload'][2]['format']) + ","
            buffer = buffer + format(data[3], output['payload'][3]['format']) + ","
            buffer = buffer + format(data[4], output['payload'][4]['format']) + ","
            buffer = buffer + format(data[5], output['payload'][5]['format']) + ","
            buffer = buffer + format(data[6], output['payload'][6]['format']) + ","
            buffer = buffer + format(data[7], output['payload'][7]['format']) + "\n"
            self.f_imu.write(buffer)

            # if self.last_time != 0:
            #     now_time = data[0] * 604800 * 1000 + data[1]
            #     if now_time - self.last_time > 10:
            #         print('{0} time err {1}'.format(now_time, now_time - self.last_time))
            #     self.last_time = now_time
            # else:
            #     self.last_time = data[0] * 604800 * 1000 + data[1]

        elif output['name'] == 'g1':
            buffer = '$GPGNSS,'
            buffer = buffer + format(data[0], output['payload'][0]['format']) + ","
            buffer = buffer + format(data[1]/1000, output['payload'][1]['format']) + ","
            buffer = buffer + format(data[3], output['payload'][3]['format']) + ","
            buffer = buffer + format(data[4], output['payload'][4]['format']) + ","
            buffer = buffer + format(data[5], output['payload'][5]['format']) + ","
            buffer = buffer + format(data[6], output['payload'][6]['format']) + ","
            buffer = buffer + format(data[7], output['payload'][7]['format']) + ","
            buffer = buffer + format(data[8], output['payload'][8]['format']) + ","
            buffer = buffer + format(data[2], output['payload'][2]['format']) + "\n"
            self.f_process.write(buffer)

            buffer = '$GPVEL,'
            buffer = buffer + format(data[0], output['payload'][0]['format']) + ","
            buffer = buffer + format(data[1]/1000, output['payload'][1]['format']) + ","
            horizontal_speed = math.sqrt(data[13] * data[13] + data[14] * data[14])
            track_over_ground = math.atan2(data[14], data[13]) * (57.295779513082320)
            buffer = buffer + format(horizontal_speed, output['payload'][13]['format']) + ","
            buffer = buffer + format(track_over_ground, output['payload'][14]['format']) + ","
            buffer = buffer + format(data[15], output['payload'][15]['format']) + "\n"
            self.f_process.write(buffer)

            buffer = ''
            buffer = buffer + format(data[0], output['payload'][0]['format']) + ","
            buffer = buffer + format(data[1]/1000, output['payload'][1]['format']) + ","
            buffer = buffer + format(data[3], output['payload'][3]['format']) + ","
            buffer = buffer + format(data[4], output['payload'][4]['format']) + ","
            buffer = buffer + format(data[5], output['payload'][5]['format']) + ","
            buffer = buffer + format(data[6], output['payload'][6]['format']) + ","
            buffer = buffer + format(data[7], output['payload'][7]['format']) + ","
            buffer = buffer + format(data[8], output['payload'][8]['format']) + ","
            buffer = buffer + format(data[2], output['payload'][2]['format']) + ","
            buffer = buffer + format(data[13],output['payload'][13]['format']) + ","
            buffer = buffer + format(data[14],output['payload'][14]['format']) + ","
            buffer = buffer + format(data[15],output['payload'][15]['format']) + ","
            track_over_ground = math.atan2(data[14], data[13]) * (57.295779513082320)
            buffer = buffer + format(track_over_ground, output['payload'][14]['format']) + "\n"
            self.f_gnssposvel.write(buffer)

            self.gnssdata.append(data)
        
        elif output['name'] == 'o1':
            buffer = '$GPODO,'
            buffer = buffer + format(data[0], output['payload'][0]['format']) + ","
            buffer = buffer + format(data[1]/1000, output['payload'][1]['format']) + ","
            buffer = buffer + format(data[2], output['payload'][2]['format']) + ","
            buffer = buffer + format(data[3], output['payload'][3]['format']) + ","
            buffer = buffer + format(data[4], output['payload'][4]['format']) + ","
            buffer = buffer + format(data[5], output['payload'][5]['format']) + "\n"
            self.f_process.write(buffer)

            buffer = ''
            buffer = buffer + format(data[0], output['payload'][0]['format']) + ","
            buffer = buffer + format(data[1]/1000, output['payload'][1]['format']) + ","
            buffer = buffer + format(data[2], output['payload'][2]['format']) + ","
            buffer = buffer + format(data[3], output['payload'][3]['format']) + ","
            buffer = buffer + format(data[4], output['payload'][4]['format']) + ","
            buffer = buffer + format(data[5], output['payload'][5]['format']) + "\n"
            self.f_odo.write(buffer)

        elif output['name'] == 'i1':
            if data[1] % 100 == 0:
                buffer = '$GPINS,'
                buffer = buffer + format(data[0], output['payload'][0]['format']) + ","
                buffer = buffer + format(data[1]/1000, output['payload'][1]['format']) + ","
                buffer = buffer + format(data[4], output['payload'][4]['format']) + ","
                buffer = buffer + format(data[5], output['payload'][5]['format']) + ","
                buffer = buffer + format(data[6], output['payload'][6]['format']) + ","
                buffer = buffer + format(data[7], output['payload'][7]['format']) + ","
                buffer = buffer + format(data[8], output['payload'][8]['format']) + ","
                buffer = buffer + format(data[9], output['payload'][9]['format']) + ","
                buffer = buffer + format(data[10], output['payload'][10]['format']) + ","
                buffer = buffer + format(data[11], output['payload'][11]['format']) + ","
                buffer = buffer + format(data[12], output['payload'][12]['format']) + ","
                buffer = buffer + format(data[3], output['payload'][3]['format']) + "\n"
                self.f_process.write(buffer)

                buffer = ''
                buffer = buffer + format(data[0], output['payload'][0]['format']) + ","
                buffer = buffer + format(data[1]/1000, output['payload'][1]['format']) + ","
                buffer = buffer + format(data[4], output['payload'][4]['format']) + ","
                buffer = buffer + format(data[5], output['payload'][5]['format']) + ","
                buffer = buffer + format(data[6], output['payload'][6]['format']) + ","
                buffer = buffer + format(data[7], output['payload'][7]['format']) + ","
                buffer = buffer + format(data[8], output['payload'][8]['format']) + ","
                buffer = buffer + format(data[9], output['payload'][9]['format']) + ","
                buffer = buffer + format(data[10], output['payload'][10]['format']) + ","
                buffer = buffer + format(data[11], output['payload'][11]['format']) + ","
                buffer = buffer + format(data[12], output['payload'][12]['format']) + ","
                buffer = buffer + format(data[3], output['payload'][3]['format']) + ","
                buffer = buffer + format(data[2], output['payload'][2]['format']) + "\n"         
                self.f_ins.write(buffer)

                if abs(data[5]*data[4]) > 0.00000001:
                    self.insdata.append(data)

    def parse_output_packet_payload(self, packet_type):
        payload_lenth = self.packet_buffer[2]
        payload = self.packet_buffer[3:payload_lenth+3]
        output = next((x for x in self.rtk_properties['userOutputPackets'] if x['name'] == packet_type), None)
        if output != None:
            self.openrtk_unpack_output_packet(output, payload, payload_lenth)
        else:
            print('no packet type {0} in json'.format(packet_type))

    def openrtk_unpack_output_packet(self, output, payload, payload_lenth):
        fmt = self.pkfmt[output['name']]
        len_fmt = fmt['len_b']
        pack_fmt = fmt['pack']
        if output['isList']:
            length = fmt['len']
            packet_num = payload_lenth // length
            for i in range(packet_num):
                payload_c = payload[i*length:(i+1)*length]
                try:
                    b = struct.pack(len_fmt, *payload_c)
                    data = struct.unpack(pack_fmt, b)
                    self.log(output, data)
                except Exception as e:
                    print("error happened when decode the payload {0}".format(e))
        else:
            try:
                b = struct.pack(len_fmt, *payload)
                data = struct.unpack(pack_fmt, b)
                self.log(output, data)
            except Exception as e:
                print("error happened when decode the payload {0}".format(e))    
    
    def write_titlebar(self, file, output):
        for value in output['payload']:
            file.write(value['name']+'('+value['unit']+')')
            file.write(",")
        file.write("\n")

    def calc_crc(self, payload):
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



def mkdir(file_path):
    path = file_path.strip()
    path = path.rstrip("\\")
    path = path[:-4]
    path = path + '_p'
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def receive_args():
    parser = argparse.ArgumentParser()
    parser.description = argparse.ArgumentParser(
        description='Aceinna OpenRTK python parse input args command:')
    parser.add_argument("-p", type=str, help="folder path", default='.')
    parser.add_argument("-i", type=int, help="ins kml rate(hz): 1 2 5 10", default=5)
    return parser.parse_args()

if __name__ == '__main__':
    # compatible code for windows python 3.8
    if is_windows and is_later_py_38:
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    args = receive_args()

    json_setting = 'openrtk_packets.json'
    
    if args.i != 1 and args.i != 2 and args.i != 5 and args.i != 10:
        print('waring: no ins kml rate {0}, just can be 1 2 5 10!'.format(args.i))
        sys.exit(0)

    for root, dirs, file_name in os.walk(args.p):
        for fname in file_name:
            if (fname.startswith('user') or fname.startswith('debug')) and fname.endswith('.bin') or (fname.startswith('IMU')) or (fname.endswith('.log')):
                file_path = os.path.join(root, fname)
                print('processing {0}'.format(file_path))
                path = mkdir(file_path)
                try:
                    with open(file_path, 'rb') as fp_rawdata:
                        if fname.startswith('user'):
                            parse = UserRawParse(fp_rawdata, path + '/' + fname[:-4] + '_', json_setting, args.i)
                        elif fname.endswith('.log'):
                            parse = ZouParse(fp_rawdata, path + '/' + fname.rstrip(".log") + '_')
                        parse.start_pasre()
                        fp_rawdata.close
                except Exception as e:
                    print(e)
