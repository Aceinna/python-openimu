import os
import sys
import argparse
import json
import struct
import math
import collections
import datetime
import time

PI = 3.1415926535897932
WGS84 = {
    'a': 6378137.0,
    'b': 6356752.3142,
    'f': 0.0033528106643315515,
    'e': 0.081819190837555025,
    'e2': 0.0066943799893122479,
    'wie': 7.2922115147e-5,
    'GM': 398600441800000.00
}

ACEINNA_GYRO = (0.005/64)
ACEINNA_ACC = (0.005*9.80665/4000)
P2_33 = 1.164153218269348E-10
P2_33_DEG = 6.670106611340576E-09
P2_27_F = 2.270936965942383E-09
P2_29_F = 5.677342414855957E-10
P2_29 = 1.862645149230957E-09
FSAS_GYRO = 1.085069444444445E-07
FSAS_ACC = 1.525878906250000E-06
ISA100C_GYRO = 5.729577951308233E-08
ISA100C_ACC = 2.0E-8

RATES_SIZE = 26

rates = [
	[0,100,2.0,100],
	[1,100,100,100],
	[3,200,ACEINNA_GYRO,ACEINNA_ACC],
	[4,100,100,100],
	[5,100,100,100],
	[8,200,100,100],
	[11,100,P2_33,P2_27_F],
	[12,100,100,100],
	[13,200,FSAS_GYRO,FSAS_ACC],
	[16,200,100,100],
	[19,200,100,100],
	[20,100,100,100],
	[26,200,ISA100C_GYRO,ISA100C_ACC],
	[27,100,100,100],
	[28,100,100,100],
	[31,200,100,100],
	[32,125,100,100],
	[33,200,100,100],
	[34,200,100,100],
	[38,400,100,100],
	[39,400,100,100],
	[41,125,100,100],
	[45,200,100,100],
	[52,200,100,100],
	[56,125,100,100],
	[58,100,P2_33_DEG,P2_29],
]

