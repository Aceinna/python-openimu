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
import traceback
from ..framework.utils import resource
from ..framework.utils.print import (print_green, print_red)

is_later_py_3 = sys.version_info > (3, 0)


class INS401Parse:
    def __init__(self, data_file, path, inskml_rate, json_setting):
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
        self.f_gnssposvel = None
        self.f_ins = None
        self.f_odo = None
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
        self.f_ins = open(self.path[0:-1] + '-ins.txt', 'w')
        self.f_nmea = open(self.path[0:-1] + '-nmea', 'wb')
        self.f_gnss_kml = open(self.path[0:-1] + '-gnss.kml', 'w')
        self.f_ins_kml = open(self.path[0:-1] + '-ins.kml', 'w')
        self.f_odo = open(self.path[0:-1] + '-odo.txt', 'w')

        packet_type = ''
        nmea_header_len = 0
        for i, new_byte in enumerate(self.rawdata):
            self.sync_pattern.append(new_byte)
            if self.sync_state == 1:
                self.packet_buffer.append(new_byte)
                # packet len
                if len(self.packet_buffer) == self.packet_buffer[2] + 8:
                    packet_crc = 256 * \
                        self.packet_buffer[-2] + self.packet_buffer[-1]
                    # packet crc
                    if packet_crc == self.calc_crc(self.packet_buffer[:-2]):
                        self.parse_output_packet_payload(packet_type)
                        self.packet_buffer = []
                        self.sync_state = 0
                    else:
                        #print('user data crc err!')
                        self.sync_state = 0  # CRC did not match
            else:
                for packet_type in self.userPacketsTypeList:
                    packet_type_split = packet_type.split(',')
                    packet_type_0 = int(packet_type_split[0], 16)
                    packet_type_1 = int(packet_type_split[1], 16)
                    # packet type
                    if list(self.sync_pattern) == [0x55, 0x55, packet_type_0, packet_type_1]:
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

    def weeksecondstoutc(self, gpsweek, gpsseconds, leapseconds):
        import datetime
        import calendar
        datetimeformat = "%Y-%m-%d %H:%M:%S"
        epoch = datetime.datetime.strptime(
            "1980-01-06 00:00:00", datetimeformat)
        elapsed = datetime.timedelta(
            days=(gpsweek*7), seconds=(gpsseconds+leapseconds))
        return datetime.datetime.strftime(epoch + elapsed, datetimeformat)

    def save_gnss_kml(self):
        color = ["ffffffff", "ff0000ff", "ffff00ff",
                 "50FF78F0", "ff00ff00", "ff00aaff"]
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

        gnss_postype = ["NONE", "PSRSP", "PSRDIFF",
                        "UNDEFINED", "RTKFIXED", "RTKFLOAT"]

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

            gnss_track += format(pos[4], ".9f") + ',' + format(pos[3],
                                                               ".9f") + ',' + format(pos[5], ".3f") + '\n'

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
                track_ground = math.atan2(
                    pos[14], pos[13]) * (57.295779513082320)

                gnss_track += "<Placemark>\n"
                if i <= 1:
                    gnss_track += "<name>Start</name>\n"
                elif i == len(self.gnssdata)-1:
                    gnss_track += "<name>End</name>\n"
                else:
                    if math.fmod(ep_sp[5]+(pos[1] % 1000)/1000+0.025, 30) < 0.05:
                        gnss_track += "<name>"\
                            + "%02d" % ep_sp[3] + "%02d" % ep_sp[4] + "%02d" % ep_sp[5]\
                            + "</name>\n"

                gnss_track += "<TimeStamp><when>"\
                    + time.strftime("%Y-%m-%dT%H:%M:%S.", ep_sp)\
                    + "%02dZ" % ((pos[1] % 1000)/10)\
                    + "</when></TimeStamp>\n"

                gnss_track += "<description><![CDATA[\n"\
                    + "<TABLE border=\"1\" width=\"100%\" Align=\"center\">\n"\
                    + "<TR ALIGN=RIGHT>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Time:</TD><TD>"\
                    + str(pos[0]) + "</TD><TD>" + "%.3f" % (pos[1]/1000) + "</TD><TD>"\
                    + "%2d:%2d:%7.4f" % (ep_sp[3], ep_sp[4], ep_sp[5]+(pos[1] % 1000)/1000) + "</TD><TD>"\
                    + "%4d/%2d/%2d" % (ep_sp[0], ep_sp[1], ep_sp[2]) + "</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Position:</TD><TD>"\
                    + "%.8f" % pos[3] + "</TD><TD>" + "%.8f" % pos[4] + "</TD><TD>" + "%.4f" % pos[5] + "</TD><TD>(DMS,m)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Vel(N,E,D):</TD><TD>"\
                    + "%.4f" % pos[13] + "</TD><TD>" + "%.4f" % pos[14] + "</TD><TD>" + "%.4f" % (-pos[15]) + "</TD><TD>(m/s)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Att(r,p,h):</TD><TD>"\
                    + "0" + "</TD><TD>" + "0" + "</TD><TD>" + "%.4f" % track_ground + "</TD><TD>(deg,approx)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Mode:</TD><TD>"\
                    + "0" + "</TD><TD>" + gnss_postype[pos[2]] + "</TD><TR>\n"\
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
        color = ["ffffffff", "50FF78F0", "ffff00ff",
                 "ff0000ff", "ff00ff00", "ff00aaff"]
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

        ins_status = ["INS_INACTIVE", "INS_ALIGNING", "INS_HIGH_VARIANCE",
                      "INS_SOLUTION_GOOD", "INS_SOLUTION_FREE", "INS_ALIGNMENT_COMPLETE"]
        ins_postype = ["INS_NONE", "INS_PSRSP", "INS_PSRDIFF",
                       "INS_PROPOGATED", "INS_RTKFIXED", "INS_RTKFLOAT"]

        for ins in self.insdata:
            ep = self.weeksecondstoutc(ins[0], ins[1]/1000, -18)
            ep_sp = time.strptime(ep, "%Y-%m-%d %H:%M:%S")

            if math.fmod(ep_sp[5]+(ins[1] % 1000)/1000+0.0005, self.inskml_rate) < self.inskml_rate:
                if abs(ins[5]*ins[4]) < 0.00000001:
                    continue

                ins_track += format(ins[5], ".9f") + ',' + format(ins[4],
                                                                  ".9f") + ',' + format(ins[6], ".3f") + '\n'

        ins_track += "</coordinates>\n"\
            + "</LineString>\n"\
            + "</Placemark>\n"

        ins_track += "<Folder>\n"\
            + "<name>Rover Position</name>\n"

        for i, ins in enumerate(self.insdata):
            ep = self.weeksecondstoutc(ins[0], ins[1]/1000, -18)
            ep_sp = time.strptime(ep, "%Y-%m-%d %H:%M:%S")

            if i == 0 or i == len(self.insdata)-1 or math.fmod(ins[1]/1000 + 0.0005, self.inskml_rate) < self.inskml_rate:
                ins_track += "<Placemark>\n"
                if i <= 1:
                    ins_track += "<name>Start</name>\n"
                elif i == len(self.insdata)-1:
                    ins_track += "<name>End</name>\n"
                else:
                    if math.fmod(ep_sp[5]+(ins[1] % 1000)/1000+0.025, 30) < 0.05:
                        ins_track += "<name>"\
                            + "%02d" % ep_sp[3] + "%02d" % ep_sp[4] + "%02d" % ep_sp[5]\
                            + "</name>\n"

                ins_track += "<TimeStamp><when>"\
                    + time.strftime("%Y-%m-%dT%H:%M:%S.", ep_sp)\
                    + "%02dZ" % ((ins[1] % 1000)/10)\
                    + "</when></TimeStamp>\n"

                ins_track += "<description><![CDATA[\n"\
                    + "<TABLE border=\"1\" width=\"100%\" Align=\"center\">\n"\
                    + "<TR ALIGN=RIGHT>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Time:</TD><TD>"\
                    + str(ins[0]) + "</TD><TD>" + "%.3f" % (ins[1]/1000) + "</TD><TD>"\
                    + "%2d:%2d:%7.4f" % (ep_sp[3], ep_sp[4], ep_sp[5]+(ins[1] % 1000)/1000) + "</TD><TD>"\
                    + "%4d/%2d/%2d" % (ep_sp[0], ep_sp[1], ep_sp[2]) + "</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Position:</TD><TD>"\
                    + "%.8f" % ins[4] + "</TD><TD>" + "%.8f" % ins[5] + "</TD><TD>" + "%.4f" % ins[6] + "</TD><TD>(DMS,m)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Vel(N,E,D):</TD><TD>"\
                    + "%.4f" % ins[7] + "</TD><TD>" + "%.4f" % ins[8] + "</TD><TD>" + "%.4f" % (-ins[9]) + "</TD><TD>(m/s)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Att(r,p,h):</TD><TD>"\
                    + "%.4f" % ins[12] + "</TD><TD>" + "%.4f" % ins[13] + "</TD><TD>" + "%.4f" % ins[14] + "</TD><TD>(deg,approx)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Mode:</TD><TD>"\
                    + ins_status[ins[2]] + "</TD><TD>" + ins_postype[ins[3]] + "</TD><TR>\n"\
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
                    + "<heading>" + "%.4f" % ins[14] + "</heading>\n"\
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
        self.f_ins.close()
        self.f_gnss_kml.close()
        self.f_ins_kml.close()
        self.log_files.clear()
        self.f_odo.close()

    def log(self, output, data):
        if output['name'] not in self.log_files.keys():
            self.log_files[output['name']] = open(
                self.path + output['display'] + '.csv', 'w')
            self.write_titlebar(self.log_files[output['name']], output)
        buffer = ''
        for i in range(len(data)):
            if i == 1:
                buffer = buffer + \
                    format(data[i]/1000, output['payload'][i]['format'])
            else:
                buffer = buffer + \
                    format(data[i], output['payload'][i]['format'])
            if i < len(data)-1:
                buffer = buffer + ","
        buffer = buffer + "\n"
        self.log_files[output['name']].write(buffer)

        # imu
        if output['name'] == '01,0a':
            buffer = '$GPIMU,'
            buffer = buffer + \
                format(data[0], output['payload'][0]['format']) + ","
            buffer = buffer + \
                format(data[1]/1000, output['payload']
                       [1]['format']) + "," + "    ,"
            buffer = buffer + \
                format(data[2], output['payload'][2]['format']) + ","
            buffer = buffer + \
                format(data[3], output['payload'][3]['format']) + ","
            buffer = buffer + \
                format(data[4], output['payload'][4]['format']) + ","
            buffer = buffer + \
                format(data[5], output['payload'][5]['format']) + ","
            buffer = buffer + \
                format(data[6], output['payload'][6]['format']) + ","
            buffer = buffer + \
                format(data[7], output['payload'][7]['format']) + "\n"
            self.f_process.write(buffer)

            buffer = ''
            buffer = buffer + \
                format(data[0], output['payload'][0]['format']) + ","
            buffer = buffer + \
                format(data[1]/1000, output['payload']
                       [1]['format']) + "," + "    ,"
            buffer = buffer + \
                format(data[2], output['payload'][2]['format']) + ","
            buffer = buffer + \
                format(data[3], output['payload'][3]['format']) + ","
            buffer = buffer + \
                format(data[4], output['payload'][4]['format']) + ","
            buffer = buffer + \
                format(data[5], output['payload'][5]['format']) + ","
            buffer = buffer + \
                format(data[6], output['payload'][6]['format']) + ","
            buffer = buffer + \
                format(data[7], output['payload'][7]['format']) + "\n"
            self.f_imu.write(buffer)

        # odometer
        elif output['name'] == '04,0a':
            buffer = '$GPODO,'
            buffer = buffer + \
                format(data[0], output['payload'][0]['format']) + ","
            buffer = buffer + \
                format(data[1]/1000, output['payload'][1]['format']) + ","
            buffer = buffer + \
                format(data[2], output['payload'][2]['format']) + ","
            buffer = buffer + \
                format(data[3], output['payload'][3]['format']) + ","
            buffer = buffer + \
                format(data[4], output['payload'][4]['format']) + ","
            buffer = buffer + \
                format(data[5], output['payload'][5]['format']) + "\n"
            self.f_process.write(buffer)

            buffer = ''
            buffer = buffer + \
                format(data[0], output['payload'][0]['format']) + ","
            buffer = buffer + \
                format(data[1]/1000, output['payload'][1]['format']) + ","
            buffer = buffer + \
                format(data[2], output['payload'][2]['format']) + ","
            buffer = buffer + \
                format(data[3], output['payload'][3]['format']) + ","
            buffer = buffer + \
                format(data[4], output['payload'][4]['format']) + ","
            buffer = buffer + \
                format(data[5], output['payload'][5]['format']) + "\n"
            self.f_odo.write(buffer)

        # gnss
        elif output['name'] == '02,0a':
            buffer = '$GPGNSS,'
            buffer = buffer + \
                format(data[0], output['payload'][0]['format']) + ","
            buffer = buffer + \
                format(data[1]/1000, output['payload'][1]['format']) + ","
            buffer = buffer + \
                format(data[3], output['payload'][3]['format']) + ","
            buffer = buffer + \
                format(data[4], output['payload'][4]['format']) + ","
            buffer = buffer + \
                format(data[5], output['payload'][5]['format']) + ","
            buffer = buffer + \
                format(data[6], output['payload'][6]['format']) + ","
            buffer = buffer + \
                format(data[7], output['payload'][7]['format']) + ","
            buffer = buffer + \
                format(data[8], output['payload'][8]['format']) + ","
            buffer = buffer + \
                format(data[2], output['payload'][2]['format']) + "\n"
            self.f_process.write(buffer)

            buffer = '$GPVEL,'
            buffer = buffer + \
                format(data[0], output['payload'][0]['format']) + ","
            buffer = buffer + \
                format(data[1]/1000, output['payload'][1]['format']) + ","
            horizontal_speed = math.sqrt(
                data[13] * data[13] + data[14] * data[14])
            track_over_ground = math.atan2(
                data[14], data[13]) * (57.295779513082320)
            buffer = buffer + format(horizontal_speed,
                                     output['payload'][13]['format']) + ","
            buffer = buffer + format(track_over_ground,
                                     output['payload'][14]['format']) + ","
            buffer = buffer + \
                format(data[15], output['payload'][15]['format']) + "\n"
            self.f_process.write(buffer)

            buffer = ''
            buffer = buffer + \
                format(data[0], output['payload'][0]['format']) + ","
            buffer = buffer + \
                format(data[1]/1000, output['payload'][1]['format']) + ","
            buffer = buffer + \
                format(data[3], output['payload'][3]['format']) + ","
            buffer = buffer + \
                format(data[4], output['payload'][4]['format']) + ","
            buffer = buffer + \
                format(data[5], output['payload'][5]['format']) + ","
            buffer = buffer + \
                format(data[6], output['payload'][6]['format']) + ","
            buffer = buffer + \
                format(data[7], output['payload'][7]['format']) + ","
            buffer = buffer + \
                format(data[8], output['payload'][8]['format']) + ","
            buffer = buffer + \
                format(data[2], output['payload'][2]['format']) + ","
            buffer = buffer + \
                format(data[13], output['payload'][13]['format']) + ","
            buffer = buffer + \
                format(data[14], output['payload'][14]['format']) + ","
            buffer = buffer + \
                format(data[15], output['payload'][15]['format']) + ","
            track_over_ground = math.atan2(
                data[14], data[13]) * (57.295779513082320)
            buffer = buffer + format(track_over_ground,
                                     output['payload'][14]['format']) + "\n"
            self.f_gnssposvel.write(buffer)

            self.gnssdata.append(data)

        # ins
        elif output['name'] == '03,0a':
            if (data[1]%100) < 10:
                buffer = '$GPINS,'
                buffer = buffer + \
                    format(data[0], output['payload'][0]['format']) + ","
                buffer = buffer + \
                    format(data[1]/1000, output['payload'][1]['format']) + ","
                buffer = buffer + \
                    format(data[4], output['payload'][4]['format']) + ","
                buffer = buffer + \
                    format(data[5], output['payload'][5]['format']) + ","
                buffer = buffer + \
                    format(data[6], output['payload'][6]['format']) + ","
                buffer = buffer + \
                    format(data[7], output['payload'][7]['format']) + ","
                buffer = buffer + \
                    format(data[8], output['payload'][8]['format']) + ","
                buffer = buffer + \
                    format(data[9], output['payload'][9]['format']) + ","
                buffer = buffer + \
                    format(data[12], output['payload'][12]['format']) + ","
                buffer = buffer + \
                    format(data[13], output['payload'][13]['format']) + ","
                buffer = buffer + \
                    format(data[14], output['payload'][14]['format']) + ","
                buffer = buffer + \
                    format(data[3], output['payload'][3]['format']) + "\n"
                self.f_process.write(buffer)

                buffer = ''
                buffer = buffer + \
                    format(data[0], output['payload'][0]['format']) + ","
                buffer = buffer + \
                    format(data[1]/1000, output['payload'][1]['format']) + ","
                buffer = buffer + \
                    format(data[4], output['payload'][4]['format']) + ","
                buffer = buffer + \
                    format(data[5], output['payload'][5]['format']) + ","
                buffer = buffer + \
                    format(data[6], output['payload'][6]['format']) + ","
                buffer = buffer + \
                    format(data[7], output['payload'][7]['format']) + ","
                buffer = buffer + \
                    format(data[8], output['payload'][8]['format']) + ","
                buffer = buffer + \
                    format(data[9], output['payload'][9]['format']) + ","
                buffer = buffer + \
                    format(data[12], output['payload'][12]['format']) + ","
                buffer = buffer + \
                    format(data[13], output['payload'][13]['format']) + ","
                buffer = buffer + \
                    format(data[14], output['payload'][14]['format']) + ","
                buffer = buffer + \
                    format(data[3], output['payload'][3]['format']) + ","
                buffer = buffer + \
                    format(data[2], output['payload'][2]['format']) + "\n"
                self.f_ins.write(buffer)

                if abs(data[5]*data[4]) > 0.00000001:
                    self.insdata.append(data)

        # diagnose
        # elif output['name'] == '05,0a':
        #     buffer = buffer + \
        #         format(data[0], output['payload'][0]['format']) + ","
        #     buffer = buffer + \
        #         format(data[1], output['payload'][1]['format']) + ","
        #     buffer = buffer + \
        #         format(data[2], output['payload'][2]['format']) + ","
        #     buffer = buffer + \
        #         format(data[3], output['payload'][3]['format']) + ","
        #     buffer = buffer + \
        #         format(data[4], output['payload'][4]['format']) + "\n"

        #self.log_files[output['name']].write(buffer)

    def parse_output_packet_payload(self, packet_type):
        payload_lenth = struct.unpack('<I', bytes(self.packet_buffer[2:6]))[0]
        payload = self.packet_buffer[6:payload_lenth+6]
        output = next(
            (x for x in self.rtk_properties['userOutputPackets'] if x['name'] == packet_type), None)
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
                    print("error happened when decode the {0} {1}".format(
                        output['display'], e))
                    traceback.print_exc()
        else:
            try:
                b = struct.pack(len_fmt, *payload)
                data = struct.unpack(pack_fmt, b)
                self.log(output, data)
            except Exception as e:
                print("error happened when decode the {0} {1}".format(
                    output['display'], e))
                traceback.print_exc()

    def write_titlebar(self, file, output):
        for value in output['payload']:
            file.write(value['name']+'('+value['unit']+')')
            file.write(",")
        file.write("\n")

    def calc_crc(self, payload):
        crc = 0x1D0F
        for bytedata in payload:
            crc = crc ^ (bytedata << 8)
            for i in range(0, 8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
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


def prepare_setting_folder(setting_file):
    '''
    Prepare folders for data storage and configuration
    '''
    executor_path = resource.get_executor_path()
    setting_folder_name = 'setting'

    # copy contents of setting file under executor path
    setting_folder_path = os.path.join(
        executor_path, setting_folder_name)

    product = 'INS401'
    product_folder = os.path.join(setting_folder_path, product)
    if not os.path.isdir(product_folder):
        os.makedirs(product_folder)

    config_path = os.path.join(
        product_folder, setting_file)

    if not os.path.isfile(config_path):
        config_content = resource.get_content_from_bundle(
            setting_folder_name, os.path.join(product, setting_file))
        if config_content is None:
            raise ValueError('Setting file content is empty')

        with open(config_path, "wb") as code:
            code.write(config_content)

    return config_path


def do_parse(folder_path, kml_rate, setting_file):
    setting_path = prepare_setting_folder(setting_file)
    for root, _, file_name in os.walk(folder_path):
        for fname in file_name:
            if fname.startswith('user') and fname.endswith('.bin'):
                file_path = os.path.join(root, fname)
                print_green(
                    'Parse is started. File path: {0}'.format(file_path))
                path = mkdir(file_path)
                try:
                    with open(file_path, 'rb') as fp_rawdata:
                        parse = INS401Parse(
                            fp_rawdata, path + '/' + fname[:-4] + '_', kml_rate, setting_path)

                        parse.start_pasre()
                        print_green('Parse done.')
                except Exception as e:
                    print_red(e)
                    traceback.print_exc()
