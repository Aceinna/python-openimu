"""
Driver for Aceinna OpenIMU Series Products
Based on PySerial https://github.com/pyserial/pyserial
Created on 2019-08-30
@author: m5horton
"""


"""
command line: python bootloader.py <binary image name>


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

Control EEPROM Config Fields
get_fields
set_fields
read_fields
write_fields

Bootloader Functions
upgrade_fw      - entry point to flash a serial connected IMU
start_bootloader
write_block
start_app

Syncing 
sync            - trys to sync to a unit continuously transmitting
set_quiet       - sets unit to stop continuous transmission (stream_mode = 0)
restore_odr     - restores unit to whatever odr_setting is

Data Functions
get_latest
get_packet
get_id_str
get_bit_status
parse_packet
calc_crc

Serial          - a tiny layer on top of Pyserial to handle exceptions as means of device detection
open
close
read
write
reset_buffer

Ping
ping_test

"""




import serial
import math
import string
import time
import sys
import collections
import glob
class OpenIMU:
    def __init__(self, ws=False):
        '''Initialize and then start ports search and autobaud process
        '''
        self.ws = ws                # set to true if being run as a thread in a websocket server
        self.ser = None             # the active UART
        self.synced = 0             # synced status in streaming mode
        # 0 = polled, 1 = streaming, commanded by set_quiet and restore_odr
        self.stream_mode = 0
        self.device_id = 0          # unit's id str
        # imu is successfully connected to a com port, kind of redundant with device_id property
        self.connected = 0
        self.odr_setting = 0        # value of the output data rate EEPROM setting
        self.logging = 0            # logging on or off
        self.logger = None          # the file logger instance
        self.packet_size = 0        # expected size of packet
        self.packet_type = 0        # expected type of packet
        # an accurate estimate of elapsed time in ODR mode using IMU timer data
        self.elapsed_time_sec = 0
        self.data = {}              # placeholder imu measurements of last converted packeted
        self.filename = sys.argv[1]
        self.ID = ''
        self.port = 'none'
        self.boot = 0

    def find_device(self):
        ''' Finds active ports and then autobauds units, repeats every 2 seconds
        '''
        while not self.autobaud(self.find_ports()):
            time.sleep(2)

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
            try:
                print('Trying: ' + port)
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

    def autobaud(self, ports):
        '''Autobauds unit - first check for stream_mode / continuous data, then check by polling unit
           :returns: 
                true when successful
        '''

        for port in ports:
            for baud in [115200, 57600, 38400]:
                self.open(port, baud)
                # sync() works for stream mode
                self.sync()
                if self.stream_mode:
                    print('Connected Stream Mode ' +
                          '{0:d}'.format(baud) + '  ' + port)
                    break
                else:
                    self.ser.close()

            # stream mode not found for port, check port by polling
            if self.stream_mode == 0:
                for baud in [115200, 57600, 38400]:
                    self.open(port, baud)
                    self.device_id = self.get_id_str()
                    if self.device_id:
                        print('Connected Polled Mode ' + '{0:d}'.format(baud))
                        odr = self.read_fields([0x0001], 1)
                        if odr:
                            print('Saved ODR: ' + '{0:d}'.format(odr[0][1]))
                            self.odr_setting = odr[0][1]
                        self.connected = 1
                        self.port = port
                        return True
                    else:
                        self.close()

            # in stream stream mode worked, get odr field and id str
            else:
                odr = self.read_fields([0x0001], 1)
                if odr:
                    print('Current ODR: ' + '{0:d}'.format(odr[0][1]))
                    self.odr_setting = odr[0][1]
                    self.device_id = self.get_id_str()  # read device string
                    self.restore_odr()
                    self.connected = 1                  # a valid connection exists to unit
                    return True
                else:
                    print('failed to get id string')
                    return False

        return False

    def get_latest(self):
        '''Get latest converted IMU readings in converted units
            :returns:
                data object or error message for web socket server to pass to app
        '''
        if self.stream_mode == 1:
            return self.data
        else:
            return {'error': 'not streaming'}

    def start_log(self, data):
        '''Creates file or cloud logger.  Autostarts log activity if ws (websocket) set to false
        '''
        self.logging = 1
        self.logger = file_storage.LogIMU380Data(self, data)
        if self.ws == False and self.odr_setting != 0:
            self.connect()

    def stop_log(self):
        '''Stops file or cloud logger
        '''
        self.logging = 0
        self.logger.close()
        self.logger = None

    def ping_test(self):
        '''Executes ping test.  Not currently used
            :returns:
                True is successful
        '''
        self.stream_mode = 0
        C = [0x55, 0x55, 0x50, 0x4B, 0x00]      # 0x55504B00
        # for some reason must add a payload byte to get correct CRC
        crc = self.calc_crc(C[2:4] + [0x00])
        crc_msb = (crc & 0xFF00) >> 8
        crc_lsb = (crc & 0x00FF)
        C.insert(len(C), crc_msb)
        C.insert(len(C), crc_lsb)
        self.reset_buffer()
        self.write(C)
        # grab with header, type, length, and crc
        R = self.read(7)
        if R == bytearray(C):
            return True
        else:
            return False

    def get_fields(self, fields, ws=False):
        '''Executes 380 GF command for an array of fields.  GF Command get current Temporary setting of 380
        '''
        # Take unit out of stream mode
        self.set_quiet()
        num_fields = len(fields)
        C = [0x55, 0x55, ord('G'), ord('F'), num_fields * 2 + 1, num_fields]
        for field in fields:
            field_msb = (field & 0xFF00) >> 8
            field_lsb = field & 0x00FF
            C.insert(len(C), field_msb)
            C.insert(len(C), field_lsb)
        crc = self.calc_crc(C[2:C[4]+5])
        crc_msb = (crc & 0xFF00) >> 8
        crc_lsb = (crc & 0x00FF)
        C.insert(len(C), crc_msb)
        C.insert(len(C), crc_lsb)
        self.write(C)
        R = self.read(num_fields * 4 + 1 + 7)
        data = []
        if R and R[0] == 85 and R[1] == 85:
            # crc is last two bytes
            packet_crc = 256 * R[-2] + R[-1]
            calc_crc = self.calc_crc(R[2:R[4]+5])
            if packet_crc == calc_crc:
                self.packet_type = '{0:1c}'.format(
                    R[2]) + '{0:1c}'.format(R[3])
                data = self.parse_packet(R[5:R[4]+5], ws)
        return data

    def read_fields(self, fields, ws=False):
        '''Executes 380 RF command for an array of fields.  RF Command get current Permanent setting of 380
        '''
        # Take unit out of stream mode
        self.set_quiet()
        num_fields = len(fields)
        C = [0x55, 0x55, ord('R'), ord('F'), num_fields * 2 + 1, num_fields]
        for field in fields:
            field_msb = (field & 0xFF00) >> 8
            field_lsb = field & 0x00FF
            C.insert(len(C), field_msb)
            C.insert(len(C), field_lsb)
        crc = self.calc_crc(C[2:C[4]+5])
        crc_msb = (crc & 0xFF00) >> 8
        crc_lsb = (crc & 0x00FF)
        C.insert(len(C), crc_msb)
        C.insert(len(C), crc_lsb)
        self.write(C)
        R = self.read(num_fields * 4 + 1 + 7)
        data = []
        if len(R) and R[0] == 85 and R[1] == 85:
            # crc is last two bytes
            packet_crc = 256 * R[-2] + R[-1]
            calc_crc = self.calc_crc(R[2:R[4]+5])
            if packet_crc == calc_crc:
                self.packet_type = '{0:1c}'.format(
                    R[2]) + '{0:1c}'.format(R[3])
                data = self.parse_packet(R[5:R[4]+5], ws)
        return data

    def write_fields(self, field_value_pairs, ws=False):
        '''Executes 380 WF command for an array of fields, value pairs.  WF Command set Permanent setting for fields on 380
        '''
        self.set_quiet()
        num_fields = len(field_value_pairs)
        C = [0x55, 0x55, ord('W'), ord('F'), num_fields * 4 + 1, num_fields]
        FIELD = 0
        VALUE = 1
        for field_value in field_value_pairs:
            field_msb = (field_value[FIELD] & 0xFF00) >> 8
            field_lsb = field_value[FIELD] & 0x00FF
            if isinstance(field_value[VALUE], int):
                value_msb = (field_value[VALUE] & 0xFF00) >> 8
                value_lsb = field_value[VALUE] & 0x0FF
            elif isinstance(field_value[VALUE], str):
                value_msb = ord(field_value[VALUE][0])
                value_lsb = ord(field_value[VALUE][1])
            C.insert(len(C), field_msb)
            C.insert(len(C), field_lsb)
            C.insert(len(C), value_msb)
            C.insert(len(C), value_lsb)
        crc = self.calc_crc(C[2:C[4]+5])
        crc_msb = (crc & 0xFF00) >> 8
        crc_lsb = (crc & 0x00FF)
        C.insert(len(C), crc_msb)
        C.insert(len(C), crc_lsb)
        self.write(C)
        time.sleep(1.0)
        R = self.read(num_fields * 2 + 1 + 7)
        print(R)
        data = []
        if R[0] == 85 and R[1] == 85:
            # crc is last two bytes
            packet_crc = 256 * R[-2] + R[-1]
            if self.calc_crc(R[2:R[4]+5]) == packet_crc:
                if R[2] == 0 and R[3] == 0:
                    print('SET FIELD ERROR/FAILURE')
                    return
                else:
                    self.packet_type = '{0:1c}'.format(
                        R[2]) + '{0:1c}'.format(R[3])
                    data = self.parse_packet(R[5:R[4]+5], ws)
        return data

    def set_fields(self, field_value_pairs, ws=False):
        '''Executes 380 SF command for an array of fields, value pairs.  SF Command sets Temporary setting for fields on 380
        '''
        self.set_quiet()
        num_fields = len(field_value_pairs)
        C = [0x55, 0x55, ord('S'), ord('F'), num_fields * 4 + 1, num_fields]
        FIELD = 0
        VALUE = 1
        for field_value in field_value_pairs:
            if (field_value[FIELD] == 1):
                self.odr_setting = field_value[VALUE]
            field_msb = (field_value[FIELD] & 0xFF00) >> 8
            field_lsb = field_value[FIELD] & 0x00FF
            value_msb = (field_value[VALUE] & 0xFF00) >> 8
            value_lsb = field_value[VALUE] & 0x0FF
            C.insert(len(C), field_msb)
            C.insert(len(C), field_lsb)
            C.insert(len(C), value_msb)
            C.insert(len(C), value_lsb)
        crc = self.calc_crc(C[2:C[4]+5])
        crc_msb = (crc & 0xFF00) >> 8
        crc_lsb = (crc & 0x00FF)
        C.insert(len(C), crc_msb)
        C.insert(len(C), crc_lsb)
        self.write(C)
        R = self.read(num_fields * 2 + 1 + 7)
        data = []
        if R[0] == 85 and R[1] == 85:
            # crc is last two bytes
            packet_crc = 256 * R[-2] + R[-1]
            if self.calc_crc(R[2:R[4]+5]) == packet_crc:
                if R[2] == 0 and R[3] == 0:
                    print('SET FIELD ERROR/FAILURE')
                    return
                else:
                    self.packet_type = '{0:1c}'.format(
                        R[2]) + '{0:1c}'.format(R[3])
                    data = self.parse_packet(R[5:R[4]+5], ws)
        return data

    def set_quiet(self):
        '''Force 380 device to quiet / polled mode and inject 0.1 second delay, then clear input buffer
        '''
        self.stream_mode = 0
        time.sleep(0.1)  # wait for any packets to clear
        C = [0x55, 0x55, ord('S'), ord('F'), 0x05, 0x01,
             0x00, 0x01, 0x00, 0x00]
        crc = self.calc_crc(C[2:C[4]+5])
        crc_msb = (crc & 0xFF00) >> 8
        crc_lsb = (crc & 0x00FF)
        C.insert(len(C), crc_msb)
        C.insert(len(C), crc_lsb)
        self.reset_buffer()
        self.write(C)
        self.read(10)
        time.sleep(0.1)  # wait for command to take effect
        self.reset_buffer()

    def restore_odr(self):
        '''Restores device to odr mode vs SF command
        '''
        print('restore odr to ' + '{0:d}'.format(self.odr_setting))
        C = [0x55, 0x55, ord('S'), ord('F'), 0x05, 0x01,
             0x00, 0x01, 0x00, self.odr_setting]
        crc = self.calc_crc(C[2:C[4]+5])
        crc_msb = (crc & 0xFF00) >> 8
        crc_lsb = (crc & 0x00FF)
        C.insert(len(C), crc_msb)
        C.insert(len(C), crc_lsb)
        self.reset_buffer()
        self.write(C)
        self.read(10)
        time.sleep(0.1)  # wait for command to take effect
        self.reset_buffer()
        self.synced = 0
        self.packet_size = 0
        self.packet_type = 0
        self.elapsed_time_sec = 0
        self.data = {}
        self.stream_mode = 1

    def connect(self):
        '''Continous data collection loop to get and process data packets
        '''
        self.find_device()

        if self.odr_setting:
            self.restore_odr()
        else:
            print('no odr setting can connect')
            return
        while self.odr_setting and self.connected:
            if self.stream_mode:
                self.get_packet()
            else:
                time.sleep(0.05)

    def disconnect(self):
        '''Ends data collection loop.  Reset settings
        '''
        self.connected = 0
        self.device_id = 0
        self.odr_setting = 0
        self.stream_mode = 0
        self.synced = 0
        self.packet_size = 0
        self.packet_type = 0

    def get_packet(self):
        '''Syncs unit and gets packet.  Assumes unit is in stream_mode'''

        # Already synced
        if self.synced == 1:
            # Read next packet of data based on expected packet size
            S = self.read(self.packet_size + 7)

            if len(S) < 2:
                # Read Failed
                self.synced = 0
                return
            if S[0] == 85 and S[1] == 85:
                packet_crc = 256 * S[-2] + S[-1]
                # Compare computed and read crc
                if self.calc_crc(S[2:S[4]+5]) == packet_crc:
                    # 5 is offset of first payload byte, S[4]+5 is offset of last payload byte
                    self.data = self.parse_packet(S[5:S[4]+5])
            else:
                # Get synced and then read next packet
                self.sync()
                self.get_packet()
        else:
            # Get synced and then read next packet
            self.sync()
            self.get_packet()

    def sync(self, prev_byte=0, bytes_read=0):
        '''Syncs a 380 in Continuous / Stream mode.  Assumes longest packet is 40 bytes
            TODO: check this assumption
            TODO: add check of CRC
            :returns:
                true if synced, false if not
        '''
        S = self.read(1)

        if not S:
            return False
        if S[0] == 85 and prev_byte == 85:      # VALID HEADER FOUND
            # Once header is found then read off the rest of packet
            print('Synced!')
            self.synced = 1
            config_bytes = self.read(3)
            self.packet_type = '{0:1c}'.format(
                config_bytes[0]) + '{0:1c}'.format(config_bytes[1])
            self.packet_size = config_bytes[2]
            # clear bytes off port, payload + 2 byte CRC
            self.read(config_bytes[2] + 2)
            return True
        else:
            # Repeat sync to search next byte pair for header
            if bytes_read == 0:
                print('Connecting ....')
            bytes_read = bytes_read + 1
            print(bytes_read)
            self.synced = 0
            if (bytes_read < 40):
                self.sync(S[0], bytes_read)
            else:
                return False

    def start_bootloader(self):
        '''Starts bootloader
            :returns:
                True if bootloader mode entered, False if failed
        '''
        self.set_quiet()
        C = [0x55, 0x55, ord('J'), ord('I'), 0x00]
        # for some reason must add a payload byte to get correct CRC
        crc = self.calc_crc(C[2:4] + [0x00])
        crc_msb = (crc & 0xFF00) >> 8
        crc_lsb = (crc & 0x00FF)
        C.insert(len(C), crc_msb)
        C.insert(len(C), crc_lsb)
        self.write(C)
        time.sleep(2)   # must wait for boot loader to be ready
        R = self.read(5)
        if R[0] == 85 and R[1] == 85:
            self.packet_type = '{0:1c}'.format(R[2]) + '{0:1c}'.format(R[3])
            if self.packet_type == 'JI':
                self.read(R[4]+2)
                print('bootloader ready')
                time.sleep(2)
                self.reset_buffer()
                if self.boot == 0:
                    print('resync with device')
                    time.sleep(2)