class INS2000Parser:
    gga_nmea_file = 'ins-gga.nmea'
    gnssposvel_txt_file = 'gnssposvel.txt'
    gnss_txt_file = 'gnss.txt'
    gnssvel_txt_file = 'gnssvel.txt'
    imu_txt_file = 'imu.txt'
    ins_txt_file = 'ins.txt'
    heading_txt_file = 'heading.txt'
    process_txt_file = 'process.txt'
    gnss_kml_file = 'gnss.kml'
    ins_kml_file = 'ins.kml'

    """Parse INS2000 data"""
    def __init__(self, bin_file, cfg_file):
        self.bin_file = bin_file
        self.cfg_file = cfg_file
        self.out_prefix = ''
        self.cfgs = None
        self.data = []
        self.buf = []
        self.header_len = 0
        self.data_len = 0
        self.message_id = 0
        self.message_type = 0
        self.ids = []
        self.idx = 0
        self.sync_pattern = collections.deque(3*[0], 3)
        self.sync_state = 0
        self.lastlctime = 0

        self.gnss_kmls = []
        self.gnss_vels = []
        self.inspvaxs = []

        self.files = {}
        self.packets = 0


    def run(self):
        """start parse data"""
        _, tmpfilename = os.path.split(self.bin_file)
        shortname, _ = os.path.splitext(tmpfilename)

        self.out_prefix = os.path.join(os.path.dirname(self.bin_file), shortname + '-')

        self.init_files()

        with open(self.cfg_file, 'r') as cfg_data:
            self.cfgs = json.load(cfg_data)

        with open(self.bin_file, 'rb') as buf_r:
            while True:
                tmp_data = buf_r.read(256)
                if tmp_data:
                    self.parse_data(tmp_data)
                else:
                    break

        self.save_gnss_kml()
        self.save_ins_kml()

        self.close_files()

    def init_files(self):
        """init all files"""

        files = [self.gga_nmea_file, self.gnssposvel_txt_file, self.gnssposvel_txt_file,
            self.gnss_txt_file, self.gnssvel_txt_file, self.imu_txt_file, self.ins_txt_file,
            self.heading_txt_file, self.process_txt_file, self.gnss_kml_file, self.ins_kml_file]
        for filename in files:
            fo = open(self.out_prefix + filename, 'w')
            self.files[filename] = fo

    def close_files(self):
        """close all files"""
        for _, fo in self.files.items():
            fo.close()

    def append_process_txt(self, data):
        """append process txt"""
        self.write_file(self.process_txt_file, data)

    def parse_data(self, data):
        """parse data"""
        for _, new_byte in enumerate(data):
            self.idx += 1
            self.sync_pattern.append(new_byte)
            if self.sync_state == 1:
                self.buf.append(new_byte)
                packet_len = len(self.buf)
                if packet_len == 6:
                    # b_buf = b''.join(map(lambda x:int.to_bytes(x, 1, 'little'), self.buf))
                    b_buf = bytearray(self.buf)
                    self.message_id, = struct.unpack('<H', b_buf[4:6])
                    if self.message_id == 1462:
                        self.header_len = 12
                    else:
                        self.header_len = self.buf[3]

                if self.header_len == packet_len:
                    if self.message_id == 1462:
                        self.message_type = 0
                        self.data_len = self.buf[3]
                    else:
                        self.message_type = self.buf[6]
                        # b_buf = b''.join(map(lambda x:int.to_bytes(x, 1, 'little'), self.buf))
                        b_buf = bytearray(self.buf)
                        self.data_len,  = struct.unpack('<H', b_buf[8:10])

                if self.data_len > 0 and packet_len == self.data_len + self.header_len + 4:
                    # self.data = b''.join(map(lambda x:int.to_bytes(x, 1, 'little'), self.buf))
                    self.data = bytearray(self.buf)
                    self.packets += 1
                    if self.check_crc(self.data):
                        self.decode_packet(self.data)
                    self.buf = []
                    self.sync_state = 0

            else:
                if list(self.sync_pattern) == [0xAA, 0x44, 0x12] or list(self.sync_pattern) == [0xAA, 0x44, 0x13]:
                    self.buf = [self.sync_pattern[0], self.sync_pattern[1], self.sync_pattern[2]]
                    self.sync_state = 1
                    continue



    def check_crc(self, packet):
        """check packet crc"""
        crc = self.crc(packet[:-4])
        check_crc, = struct.unpack('<L', packet[-4:])
        return crc == check_crc

    def decode_packet(self, packet):
        """decode packet"""
        message_id, = struct.unpack('<H', packet[4:6])
        message_id_str = str(message_id)
        if not message_id_str in self.cfgs["packetsTypeList"]:
            return

        message_str = self.cfgs["packetsTypeList"][message_id_str]
        if not message_str in self.cfgs["outputPackets"]:
            return

        payload = self.cfgs["outputPackets"][message_str]["payload"]
        bin_format, keys = self.output_fmt(payload)

        try:
            packets = struct.unpack(bin_format, packet[self.header_len:-4])
        except Exception as e:
            return

        dict_pack = dict(zip(keys, packets))
        dict_pack['header_message_id'] = message_id
        if message_id == 1462:
            dict_pack['header_gps_week'], = struct.unpack('<H', packet[6:8])
            dict_pack['header_gps_seconds'], = struct.unpack('i', packet[8:12])
        else:
            dict_pack['header_gps_week'], = struct.unpack('<H', packet[14:16])
            dict_pack['header_gps_seconds'], = struct.unpack('i', packet[16:20])


        if message_id == 971:
            self.trace_heading(dict_pack)
        if message_id == 1465:
            self.trace_gga_nmea(dict_pack)
        if message_id == 1429:
            self.trace_gnss_kml(dict_pack)
        if message_id == 1430:
            self.trace_gnss_vel(dict_pack)
        if message_id == 1462:
            self.trace_rawimusx(dict_pack)


    def crc(self, data):
        """crc"""
        crc_rst = 0
        temp1 = 0
        temp2 = 0
        for byte_data in data:
            temp1 = (crc_rst >> 8)  & 0x00FFFFFF
            temp2 = self.crc_value((crc_rst ^ byte_data) & 0xFF)
            crc_rst = temp1 ^ temp2

        return crc_rst

    def crc_value(self, value):
        """Calculate a CRC value to be used by CRC calculation functions"""
        j = 8
        crc = value
        while j > 0:
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
            j -= 1

        return crc

    def output_fmt(self, payload):
        """generate struct format"""
        packet_fmt = '<'
        keys = []
        for item in payload:
            if item["type"] == "int8":
                packet_fmt += 'b'
            if item["type"] == "uint8":
                packet_fmt += 'B'
            if item["type"] == "bool":
                packet_fmt += '?'
            if item["type"] == "int16":
                packet_fmt += 'h'
            if item["type"] == "uint16":
                packet_fmt += 'H'
            if item["type"] == "int32":
                packet_fmt += 'i'
            if item["type"] == "uint32":
                packet_fmt += 'I'
            if item["type"] == "int64":
                packet_fmt += 'q'
            if item["type"] == "uint64":
                packet_fmt += 'Q'
            if item["type"] == "float":
                packet_fmt += 'f'
            if item["type"] == "double":
                packet_fmt += 'd'
            if item["type"] == "string":
                packet_fmt += item["length"] + 's'

            keys.append(item["name"])

        return packet_fmt, keys

    def trace_heading(self, msg):
        """trace heading"""
        heading_txt = "%4d,%10.4f,%10.5f,%14.5f,%14.5f,%14.5f,%14.5f,%8d,%8d\n" % (msg['header_gps_week'],
            msg['header_gps_seconds'] / 1000, msg['length'], msg['heading'], msg['pitch'],
            msg['hdgstddev'], msg['ptchstddev'], msg['sol_stat'], msg['pos_type'])
        self.write_file(self.heading_txt_file, heading_txt)
        self.append_process_txt('$GPHEAD2,%s' % heading_txt)

    def trace_gga_nmea(self, msg):
        """trace gga nmea"""
        self.print_ins_txt(msg)
        if math.fabs(msg['lat']) > 0.001:
            self.inspvaxs.append(msg)

        if not (math.fabs(msg['lat']) > 0.001 and (msg['ins_status'] == 3 or msg['ins_status'] == 6 or
            msg['ins_status'] == 7)):
            return

        leverarm_v = [0.0, 0.0, 0.0]
        eular = [msg['roll'] * PI / 180, msg['pitch'] * PI / 180, msg['azimuth'] * PI / 180]
        c_vn = self.euler2dcm(eular)
        leverarm_n = [0]*3
        self.matrix_mutiply(c_vn, leverarm_v, 3, 3, 1, leverarm_n)
        d_leverarm = [0]*3
        pos = [msg['lat']*PI / 180, msg['lon']*PI / 180, msg['hgt'] + msg['undulation']]
        m, n = self.update_m_n(pos)
        d_leverarm[0] = leverarm_n[0] / (m + pos[2])
        d_leverarm[1] = leverarm_n[1] / ((n + pos[2])*math.cos(pos[0]))
        d_leverarm[2] = -leverarm_n[2]
        self.matrix_add(pos, d_leverarm, 3, 1, pos)
        position_type = self.getpostype(msg['pos_type'])
        gga = self.output_gga_nmea(msg['header_gps_seconds'] / 1000, position_type, pos, 10, 1.0, 1.0)
        self.write_file(self.gga_nmea_file, gga)

    def print_ins_txt(self, msg):
        """print ins txt"""
        ins_txt = "%4d,%10.4f,%14.9f,%14.9f,%10.4f,%10.4f,%10.4f,%10.4f,%14.9f,%14.9f,%14.9f,%d,%d\n" % (msg['header_gps_week'], msg['header_gps_seconds'] / 1000,
		    msg['lat'], msg['lon'], msg['hgt'] + msg['undulation'], msg['north_velocity'], msg['east_velocity'], msg['up_velocity'], msg['roll'], msg['pitch'],
            msg['azimuth'], msg['ins_status'], msg['pos_type'])
        self.write_file(self.ins_txt_file, ins_txt)
        self.append_process_txt('$GPINS,%s' % ins_txt)

    def trace_gnss_kml(self, msg):
        """trace gnss kml"""
        self.print_gnss_txt(msg)

        if math.fabs(msg['lat']) > 0.001:
            self.gnss_kmls.append(msg)

    def print_gnss_txt(self, msg):
        """print gnss txt"""
        pos_type = self.getpostype(msg['pos_type'])
        if msg['sol_status'] != 0:
            pos_type = 0

        if math.fmod(msg['header_gps_seconds'] / 1000 + 0.001, 1) < 0.01:
            if pos_type >= 0:
                gnss_txt = '%4d,%10.4f,%14.9f,%14.9f,%10.4f,%10.4f,%10.4f,%10.4f,%d\n' % (msg['header_gps_week'], msg['header_gps_seconds'] / 1000,
				    msg['lat'], msg['lon'], msg['hgt'] + msg['undulation'], msg['lat_sigma'], msg['lon_sigma'], msg['hgt_sigma'], pos_type)
                self.write_file(self.gnss_txt_file, gnss_txt)
                self.append_process_txt('$GPGNSS,%s' % gnss_txt)

    def trace_gnss_vel(self, msg):
        """trace gnss vel"""
        self.print_gnsssvel_txt(msg)

        if math.fabs(msg['hor_spd']) > 0.0001 or math.fabs(msg['vert_spd']) > 0.0001 or math.fabs(msg['trk_gnd']) > 0.0001:
            self.gnss_vels.append(msg)

    def trace_rawimusx(self, msg):
        """trace rawimusx"""
        lctime = msg['header_gps_seconds'] / 1000
        fxyz_scale, wxyz_scale, sample_rate = [0.0, 0.0, 0.0]
        x_accel, y_accel, z_accel, x_gyro, y_gyro, z_gyro =  [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        for i in range(RATES_SIZE):
            if rates[i][0] == msg['imutype']:
                sample_rate = rates[i][1]
                wxyz_scale = rates[i][2]
                fxyz_scale = rates[i][3]
                break

        x_accel = msg['x_accel'] * fxyz_scale * sample_rate
        y_accel = -msg['y_accel'] *fxyz_scale * sample_rate
        z_accel = msg['z_accel'] * fxyz_scale * sample_rate
        x_gyro = msg['x_gyro'] * wxyz_scale * sample_rate
        y_gyro = -msg['y_gyro'] * wxyz_scale * sample_rate
        z_gyro = msg['z_gyro'] * wxyz_scale * sample_rate

        if math.fmod(lctime + 0.02, 1) < 0.01 and lctime - self.lastlctime > 0.98:
            msg['header_gps_seconds'] = math.floor(lctime + 0.02)
            self.lastlctime = lctime
        else:
            lctime = 0

        imu_txt = "%4d,%10.4f,%10.4f,%14.10f,%14.10f,%14.10f,%14.10f,%14.10f,%14.10f \n" % (msg['week'], msg['seconds'],
            math.floor(lctime + 0.02), x_accel, y_accel, z_accel, x_gyro, y_gyro, z_gyro)
        self.write_file(self.imu_txt_file, imu_txt)
        self.append_process_txt("$GPIMU,%s" % imu_txt)

    def print_gnsssvel_txt(self, msg):
        """print gnssvel txt"""
        if math.fmod(msg['header_gps_seconds'] / 1000 + 0.001, 1) < 0.01:
            gnssvel_txt = "%4d,%10.4f,%14.9f,%14.9f,%10.4f,%10.4f,%8d,%8d\n" % (msg['header_gps_week'], msg['header_gps_seconds'] / 1000,
			    msg['hor_spd'], msg['trk_gnd'], msg['vert_spd'], msg['latency'], msg['sol_status'], msg['vel_type'])
            self.write_file(self.gnssvel_txt_file, gnssvel_txt)
            self.append_process_txt('$GPVEL,%s' % gnssvel_txt)

    def print_gnssposvel_txt(self, pos, vel):
        """print gnssposvel txt"""
        if math.fabs(pos['lat']) > 0.001:
            pos_type = self.getpostype(pos['pos_type'])
            north_velocity = vel['hor_spd'] * math.cos(vel['trk_gnd'] * PI / 180)
            east_velocity = vel['hor_spd'] * math.sin(vel['trk_gnd'] * PI / 180)
            up_velocity = vel['vert_spd']
            gnssposvel_txt = "%4d,%10.4f,%14.9f,%14.9f,%10.4f,%10.4f,%10.4f,%10.4f,%d,%10.4f,%10.4f,%10.4f,%10.4f\n" % (pos['header_gps_week'], pos['header_gps_seconds'] / 1000,
			    pos['lat'], pos['lon'], pos['hgt'] + pos['undulation'], pos['lat_sigma'], pos['lon_sigma'], pos['hgt_sigma'], pos_type, north_velocity, east_velocity, up_velocity, vel['trk_gnd'])
            self.write_file(self.gnssposvel_txt_file, gnssposvel_txt)

    def save_gnss_kml(self):
        """save gnss kml"""
        gnss_kml = ''
        gnss_kml += '<?xml version="1.0" encoding="UTF-8"?>\n'
        gnss_kml += '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
        gnss_kml += '<Document>\n'

        colors = ["ffffffff","ff0000ff","ffff00ff","50FF78F0","ff00ff00","ff00aaff"]

        for i in range(6):
            gnss_kml += '<Style id="P{:d}">\n'.format(i)
            gnss_kml += '<IconStyle>\n'
            gnss_kml += '<color>{:s}</color>\n'.format(colors[i])
            gnss_kml += '<scale>0.3</scale>\n'
            gnss_kml += '<Icon><href>http://maps.google.com/mapfiles/kml/shapes/track.png</href></Icon>'
            gnss_kml += '</IconStyle>\n'
            gnss_kml += '</Style>\n'

        gnss_kml += "<Placemark>\n"\
            + "<name>Rover Track</name>\n"\
            + "<Style>\n"\
            + "<LineStyle>\n"\
            + "<color>ffffffff</color>\n"\
            + "</LineStyle>\n"\
            + "</Style>\n"\
            + "<LineString>\n"\
            + "<coordinates>\n"

        for msg in self.gnss_kmls:
            gnss_kml += '{:.9f},{:.9f},{:.3f}\n'.format(msg['lon'], msg['lat'], msg['hgt'] + msg['undulation'])

        gnss_kml += "</coordinates>\n"\
            + "</LineString>\n"\
            + "</Placemark>\n"

        gnss_kml += "<Folder>\n"\
            + "<name>Rover Position</name>\n"

        for i, msg in enumerate(self.gnss_kmls):
            ep = self.weeksecondstoutc(msg['header_gps_week'], msg['header_gps_seconds'] / 1000, -18)
            ep_sp = time.strptime(ep, "%Y-%m-%d %H:%M:%S")

            vel = self.gnss_vels[i]
            north_velocity = vel['hor_spd']* math.cos(vel['trk_gnd'] * PI / 180)
            east_velocity = vel['hor_spd'] * math.sin(vel['trk_gnd'] * PI / 180)
            up_velocity = vel['vert_spd']

            self.print_gnssposvel_txt(msg, vel)

            gnss_kml += "<Placemark>\n"
            if i <= 1:
                gnss_kml += "<name>Start</name>\n"
            elif i == len(self.gnss_kmls)-1:
                gnss_kml += "<name>End</name>\n"
            else:
                if math.fmod(ep_sp[5] + 0.025, 30) < 0.05:
                    gnss_kml += "<name>"\
                        + "%02d" % ep_sp[3] + "%02d" % ep_sp[4] + "%02d" % ep_sp[5]\
                        + "</name>\n"

            gnss_kml += "<TimeStamp><when>"\
                    + time.strftime("%Y-%m-%dT%H:%M:%S.", ep_sp)\
                    + "%02dZ" % ((msg['header_gps_seconds']%1000)/10)\
                    + "</when></TimeStamp>\n"

            gnss_kml += "<description><![CDATA[\n"\
                + "<TABLE border=\"1\" width=\"100%\" Align=\"center\">\n"\
                + "<TR ALIGN=RIGHT>\n"\
                + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Time:</TD><TD>"\
                + str(msg['header_gps_week']) + "</TD><TD>" + "%.3f" % (msg['header_gps_seconds']/1000) + "</TD><TD>"\
                + "%2d:%2d:%7.4f" % (ep_sp[3],ep_sp[4],ep_sp[5]+(msg['header_gps_seconds']%1000)/1000) + "</TD><TD>"\
                + "%4d/%2d/%2d" % (ep_sp[0], ep_sp[1], ep_sp[2]) + "</TD></TR>\n"\
                + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Position:</TD><TD>"\
                + "%.8f" % msg['lat'] + "</TD><TD>" + "%.8f" % msg['lon'] + "</TD><TD>" + "%.4f" % (msg['hgt'] + msg['undulation']) + "</TD><TD>(DMS,m)</TD></TR>\n"\
                + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Vel(N,E,D):</TD><TD>"\
                + "%.4f" % north_velocity + "</TD><TD>" + "%.4f" % east_velocity + "</TD><TD>" + "%.4f" % (-up_velocity) + "</TD><TD>(m/s)</TD></TR>\n"\
                + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Att(r,p,h):</TD><TD>"\
                + "0" + "</TD><TD>" + "0" + "</TD><TD>" + "%.4f" % vel['trk_gnd'] + "</TD><TD>(deg,approx)</TD></TR>\n"\
                + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Mode:</TD><TD>"\
                + str(msg['sol_status']) + "</TD><TD>" + str(msg['pos_type']) + "</TD><TR>\n"\
                + "</TABLE>\n"\
                + "]]></description>\n"

            color = self.getpostype(msg['pos_type'])
            gnss_kml += "<styleUrl>#P" + str(color) + "</styleUrl>\n"\
                    + "<Style>\n"\
                    + "<IconStyle>\n"\
                    + "<heading>" + "%.4f" % vel['trk_gnd'] + "</heading>\n"\
                    + "</IconStyle>\n"\
                    + "</Style>\n"

            gnss_kml += "<Point>\n"\
                    + "<coordinates>" + "%.9f,%.9f,%.3f" % (msg['lon'], msg['lat'], msg['hgt'] + msg['undulation']) + "</coordinates>\n"\
                    + "</Point>\n"

            gnss_kml += "</Placemark>\n"

        gnss_kml += "</Folder>\n"\
            + "</Document>\n"\
            + "</kml>\n"

        self.write_file(self.gnss_kml_file, gnss_kml)

    def save_ins_kml(self):
        """save ins kml"""
        color = ["ffffffff","ff0000ff","ffff00ff","50FF78F0","ff00ff00","ff00aaff"]
        ins_kml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"\
            + "<kml xmlns=\"http://www.opengis.net/kml/2.2\">\n"\
            + "<Document>\n"
        for i in range(6):
            ins_kml += "<Style id=\"P" + str(i) + "\">\r\n"\
                + "<IconStyle>\r\n"\
                + "<color>" + color[i] + "</color>\n"\
                + "<scale>0.3</scale>\n"\
                + "<Icon><href>http://maps.google.com/mapfiles/kml/shapes/track.png</href></Icon>\n"\
                + "</IconStyle>\n"\
                + "</Style>\n"

        ins_kml += "<Placemark>\n"\
                + "<name>Rover Track</name>\n"\
                + "<Style>\n"\
                + "<LineStyle>\n"\
                + "<color>ffffffff</color>\n"\
                + "</LineStyle>\n"\
                + "</Style>\n"\
                + "<LineString>\n"\
                + "<coordinates>\n"

        for ins in self.inspvaxs:
            if math.fmod(ins['header_gps_seconds'] / 1000 + 0.0005, 1.0) < 0.005:
                ins_kml += '{:.9f},{:.9f},{:.3f}\n'.format(ins['lon'], ins['lat'], ins['hgt'] + ins['undulation'])

        ins_kml += "</coordinates>\n"\
            + "</LineString>\n"\
            + "</Placemark>\n"

        ins_kml += "<Folder>\n"\
            + "<name>Rover Position</name>\n"

        for i, ins in enumerate(self.inspvaxs):
            ep = self.weeksecondstoutc(ins['header_gps_week'], ins['header_gps_seconds'] / 1000, -18)
            ep_sp = time.strptime(ep, "%Y-%m-%d %H:%M:%S")

            if i == 0 or i == len(self.inspvaxs)-1 or math.fmod(ins['header_gps_seconds'] / 1000 + 0.0005, 1.0) < 0.005:
                ins_kml += "<Placemark>\n"
                if i <= 1:
                    ins_kml += "<name>Start</name>\n"
                elif i == len(self.inspvaxs)-1:
                    ins_kml += "<name>End</name>\n"
                else:
                    if math.fmod(ep_sp[5]+(ins['header_gps_seconds'] % 1000)/1000+0.025, 30) < 0.05:
                        ins_kml += "<name>"\
                            + "%02d" % ep_sp[3] + "%02d" % ep_sp[4] + "%02d" % ep_sp[5]\
                            + "</name>\n"

                ins_kml += "<TimeStamp><when>"\
                    + time.strftime("%Y-%m-%dT%H:%M:%S.", ep_sp)\
                    + "%02dZ" % ((ins['header_gps_seconds']%1000)/10)\
                    + "</when></TimeStamp>\n"

                ins_kml += "<description><![CDATA[\n"\
                    + "<TABLE border=\"1\" width=\"100%\" Align=\"center\">\n"\
                    + "<TR ALIGN=RIGHT>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Time:</TD><TD>"\
                    + str(ins['header_gps_week']) + "</TD><TD>" + "%.3f" % (ins['header_gps_seconds']/1000) + "</TD><TD>"\
                    + "%2d:%2d:%7.4f" % (ep_sp[3],ep_sp[4],ep_sp[5]+(ins['header_gps_seconds']%1000)/1000) + "</TD><TD>"\
                    + "%4d/%2d/%2d" % (ep_sp[0], ep_sp[1], ep_sp[2]) + "</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Position:</TD><TD>"\
                    + "%.9f" % ins['lat'] + "</TD><TD>" + "%.9f" % ins['lon'] + "</TD><TD>" + "%.4f" % (ins['hgt'] + ins['undulation']) + "</TD><TD>(DMS,m)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Vel(N,E,D):</TD><TD>"\
                    + "%.4f" % ins['north_velocity'] + "</TD><TD>" + "%.4f" % ins['east_velocity'] + "</TD><TD>" + "%.4f" % (-ins['up_velocity']) + "</TD><TD>(m/s)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Att(r,p,h):</TD><TD>"\
                    + "%.4f" % ins['roll'] + "</TD><TD>" + "%.4f" % ins['pitch'] + "</TD><TD>" + "%.4f" % (-ins['azimuth']) + "</TD><TD>(deg,approx)</TD></TR>\n"\
                    + "<TR ALIGN=RIGHT><TD ALIGN=LEFT>Mode:</TD><TD>"\
                    + str(ins['ins_status']) + "</TD><TD>" + str(ins['pos_type']) + "</TD><TR>\n"\
                    + "</TABLE>\n"\
                    + "]]></description>\n"

                pcolor = 0
                if ins['ins_status'] == 0:     # "INS_INACTIVE"
                    pcolor = 0
                elif ins['ins_status'] == 1:   # "SPP/INS_SPP"
                    pcolor = 1
                elif ins['ins_status'] == 2:   # "PSRDIFF/INS_PSRDIFF (RTD)"
                    pcolor = 1
                elif ins['ins_status'] == 3:   # "INS_DR"
                    pcolor = 4
                elif ins['ins_status'] == 6:   # "RTK_FIX/INS_RTKFIXED"
                    pcolor = 1
                elif ins['ins_status'] == 7:   # "RTK_FLOAT/INS_RTKFLOAT"
                    pcolor = 1

                ins_kml += "<styleUrl>#P" + str(pcolor) + "</styleUrl>\n"\
                    + "<Style>\n"\
                    + "<IconStyle>\n"\
                    + "<heading>" + "%.4f" % ins['azimuth'] + "</heading>\n"\
                    + "</IconStyle>\n"\
                    + "</Style>\n"

                ins_kml += "<Point>\n"\
                    + "<coordinates>" + "%.9f,%.9f,%.3f" % (ins['lon'], ins['lat'], ins['hgt'] + ins['undulation']) + "</coordinates>\n"\
                    + "</Point>\n"

                ins_kml += "</Placemark>\n"

        ins_kml += "</Folder>\n"\
            + "</Document>\n"\
            + "</kml>\n"

        self.write_file(self.ins_kml_file, ins_kml)

    def output_gga_nmea(self, time, pos_type, blh, ns, dop, age):
        """output gga nmea"""
        gga = ''
        if pos_type != 1 and pos_type != 4 and pos_type != 5:
            gga += '$GPGGA,,,,,,,,,,,,,,'
        else:
            ep = [0] * 6
            dms1 = [0] * 3
            dms2 = [0] * 3
            h = 0.0

            time -= 18.0
            ep[2] = math.floor(time / (24 * 3600))
            time -= ep[2] * 24 * 3600.0
            ep[3] = math.floor(time / 3600)
            time -= ep[3] * 3600
            ep[4] = math.floor(time / 60)
            time -= ep[4] * 60
            ep[5] = time

            self.deg2dms(math.fabs(blh[0]) * 180.0 / PI, dms1)
            self.deg2dms(math.fabs(blh[1]) * 180.0 / PI, dms2)

            lat_str = 'N'
            if blh[0] < 0:
                lat_str = 'S'
            lon_str = 'E'
            if blh[1] < 0:
                lon_str = 'W'
            gga += '$GPGGA,{:02.0f}{:02.0f}{:05.2f},{:02.0f}{:010.7f},{:s},{:03.0f}{:010.7f},{:s},{:d},{:02d},{:.1f},{:.3f},M,{:.3f},M,{:.1f},'.format(
                ep[3], ep[4], ep[5], dms1[0], dms1[1] + dms1[2] / 60.0, lat_str,
                dms2[0], dms2[1] + dms2[2] / 60.0, lon_str, pos_type,
                ns, dop, blh[2] - h, h, age)

        checksum = 0
        for i in range(1, len(gga)):
            checksum = checksum ^ ord(gga[i])
        str_checksum = hex(checksum)
        if str_checksum.startswith("0x"):
            str_checksum = str_checksum[2:]
        gga += '*' + str_checksum.upper() + '\r\n'
        return gga


    def update_m_n(self, blh):
        """update m and n"""
        sinb = math.sin(blh[0])
        temp = 1 - WGS84['e2'] * sinb * sinb
        sqrt_temp = math.sqrt(temp)
        m = WGS84['a'] * (1 - WGS84['e2']) / (sqrt_temp * temp)
        n = WGS84['a'] / sqrt_temp
        return m, n

    def euler2dcm(self, eular):
        """euler to dcm"""
        c_vn =[[0]*3 for _ in range(3)]
        roll = eular[0]
        pitch = eular[1]
        heading = eular[2]

        cr = math.cos(roll)
        cp = math.cos(pitch)
        ch = math.cos(heading)
        sr = math.sin(roll)
        sp = math.sin(pitch)
        sh = math.sin(heading)

        c_vn[0][0] = cp * ch
        c_vn[0][1] =  -cr * sh + sr * sp * ch
        c_vn[0][2] = sr * sh + cr * sp*ch

        c_vn[1][0] = cp * sh
        c_vn[1][1] = cr * ch + sr * sp*sh
        c_vn[1][2] = -sr * ch + cr * sp * sh

        c_vn[2][0] = -sp
        c_vn[2][1] = sr * cp
        c_vn[2][2] = cr * cp

        return c_vn

    def matrix_mutiply(self, matrix_a, matrix_b, matrix_a_row, matrix_a_column, matrix_b_column, matrix_result):
        """matrix_mutiply"""
        sum = 0.0
        median = 0.0
        for i in range(matrix_a_row):
            for k in range(matrix_b_column):
                for j in range(matrix_a_column):
                    median = matrix_a[i][j] * matrix_b[j]
                    sum += median

                matrix_result[matrix_b_column*i + k] = sum
                sum = 0

    def matrix_add(self, matrix_a, matrix_b, matrix_a_row, matrix_a_colume, matrix_result):
        """matrix add"""
        for i in range(matrix_a_row*matrix_a_colume):
            matrix_result[i] = matrix_a[i] + matrix_b[i]

    def getpostype(self, position_type):
        """get position type"""
        positions = {
            '16': 1,
            '53': 1,
            '17': 2,
            '54': 2,
            '50': 4,
            '56': 4,
            '55': 5,
            '34': 5,
        }
        return positions.get(str(position_type), 0)

    def deg2dms(self, deg, dms):
        """deg to dms"""
        sign = 1.0
        if deg < 0.0:
            sign = -1.0

        a = math.fabs(deg)
        dms[0] = math.floor(a)
        a = (a - dms[0]) * 60.0
        dms[1] = math.floor(a)
        a = (a - dms[1]) * 60.0
        dms[2] = a
        dms[0] *= sign

    def weeksecondstoutc(self, gpsweek, gpsseconds, leapseconds):
        datetimeformat = "%Y-%m-%d %H:%M:%S"
        epoch = datetime.datetime.strptime("1980-01-06 00:00:00",datetimeformat)
        elapsed = datetime.timedelta(days=(gpsweek*7),seconds=(gpsseconds+leapseconds))
        return datetime.datetime.strftime(epoch + elapsed,datetimeformat)

    def write_file(self, file, data):
        if self.files[file] is not None:
            self.files[file].write(data)

def receive_args():
    """Parse argument"""
    parser = argparse.ArgumentParser(
        description='Aceinna INS2000 parse input args command:'
    )

    parser.add_argument("-f", type=str, help="The file to be decoded", default="ins2000.bin")
    parser.add_argument("-c", type=str, help="Decoding configuration file",
        default="../src/aceinna/setting/INS2000/INS2000.json")
    return parser.parse_args()


if __name__ == '__main__':
    args = receive_args()

    appRoot = os.path.abspath(os.path.dirname(__file__))

    binFile = args.f
    if not os.path.isabs(binFile):
        binFile = os.path.abspath(os.path.join(appRoot, binFile))

    if not os.path.exists(binFile):
        print("Could not find the parse file {0}".format(binFile))
        sys.exit(1)

    cfgFile = args.c
    if not os.path.isabs(cfgFile):
        cfgFile = os.path.abspath(os.path.join(appRoot, cfgFile))

    if not os.path.exists(cfgFile):
        print("Could not find the config file {0}".format(cfgFile))
        sys.exit(1)

    ins_parser = INS2000Parser(binFile, cfgFile)
    ins_parser.run()