#                    self.find_device()
#                    self.reset_buffer()
                return True
            else:
                return False
        else:
            return False

    def start_app(self):
        '''Starts app
        '''
        self.set_quiet()
        C = [0x55, 0x55, ord('J'), ord('A'), 0x00]
        # for some reason must add a payload byte to get correct CRC
        crc = self.calc_crc(C[2:4] + [0x00])
        crc_msb = (crc & 0xFF00) >> 8
        crc_lsb = (crc & 0x00FF)
        C.insert(len(C), crc_msb)
        C.insert(len(C), crc_lsb)
        self.write(C)
        time.sleep(1)
        R = self.read(7)
        if R[0] == 85 and R[1] == 85:
            self.packet_type = '{0:1c}'.format(R[2]) + '{0:1c}'.format(R[3])
            print(self.packet_type)

    def write_block(self, buf, data_len, addr):
        '''Executed WA command to write a block of new app code into memory
        '''
        print(data_len, addr)
        C = [0x55, 0x55, ord('W'), ord('A'), data_len+5]
        addr_3 = (addr & 0xFF000000) >> 24
        addr_2 = (addr & 0x00FF0000) >> 16
        addr_1 = (addr & 0x0000FF00) >> 8
        addr_0 = (addr & 0x000000FF)
        C.insert(len(C), addr_3)
        C.insert(len(C), addr_2)
        C.insert(len(C), addr_1)
        C.insert(len(C), addr_0)
        C.insert(len(C), data_len)
        for i in range(data_len):
            C.insert(len(C), buf[i])
        crc = self.calc_crc(C[2:C[4]+5])
        crc_msb = int((crc & 0xFF00) >> 8)
        crc_lsb = int((crc & 0x00FF))
        C.insert(len(C), crc_msb)
        C.insert(len(C), crc_lsb)
        status = 0
        while (status == 0):
            self.write(C)
            if addr == 0:
                time.sleep(8)
            else:
                time.sleep(0.1)
            R = self.read(12)  # longer response
            if len(R) > 1 and R[0] == 85 and R[1] == 85:
                self.packet_type = '{0:1c}'.format(
                    R[2]) + '{0:1c}'.format(R[3])
                print(self.packet_type)
                if self.packet_type == 'WA':
                    status = 1
                else:
                    sys.exit()
                    print('retry 1')
                    status = 0
            else:
                print(len(R))
                print(R)
                self.reset_buffer()
                time.sleep(1)
                print('no packet')
                sys.exit()

    def upgrade_fw(self, file):
        '''Upgrades firmware of connected 380 device to file provided in argument
        '''
        print('upgrade fw')
        max_data_len = 240
        write_len = 0
        fw = open(self.filename, 'rb').read()
        fs_len = len(fw)

#        if not self.start_bootloader():
#            print('Bootloader Start Failed')
#            return False

        time.sleep(1)
        while (write_len < fs_len):
            packet_data_len = max_data_len if (
                fs_len - write_len) > max_data_len else (fs_len-write_len)
            # From IMUView
            # Array.Copy(buf,write_len,write_buf,0,packet_data_len);
            write_buf = fw[write_len:(write_len+packet_data_len)]
            self.write_block(write_buf, packet_data_len, write_len)
            write_len += packet_data_len
        time.sleep(1)
        # Start new app
        self.start_app()

    def get_id_str(self):
        ''' Executes GP command and requests ID data from 380
            :returns:
                id string of connected device, or false if failed
        '''
        self.set_quiet()
        C = [0x55, 0x55, ord('G'), ord('P'), 0x02, ord('I'), ord('D')]
        crc = self.calc_crc(C[2:C[4]+5])
        crc_msb = (crc & 0xFF00) >> 8
        crc_lsb = (crc & 0x00FF)
        C.insert(len(C), crc_msb)
        C.insert(len(C), crc_lsb)
        self.write(C)
        R = self.read(5)
        if len(R) and R[0] == 85 and R[1] == 85:
            self.packet_type = '{0:1c}'.format(R[2]) + '{0:1c}'.format(R[3])
            payload_length = R[4]
            R = self.read(payload_length+2)
            id_str = self.parse_packet(R[0:payload_length])
            self.ID = id_str
            if id_str.find('load') == -1:
                self.boot = 0
            else:
                self.boot = 1
            return id_str
        else:
            return False

    def get_bit_status(self):
        ''' Executes GP command and requests bit stsatus from 380
            :returns:
        '''
        self.set_quiet()
        C = [0x55, 0x55, ord('G'), ord('P'), 0x02, ord('T'), ord('0')]
        crc = self.calc_crc(C[2:C[4]+5])
        crc_msb = (crc & 0xFF00) >> 8
        crc_lsb = (crc & 0x00FF)
        C.insert(len(C), crc_msb)
        C.insert(len(C), crc_lsb)
        self.write(C)
        R = self.read(5)
        if len(R) and R[0] == 85 and R[1] == 85:
            self.packet_type = '{0:1c}'.format(R[2]) + '{0:1c}'.format(R[3])
            payload_length = R[4]
            R = self.read(payload_length+2)
            id_str = self.parse_packet(R[0:payload_length])
            return id_str
        else:
            return False

    def parse_packet(self, payload, ws=False):
        '''Parses packet payload to engineering units based on packet type
           Currently supports S0, S1, A1 packets.  Logs data if logging is on.
           Prints data if a GF/RF/SF/WF. Add A2, N0, N1 packet types.
        '''
        if self.packet_type == 'S0':
            '''S0 Payload Contents
                Byte Offset	Name	Format	Scaling	Units	Description
                0	xAccel	    I2	20/2^16	G	X accelerometer
                2	yAccel	    I2	20/2^16	G	Y accelerometer
                4	zAccel	    I2	20/2^16	G	Z accelerometer
                6	xRate   	I2	7*pi/2^16 [1260 deg/2^16]	rad/s [deg/sec]	X angular rate
                8	yRate	    I2	7*pi/2^16 [1260 deg/2^16]	rad/s [deg/sec]	Y angular rate
                10	zRate	    I2	7*pi/2^16 [1260 deg/2^16]	rad/s [deg/sec]	Z angular rate
                12	xMag	    I2	2/2^16	Gauss	X magnetometer
                14	yMag	    I2	2/2^16	Gauss	Y magnetometer
                16	zMag	    I2	2/2^16	Gauss	Z magnetometer
                18	xRateTemp	I2	200/2^16	deg. C	X rate temperature
                20	yRateTemp	I2	200/2^16	deg. C	Y rate temperature
                22	zRateTemp	I2	200/2^16	deg. C	Z rate temperature
                24	boardTemp	I2	200/2^16	deg. C	CPU board temperature
                26	GPSITOW	    U2	truncated	Ms	GPS ITOW (lower 2 bytes)
                28	BITstatus   U2 Master BIT and Status'''

            accels = [0 for x in range(3)]
            for i in range(3):
                accel_int16 = (256 * payload[2*i] + payload[2*i+1]) - 65535 if 256 * \
                    payload[2*i] + payload[2*i+1] > 32767 else 256 * payload[2*i] + payload[2*i+1]
                accels[i] = (9.80665 * 20 * accel_int16) / math.pow(2, 16)

            gyros = [0 for x in range(3)]
            for i in range(3):
                gyro_int16 = (256 * payload[2*i+6] + payload[2*i+7]) - 65535 if 256 * payload[2 *
                                                                                              i+6] + payload[2*i+7] > 32767 else 256 * payload[2*i+6] + payload[2*i+7]
                gyros[i] = (1260 * gyro_int16) / math.pow(2, 16)

            mags = [0 for x in range(3)]
            for i in range(3):
                mag_int16 = (256 * payload[2*i+12] + payload[2*i+13]) - 65535 if 256 * payload[2 *
                                                                                               i+12] + payload[2*i+13] > 32767 else 256 * payload[2*i+12] + payload[2*i+13]
                mags[i] = (2 * mag_int16) / math.pow(2, 16)

            temps = [0 for x in range(4)]
            for i in range(4):
                temp_int16 = (256 * payload[2*i+18] + payload[2*i+19]) - 65535 if 256 * payload[2 *
                                                                                                i+18] + payload[2*i+19] > 32767 else 256 * payload[2*i+18] + payload[2*i+19]
                temps[i] = (200 * temp_int16) / math.pow(2, 16)

            # Counter Value
            itow = 256 * payload[26] + payload[27]

            # BIT Value
            bit = 256 * payload[28] + payload[29]

            if self.data:
                prev_time = self.data['GPSITOW']
                if (itow > prev_time):
                    self.elapsed_time_sec += (1.0 /
                                              65535.0) * (itow - prev_time)
                else:
                    self.elapsed_time_sec += (1.0 / 65535.0) * \
                        (65535 - prev_time) + (1.0 / 65535.0) * itow

            data = collections.OrderedDict([('time', self.elapsed_time_sec), ('xAccel', accels[0]), ('yAccel', accels[1]), ('zAccel', accels[2]), ('xRate', gyros[0]),
                                            ('yRate', gyros[1]), ('zRate', gyros[2]), ('xMag', mags[0]), (
                                                'yMag', mags[1]), ('zMag', mags[2]), ('xRateTemp', temps[0]),
                                            ('yRateTemp', temps[1]), ('zRateTemp', temps[2]), ('boardTemp', temps[3]), ('GPSITOW', itow), ('BITstatus', bit)])

            if self.logging == 1 and self.logger is not None:
                self.logger.log(data, self.odr_setting)

            return data

        elif self.packet_type == 'F1':
            '''F1 Payload Contents
                Byte Offset	Name	Format	Scaling	Units	Description
                0       payload length  U2                      user-definied payload length 
                2       payload content U1                      JSON file'''

            # payload length
            len = 256 * payload[0] + payload[1]

            if len == 0:
                return 0

            f = open("user_format.json", "r")

            f.close()

            return len

        elif self.packet_type == 'S1':
            '''S1 Payload Contents
                Byte Offset	Name	Format	Scaling	Units	Description
                0	xAccel	I2	20/2^16	G	X accelerometer
                2	yAccel	I2	20/2^16	G	Y accelerometer
                4	zAccel	I2	20/2^16	G	Z accelerometer
                6	xRate	I2	7*pi/2^16   [1260 deg/2^16]	rad/s [deg/sec]	X angular rate
                8	yRate	I2	7*pi/2^16   [1260 deg/2^16]	rad/s [deg/sec]	Y angular rate
                10	zRate	I2	7*pi/2^16   [1260 deg/2^16]	rad/s [deg/sec]	Z angular rate
                12	xRateTemp	I2	200/2^16	deg. C	X rate temperature
                14	yRateTemp	I2	200/2^16	deg. C	Y rate temperature
                16	zRateTemp	I2	200/2^16	deg. C	Z rate temperature
                18	boardTemp	I2	200/2^16	deg. C	CPU board temperature
                20	counter         U2	-	packets	Output time stamp 
                22	BITstatus	U2	-	-	Master BIT and Status'''

            accels = [0 for x in range(3)]
            for i in range(3):
                accel_int16 = (256 * payload[2*i] + payload[2*i+1]) - 65535 if 256 * \
                    payload[2*i] + payload[2*i+1] > 32767 else 256 * payload[2*i] + payload[2*i+1]
                accels[i] = (9.80665 * 20 * accel_int16) / math.pow(2, 16)

            gyros = [0 for x in range(3)]
            for i in range(3):
                gyro_int16 = (256 * payload[2*i+6] + payload[2*i+7]) - 65535 if 256 * payload[2 *
                                                                                              i+6] + payload[2*i+7] > 32767 else 256 * payload[2*i+6] + payload[2*i+7]
                gyros[i] = (1260 * gyro_int16) / math.pow(2, 16)

            temps = [0 for x in range(4)]
            for i in range(4):
                temp_int16 = (256 * payload[2*i+12] + payload[2*i+13]) - 65535 if 256 * payload[2 *
                                                                                                i+12] + payload[2*i+13] > 32767 else 256 * payload[2*i+12] + payload[2*i+13]
                temps[i] = (200 * temp_int16) / math.pow(2, 16)

            # Counter Value
            count = 256 * payload[20] + payload[21]

            # BIT Value
            bit = 256 * payload[22] + payload[23]

            if self.data:
                prev_time = self.data['counter']
                if (count > prev_time):
                    self.elapsed_time_sec += (1.0 /
                                              65535.0) * (count - prev_time)
                else:
                    self.elapsed_time_sec += (1.0 / 65535.0) * \
                        (65535 - prev_time) + (1.0 / 65535.0) * count

            data = collections.OrderedDict([('time', self.elapsed_time_sec), ('xAccel', accels[0]), ('yAccel', accels[1]), ('zAccel', accels[2]), ('xRate', gyros[0]),
                                            ('yRate', gyros[1]), ('zRate',
                                                                  gyros[2]), ('xRateTemp', temps[0]),
                                            ('yRateTemp', temps[1]), ('zRateTemp', temps[2]), ('boardTemp', temps[3]), ('counter', count), ('BITstatus', bit)])

            if self.logging == 1 and self.logger is not None:
                self.logger.log(data, self.odr_setting)

            return data

        elif self.packet_type == 'A1':
            '''A1 Payload Contents
                0	rollAngle	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Roll angle
                2	pitchAngle	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Pitch angle
                4	yawAngleMag	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Yaw angle (magnetic north)
                6	xRateCorrected	I2	7*pi/2^16[1260 deg/2^16]	rad/s  [deg/sec]	X angular rate Corrected
                8	yRateCorrected	I2	7*pi/2^16 [1260 deg/2^16]	rad/s  [deg/sec]	Y angular rate Corrected
                10	zRateCorrected	I2	7*pi/2^16 [1260 deg/2^16]	rad/s  [deg/sec]	Z angular rate Corrected
                12	xAccel	I2	20/2^16	g	X accelerometer
                14	yAccel	I2	20/2^16	g	Y accelerometer
                16	zAccel	I2	20/2^16	g	Z accelerometer
                18	xMag	I2	2/2^16	Gauss	X magnetometer
                20	yMag	I2	2/2^16	Gauss	Y magnetometer
                22	zMag	I2	2/2^16	Gauss	Z magnetometer
                24	xRateTemp	I2	200/2^16	Deg C	X rate temperature
                26	timeITOW	U4	1	ms	DMU ITOW (sync to GPS)
                30	BITstatus	U2	-	-	Master BIT and Status'''

            angles = [0 for x in range(3)]
            for i in range(3):
                angle_int16 = (256 * payload[2*i] + payload[2*i+1]) - 65535 if 256 * \
                    payload[2*i] + payload[2*i+1] > 32767 else 256 * payload[2*i] + payload[2*i+1]
                angles[i] = (360.0 * angle_int16) / math.pow(2, 16)

            gyros = [0 for x in range(3)]
            for i in range(3):
                gyro_int16 = (256 * payload[2*i+6] + payload[2*i+7]) - 65535 if 256 * payload[2 *
                                                                                              i+6] + payload[2*i+7] > 32767 else 256 * payload[2*i+6] + payload[2*i+7]
                gyros[i] = (1260 * gyro_int16) / math.pow(2, 16)

            accels = [0 for x in range(3)]
            for i in range(3):
                accel_int16 = (256 * payload[2*i+12] + payload[2*i+13]) - 65535 if 256 * payload[2 *
                                                                                                 i+12] + payload[2*i+13] > 32767 else 256 * payload[2*i+12] + payload[2*i+13]
                accels[i] = (9.80665 * 20 * accel_int16) / math.pow(2, 16)

            mags = [0 for x in range(3)]
            for i in range(3):
                mag_int16 = (256 * payload[2*i+18] + payload[2*i+19]) - 65535 if 256 * payload[2 *
                                                                                               i+18] + payload[2*i+19] > 32767 else 256 * payload[2*i+18] + payload[2*i+19]
                mags[i] = (2 * mag_int16) / math.pow(2, 16)

            temp_int16 = (256 * payload[2*i+24] + payload[2*i+25]) - 65535 if 256 * payload[2 *
                                                                                            i+24] + payload[2*i+25] > 32767 else 256 * payload[2*i+24] + payload[2*i+25]
            temp = (200 * temp_int16) / math.pow(2, 16)

            # Counter Value
            itow = 16777216 * payload[26] + 65536 * \
                payload[27] + 256 * payload[28] + payload[29]

            # BIT Value
            bit = 256 * payload[30] + payload[31]

            if self.data:
                prev_time = self.data['timeITOW']
                if (itow > prev_time):
                    self.elapsed_time_sec += (1.0 /
                                              65535.0) * (itow - prev_time)
                else:
                    self.elapsed_time_sec += (1.0 / 65535.0) * \
                        (65535 - prev_time) + (1.0 / 65535.0) * itow

            data = collections.OrderedDict([('time', self.elapsed_time_sec), ('rollAngle', angles[0]), ('pitchAngle', angles[1]), ('yawAngleMag', angles[2]),
                                            ('xRateCorrected', gyros[0]), ('yRateCorrected', gyros[1]), (
                                                'zRateCorrected', gyros[2]),
                                            ('xAccel', accels[0]), ('yAccel',
                                                                    accels[1]), ('zAccel', accels[2]),
                                            ('xMag', mags[0]), ('yMag', mags[1]), (
                                                'zMag', mags[2]), ('xRateTemp', temp),
                                            ('timeITOW', itow), ('BITstatus', bit)])

            if self.logging == 1 and self.logger is not None:
                self.logger.log(data, self.odr_setting)

            return data

        elif self.packet_type == 'A2':
            '''A2 Payload Contents
                0	rollAngle	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Roll angle
                2	pitchAngle	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Pitch angle
                4	yawAngleMag	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Yaw angle (magnetic north)
                6	xRateCorrected	I2	7*pi/2^16[1260 deg/2^16]	rad/s  [deg/sec]	X angular rate Corrected
                8	yRateCorrected	I2	7*pi/2^16 [1260 deg/2^16]	rad/s  [deg/sec]	Y angular rate Corrected
                10	zRateCorrected	I2	7*pi/2^16 [1260 deg/2^16]	rad/s  [deg/sec]	Z angular rate Corrected
                12	xAccel	  I2	20/2^16	g	X accelerometer
                14	yAccel	  I2	20/2^16	g	Y accelerometer
                16	zAccel	  I2	20/2^16	g	Z accelerometer
                18	xRateTemp I2	200/2^16	Deg.C   X rate temperature 
                20	yRatetemp I2	200/2^16	Deg.C	Y rate temperature 
                22	zRateTemp I2	200/2^16	Deg.C   Z rate temperature 
                24	timeITOW	U4	1	ms	DMU ITOW (sync to GPS)
                28	BITstatus	U2	-	-	Master BIT and Status'''

            angles = [0 for x in range(3)]
            for i in range(3):
                angle_int16 = (256 * payload[2*i] + payload[2*i+1]) - 65535 if 256 * \
                    payload[2*i] + payload[2*i+1] > 32767 else 256 * payload[2*i] + payload[2*i+1]
                angles[i] = (360.0 * angle_int16) / math.pow(2, 16)

            gyros = [0 for x in range(3)]
            for i in range(3):
                gyro_int16 = (256 * payload[2*i+6] + payload[2*i+7]) - 65535 if 256 * payload[2 *
                                                                                              i+6] + payload[2*i+7] > 32767 else 256 * payload[2*i+6] + payload[2*i+7]
                gyros[i] = (1260 * gyro_int16) / math.pow(2, 16)

            accels = [0 for x in range(3)]
            for i in range(3):
                accel_int16 = (256 * payload[2*i+12] + payload[2*i+13]) - 65535 if 256 * payload[2 *
                                                                                                 i+12] + payload[2*i+13] > 32767 else 256 * payload[2*i+12] + payload[2*i+13]
                accels[i] = (9.80665 * 20 * accel_int16) / math.pow(2, 16)

            temp = [0 for x in range(3)]
            for i in range(3):
                temp_int16 = (256 * payload[2*i+18] + payload[2*i+19]) - 65535 if 256 * payload[2 *
                                                                                                i+18] + payload[2*i+19] > 32767 else 256 * payload[2*i+18] + payload[2*i+19]
                temp[i] = (200 * temp_int16) / math.pow(2, 16)

            # Counter Value
            itow = 16777216 * payload[24] + 65536 * \
                payload[25] + 256 * payload[26] + payload[27]

            # BIT Value
            bit = 256 * payload[28] + payload[29]

            if self.data:
                prev_time = self.data['timeITOW']
                if (itow > prev_time):
                    self.elapsed_time_sec += (1.0 /
                                              65535.0) * (itow - prev_time)
                else:
                    self.elapsed_time_sec += (1.0 / 65535.0) * \
                        (65535 - prev_time) + (1.0 / 65535.0) * itow

            data = collections.OrderedDict([('time', self.elapsed_time_sec), ('rollAngle', angles[0]), ('pitchAngle', angles[1]), ('yawAngleMag', angles[2]),
                                            ('xRateCorrected', gyros[0]), ('yRateCorrected', gyros[1]), (
                                                'zRateCorrected', gyros[2]),
                                            ('xAccel', accels[0]), ('yAccel',
                                                                    accels[1]), ('zAccel', accels[2]),
                                            ('xRateTemp', temp[0]), ('yRateTemp',
                                                                     temp[1]), ('zRateTemp', temp[2]),
                                            ('timeITOW', itow), ('BITstatus', bit)])

            if self.logging == 1 and self.logger is not None:
                self.logger.log(data, self.odr_setting)

            return data

        elif self.packet_type == 'A3':
            '''A3 Payload Contents
                0	rollAngle	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Roll angle
                2	pitchAngle	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Pitch angle
                4	yawAngleMag	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Yaw angle (magnetic north)
                6	xRateScaled     I2	7*pi/2^16[1260 deg/2^16]	rad/s  [deg/sec]	X angular rate Corrected
                8	yRateScaled     I2	7*pi/2^16 [1260 deg/2^16]	rad/s  [deg/sec]	Y angular rate Corrected
                10	zRateScaled     I2	7*pi/2^16 [1260 deg/2^16]	rad/s  [deg/sec]	Z angular rate Corrected
                12	xAccel	  I2	20/2^16	g	X accelerometer
                14	yAccel	  I2	20/2^16	g	Y accelerometer
                16	zAccel	  I2	20/2^16	g	Z accelerometer
                18	xRateTemp I2	200/2^16	Deg.C   X rate temperature 
                20	yRatetemp I2	200/2^16	Deg.C	Y rate temperature 
                22	zRateTemp I2	200/2^16	Deg.C   Z rate temperature 
                24	timeITOW	U4	1	ms	DMU ITOW (sync to GPS)
                28	BITstatus	U2	-	-	Master BIT and Status'''

            angles = [0 for x in range(3)]
            for i in range(3):
                angle_int16 = (256 * payload[2*i] + payload[2*i+1]) - 65535 if 256 * \
                    payload[2*i] + payload[2*i+1] > 32767 else 256 * payload[2*i] + payload[2*i+1]
                angles[i] = (360.0 * angle_int16) / math.pow(2, 16)

            gyros = [0 for x in range(3)]
            for i in range(3):
                gyro_int16 = (256 * payload[2*i+6] + payload[2*i+7]) - 65535 if 256 * payload[2 *
                                                                                              i+6] + payload[2*i+7] > 32767 else 256 * payload[2*i+6] + payload[2*i+7]
                gyros[i] = (1260 * gyro_int16) / math.pow(2, 16)

            accels = [0 for x in range(3)]
            for i in range(3):
                accel_int16 = (256 * payload[2*i+12] + payload[2*i+13]) - 65535 if 256 * payload[2 *
                                                                                                 i+12] + payload[2*i+13] > 32767 else 256 * payload[2*i+12] + payload[2*i+13]
                accels[i] = (9.80665 * 20 * accel_int16) / math.pow(2, 16)

            temp = [0 for x in range(3)]
            for i in range(3):
                temp_int16 = (256 * payload[2*i+18] + payload[2*i+19]) - 65535 if 256 * payload[2 *
                                                                                                i+18] + payload[2*i+19] > 32767 else 256 * payload[2*i+18] + payload[2*i+19]
                temp[i] = (200 * temp_int16) / math.pow(2, 16)

            # Counter Value
            itow = 16777216 * payload[24] + 65536 * \
                payload[25] + 256 * payload[26] + payload[27]

            # BIT Value
            bit = 256 * payload[28] + payload[29]

            data = collections.OrderedDict([('rollAngle', angles[0]), ('pitchAngle', angles[1]), ('yawAngleMag', angles[2]),
                                            ('xRateScaled', gyros[0]), ('yRateScaled', gyros[1]), (
                                                'zRateScaled', gyros[2]),
                                            ('xAccel', accels[0]), ('yAccel',
                                                                    accels[1]), ('zAccel', accels[2]),
                                            ('xRateTemp', temp[0]), ('yRateTemp',
                                                                     temp[1]), ('zRateTemp', temp[2]),
                                            ('timeITOW', itow), ('BITstatus', bit)])

            if self.logging == 1 and self.logger is not None:
                self.logger.log(data, self.odr_setting)

            return data

        elif self.packet_type == 'N0':
            '''N0 Payload Contents
                0	rollAngle	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Roll angle
                2	pitchAngle	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Pitch angle
                4	yawAngleMag	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Yaw angle (magnetic north)
                6	xRateCorrected  I2	7*pi/2^16[1260 deg/2^16]	rad/s  [deg/sec]	X angular rate Corrected
                8	yRateCorrected  I2	7*pi/2^16 [1260 deg/2^16]	rad/s  [deg/sec]	Y angular rate Corrected
                10	zRateCorrected  I2	7*pi/2^16 [1260 deg/2^16]	rad/s  [deg/sec]	Z angular rate Corrected
                12	nVel            I2	512/2^16	m/s        North velocity	
                14	eVel            I2	512/2^16	m/s	   East Velocity 
                16	dVel            I2	512/2^16	m/s	   Down velocity 
                18	longiTude       I4	2*pi/2^32	Radians    Longitude 
                22	latiTude        I4	2*pi/2^32     	Radians    Latitude 
                26	altiTude        I2	2^14/2^16	m          GPS altitude 
                28	iTOW	        U2	truncated	ms	   ITOW (lower 2 bytes)
                30	BITstatus	U2	-	        -	   Master BIT and Status'''

            angles = [0 for x in range(3)]
            for i in range(3):
                angle_int16 = (256 * payload[2*i] + payload[2*i+1]) - 65535 if 256 * \
                    payload[2*i] + payload[2*i+1] > 32767 else 256 * payload[2*i] + payload[2*i+1]
                angles[i] = (360.0 * angle_int16) / math.pow(2, 16)

            gyros = [0 for x in range(3)]
            for i in range(3):
                gyro_int16 = (256 * payload[2*i+6] + payload[2*i+7]) - 65535 if 256 * payload[2 *
                                                                                              i+6] + payload[2*i+7] > 32767 else 256 * payload[2*i+6] + payload[2*i+7]
                gyros[i] = (1260 * gyro_int16) / math.pow(2, 16)

            vel = [0 for x in range(3)]
            for i in range(3):
                vel_int16 = (256 * payload[2*i+12] + payload[2*i+13]) - 65535 if 256 * payload[2 *
                                                                                               i+12] + payload[2*i+13] > 32767 else 256 * payload[2*i+12] + payload[2*i+13]
                vel[i] = (512 * vel_int16) / math.pow(2, 16)

            tude = [0 for x in range(3)]
            for i in range(2):
                tude_int32 = (16777216 * payload[2*i+18] + 65536 * payload[2*i+19] + 256 * payload[2*i+20] + payload[21]) - 2147483648 if 16777216 * payload[2*i+18] + 65536 * \
                    payload[2*i+19] + 256 * payload[2*i+20] + payload[21] > 2147483647 else 16777216 * payload[2*i+18] + 65536 * payload[2*i+19] + 256 * payload[2*i+20] + payload[21]
                tude[i] = (360.0 * tude_int32) / math.pow(2, 32)

            # altitude
            tude_int16 = 256 * payload[26] + payload[27]
            tude[2] = (16384 * tude_int16) / math.pow(2, 16)

            # Counter Value
            itow = 256 * payload[28] + payload[29]

            # BIT Value
            bit = 256 * payload[30] + payload[31]

            data = collections.OrderedDict([('rollAngle', angles[0]), ('pitchAngle', angles[1]), ('yawAngleMag', angles[2]),
                                            ('xRateCorrected', gyros[0]), ('yRateCorrected', gyros[1]), (
                                                'zRateCOrrected', gyros[2]),
                                            ('nVel', vel[0]), ('eVel',
                                                               vel[1]), ('dVel', vel[2]),
                                            ('longitude', tude[0]), ('latitude',
                                                                     tude[1]), ('altitude', tude[2]),
                                            ('iTOW', itow), ('BITstatus', bit)])

            if self.logging == 1 and self.logger is not None:
                self.logger.log(data, self.odr_setting)

            return data

        elif self.packet_type == 'N1':
            '''N0 Payload Contents
                0	rollAngle	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Roll angle
                2	pitchAngle	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Pitch angle
                4	yawAngleMag	I2	2*pi/2^16 [360 deg/2^16]	Radians [deg]	Yaw angle (magnetic north)
                6	xRateCorrected  I2	7*pi/2^16[1260 deg/2^16]	rad/s  [deg/sec]	X angular rate Corrected
                8	yRateCorrected  I2	7*pi/2^16 [1260 deg/2^16]	rad/s  [deg/sec]	Y angular rate Corrected
                10	zRateCorrected  I2	7*pi/2^16 [1260 deg/2^16]	rad/s  [deg/sec]	Z angular rate Corrected
                12	xAccel	        I2	20/2^16	                        g	                X accelerometer
                14	yAccel	        I2	20/2^16	                        g	                Y accelerometer
                16	zAccel	        I2	20/2^16	                        g	                Z accelerometer
                18	nVel            I2	512/2^16	m/s        North velocity	
                20	eVel            I2	512/2^16	m/s	   East Velocity 
                22	dVel            I2	512/2^16	m/s	   Down velocity 
                24	longiTude       I4	2*pi/2^32	Radians    Longitude 
                28	latiTude        I4	2*pi/2^32     	Radians    Latitude 
                32	altiTude        I2	2^14/2^16	m          GPS altitude 
                34	xRateTemp	I2	200/2^16	Deg C	X rate temperature
                36	iTOW	        U2	truncated	ms	   ITOW (lower 2 bytes)'''

            angles = [0 for x in range(3)]
            for i in range(3):
                angle_int16 = (256 * payload[2*i] + payload[2*i+1]) - 65535 if 256 * \
                    payload[2*i] + payload[2*i+1] > 32767 else 256 * payload[2*i] + payload[2*i+1]
                angles[i] = (360.0 * angle_int16) / math.pow(2, 16)

            gyros = [0 for x in range(3)]
            for i in range(3):
                gyro_int16 = (256 * payload[2*i+6] + payload[2*i+7]) - 65535 if 256 * payload[2 *
                                                                                              i+6] + payload[2*i+7] > 32767 else 256 * payload[2*i+6] + payload[2*i+7]
                gyros[i] = (1260 * gyro_int16) / math.pow(2, 16)

            accels = [0 for x in range(3)]
            for i in range(3):
                accel_int16 = (256 * payload[2*i+12] + payload[2*i+13]) - 65535 if 256 * payload[2 *
                                                                                                 i+12] + payload[2*i+13] > 32767 else 256 * payload[2*i+12] + payload[2*i+13]
                accels[i] = (9.80665 * 20 * accel_int16) / math.pow(2, 16)
            vel = [0 for x in range(3)]
            for i in range(3):
                vel_int16 = (256 * payload[2*i+18] + payload[2*i+19]) - 65535 if 256 * payload[2 *
                                                                                               i+18] + payload[2*i+19] > 32767 else 256 * payload[2*i+18] + payload[2*i+19]
                vel[i] = (512 * vel_int16) / math.pow(2, 16)

            tude = [0 for x in range(3)]
            for i in range(2):
                tude_int32 = (16777216 * payload[2*i+24] + 65536 * payload[2*i+25] + 256 * payload[2*i+26] + payload[27]) - 2147483648 if 16777216 * payload[2*i+24] + 65536 * \
                    payload[2*i+25] + 256 * payload[2*i+26] + payload[27] > 2147483647 else 16777216 * payload[2*i+24] + 65536 * payload[2*i+25] + 256 * payload[2*i+26] + payload[27]
                tude[i] = (360.0 * tude_int32) / math.pow(2, 32)

            # altitude
            tude_int16 = 256 * payload[32] + payload[33]
            tude[2] = (16384 * tude_int16) / math.pow(2, 16)

            temp_int16 = (256 * payload[2*i+34] + payload[2*i+35]) - 65535 if 256 * payload[2 *
                                                                                            i+34] + payload[2*i+35] > 32767 else 256 * payload[2*i+34] + payload[2*i+35]
            temp = (200 * temp_int16) / math.pow(2, 16)

            # Counter Value
            itow = 256 * payload[28] + payload[29]

            data = collections.OrderedDict([('rollAngle', angles[0]), ('pitchAngle', angles[1]), ('yawAngleMag', angles[2]),
                                            ('xRateCorrected', gyros[0]), ('yRateCorrected', gyros[1]), (
                                                'zRateCOrrected', gyros[2]),
                                            ('xAccel', accels[0]), ('yAccel',
                                                                    accels[1]), ('zAccel', accels[2]),
                                            ('nVel', vel[0]), ('eVel',
                                                               vel[1]), ('dVel', vel[2]),
                                            ('longitude', tude[0]), ('latitude',
                                                                     tude[1]), ('altitude', tude[2]),
                                            ('xRateTemp', temp), ('iTOW', itow)])

            if self.logging == 1 and self.logger is not None:
                self.logger.log(data, self.odr_setting)

            return data

        elif self.packet_type == 'T0':
            '''T0 Payload Contents
                Byte Offset	Name	 Format	Scaling	Units	Description
                0	BitStatus        U2	                Master BIT and Status Field 
                2	hardwareBIT      U2	                Hardware BIT Field 
                4	hardwarePowerBIT U2	                Hardware Power BIT Field 
                6	hardwareEnvironmentalBIT U2             Hardware Environmental BIT Field	
                8	comBit           U2                     communication BIT Field
                10	comSerialABIT    U2	                Communication Serial A BIT Field
                12      comSerialBBIT    U2                     Communication Serial B BIT Field	
                14	softwareBIT      U2                     Software BIT Filed	
                16	softwareAlgorithmBIT U2	                Software Algorithm BIT Field
                18	softwareDataBIT  U2	                Software Data BIT Field
                20	hardwareStatus   U2	                Hardware Status Field
                22	comStatus        U2	                Communication Status Field
                24	softwareStatus   U2	                Software Status Field
                26	sensorStatus     U2                     Sensor Status Field'''

            # BIT Status
            bitStatus = 256 * payload[0] + payload[1]

            # hardware bit
            hardwareBit = 256 * payload[2] + payload[3]

            # hardware power bit
            hardwarePowerBit = 256 * payload[4] + payload[5]

            # hardware environmental bit
            hardwareEnvironmentalBit = 256 * payload[6] + payload[7]

            # com bit
            comBit = 256 * payload[8] + payload[9]

            # com serial A bit
            comSerialABit = 256 * payload[10] + payload[11]

            # com serial B bit
            comSerialBBit = 256 * payload[12] + payload[13]

            # software bit
            softwareBit = 256 * payload[14] + payload[15]

            # software algorithm bit
            softwareAlgBit = 256 * payload[16] + payload[17]

            # software data bit
            softwareDataBit = 256 * payload[18] + payload[19]

            # hardware status
            hardwareStatus = 256 * payload[20] + payload[21]

            # com status
            comStatus = 256 * payload[22] + payload[23]

            # software status
            softwareStatus = 256 * payload[24] + payload[25]

            # sensor status
            sensorStatus = 256 * payload[26] + payload[27]

            data = collections.OrderedDict([('bitStatus', bitStatus), ('hardware bit', hardwareBit), ('hardwarePowerBit', hardwarePowerBit),
                                            ('hardwareEnvironmentalBit', hardwareEnvironmentalBit), (
                                                'comBit', comBit), ('com Serial A Bit', comSerialABit),
                                            ('com Serial B Bit', comSerialBBit), ('software bit',
                                                                                  softwareBit), ('software algorithm bit', softwareAlgBit),
                                            ('software data bit', softwareDataBit), ('hardware status',
                                                                                     hardwareStatus), ('com status', comStatus),
                                            ('software status', softwareStatus), ('sensor status', sensorStatus)])

            if self.logging == 1 and self.logger is not None:
                self.logger.log(data, self.odr_setting)

            return data

        elif self.packet_type == 'SF':
            n = payload[0]
            for i in range(n):
                if ws == False:
                    print('Set Field: 0x{0:02X}'.format(
                        payload[i*2+1]) + '{0:02X}'.format(payload[i*2+2]))
                else:
                    return 1
        elif self.packet_type == 'WF':
            n = payload[0]
            data = [0] * n  # empty array
            for i in range(n):
                if ws == False:
                    print('Write Field: 0x{0:02X}'.format(
                        payload[i*2+1]) + '{0:02X}'.format(payload[i*2+2]))
                else:
                    return 1
        elif self.packet_type == 'RF':
            n = payload[0]
            data = [0] * n  # empty array
            for i in range(n):
                if ws == False:
                    print(('Read Field: 0x{0:02X}'.format(payload[i*4+1]) + '{0:02X}'.format(payload[i*4+2])
                           + ' set to: 0x{0:02X}{1:02X}'.format(payload[i*4+3], payload[i*4+4])
                           + ' ({0:1c}{1:1c})'.format(payload[i*4+3], payload[i*4+4])))
                else:
                    data[i] = [256 * payload[i*4+1] + payload[i*4+2],
                               256 * payload[i*4+3] + payload[i*4+4]]
            return data

        elif self.packet_type == 'GF':
            n = payload[0]
            data = [0] * n  # empty array
            for i in range(n):
                # remap about odr because unit was forced to quiet mode during GF read
                if ((256 * payload[i*4+1] + payload[i*4+2]) == 1):
                    payload[i*4+3] = 0
                    payload[i*4+4] = self.odr_setting
                if ws == False:
                    print(('Get Field: 0x{0:02X}'.format(payload[i*4+1]) + '{0:02X}'.format(payload[i*4+2])
                           + ' set to: 0x{0:02X}{1:02X}'.format(payload[i*4+3], payload[i*4+4])
                           + ' ({0:1c}{1:1c})'.format(payload[i*4+3], payload[i*4+4])))
                else:
                    data[i] = [256 * payload[i*4+1] + payload[i*4+2],
                               256 * payload[i*4+3] + payload[i*4+4]]
            return data

        elif self.packet_type == 'VR':
            '''this packet type is obsolete'''
            print('Version String: {0}.{1}.{2}.{3}.{4}'.format(*payload))
        elif self.packet_type == 'ID':
            sn = int(payload[0] << 24) + int(payload[1] << 16) + \
                int(payload[2] << 8) + int(payload[3])
            print('ID String: {0} {1}'.format(sn, payload[4:].decode()))
            return '{0} {1}'.format(sn, payload[4:].decode())

    def calc_crc(self, payload):
        '''Calculates CRC per 380 manual
        '''
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

    def open(self, port, baud):
        try:
            self.ser = serial.Serial(port, baud, timeout=0.1)
        except (OSError, serial.SerialException):
            print('serial port open exception' + port)

    def close(self):
        self.ser.close()

    def read(self, n):
        bytes = []
        try:
            bytes = self.ser.read(n)
        except:
            # except (OSError, serial.SerialException):
            self.disconnect()    # sets connected to 0, and other related parameters to initial values
            print('serial exception read')
            self.connect()
        if bytes and len(bytes):
            return bytearray(bytes)
        else:
            print('empty read')
            return bytearray(bytes)

    def write(self, n):
        try:
            self.ser.write(n)
        except:
            # except (OSError, serial.SerialException):
            self.disconnect()   # sets connected to 0, and other related parameters to initial values
            print('serial exception write')
            self.connect()

    def reset_buffer(self):
        try:
            self.ser.reset_input_buffer()
        except:
            # except (OSError, serial.SerialException):
            self.disconnect()   # sets connected to 0, and other related parameters to initial values
            print('serial exception reset')
            self.connect()


if __name__ == "__main__":
    unit = OpenIMU()
    unit.find_device()
    print('file name ' + unit.filename)
    #unit.start_bootloader()
    if unit.connected != 0:
        if unit.boot != 1:
            unit.close()
            unit.open(unit.port, 57600)
        unit.upgrade_fw(unit.filename)
