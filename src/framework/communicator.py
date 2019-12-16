import sys
import os
import socket
import select
import time
import datetime
import json
import glob
import serial
import serial.tools.list_ports
from ..devices import DeviceManager
import threading
if sys.version_info[0] > 2:
    from queue import Queue
else:
    from Queue import Queue


class CommunicatorFactory:
    @staticmethod
    def create(type, options):
        if type == 'uart':
            return SerialPort(options)
        elif type == 'spi':
            return SPI(options)
        else:
            raise Exception('no matched communicator')


class Communicator(object):
    '''
    '''

    def __init__(self):
        # use to store some configuration files.
        self.setting_folder = os.path.join(os.getcwd(), r'setting')
        self.connection_file = os.path.join(
            self.setting_folder, 'connection.json')
        self.read_size = 0
        self.device = None
        pass

    def find_device(self, callback):
        callback()
        pass

    def open(self):
        pass

    def close(self):
        pass

    def write(self, data, is_flush=False):
        pass

    def read(self, size):
        pass

    def confirm_device(self):
        self.device = DeviceManager.ping(self)


class SerialPort(Communicator):
    def __init__(self, options=None):
        super(SerialPort, self).__init__()
        self.type = 'uart'
        self.serial_port = None  # the active UART
        self.port = None
        self.baud = None
        self.read_size = 100
        # self.baudrateList = [115200]  # for test
        self.baudrateList = [38400, 57600, 115200,
                             230400, 460800]  # default baudrate list
        if options and options.b and len(options.b) > 0:
            self.baudrateList = options.b

    def find_device(self, callback):
        ''' Finds active ports and then autobauds units
        '''
        self.device = None
        while self.device is None:
            if self.try_last_port():
                break
            else:
                num_ports = self.find_ports()
                self.autobaud(num_ports)
            time.sleep(0.5)
        callback(self.device)

    def find_ports(self):
        # portList = list(serial.tools.list_ports.comports())
        # filterPortList = filter(
        #     lambda item: item.device.find('Bluetooth') == -1, portList)
        # ports = [p.device for p in filterPortList]
        # ports.sort()
        # print("\nsystem ports detected", ports)

        portList = list(serial.tools.list_ports.comports())
        ports = [p.device for p in portList]

        result = []
        for port in ports:
            if "Bluetooth" in port:
                continue
            else:
                print('Check if is a used port ' + port)
                s = None
                try:
                    s = serial.Serial(port)
                    if s:
                        s.close()
                        result.append(port)
                except Exception as e:
                    print(e)
                    pass
        return result

        # return ports

    def autobaud(self, ports):
        '''Autobauds unit - first check for stream_mode / continuous data, then check by polling unit
           Converts resets polled unit (temporarily) to 100Hz ODR
           :returns:
                true when successful
        '''
        print('start to connect serial port')
        bandListFromOptions = self.baudrateList

        for port in ports:
            for baud in bandListFromOptions:
                print("try {0}:{1}".format(port, baud))
                self.open(port, baud)
                if self.serial_port is not None:
                    self.confirm_device()

                    if self.device is None:
                        self.close()
                        continue
                    else:
                        self.save_last_port()
                        break
        return False

    def try_last_port(self):
        '''try to open serial port based on the port and baud read from connection.json.
           try to find frame header in serial data.
           returns: True if find header
                    False if not find header.
        '''
        print('try to use last connected port')
        connection = None
        try:
            with open(self.connection_file) as json_data:
                connection = json.load(json_data)

            if connection:
                self.open_serial_port(
                    port=connection['port'], baud=connection['baud'], timeout=0.005)
                if self.serial_port is not None:
                    self.confirm_device()
                    if self.device is None:
                        self.close()
                        return False
                    else:
                        self.save_last_port()
                        # Assume max_len of a frame is less than 300 bytes.
                        return True
                else:
                    return False
        except Exception as e:
            print(e)
            return False

    def save_last_port(self):
        if not os.path.exists(self.setting_folder):
            try:
                os.mkdir(self.setting_folder)
            except:
                return

        connection = {"port": self.serial_port.port,
                      "baud": self.serial_port.baudrate}
        try:
            with open(self.connection_file, 'w') as outfile:
                json.dump(connection, outfile)
        except:
            pass

    def open_serial_port(self, port=None, baud=115200, timeout=0.1):
        ''' open serial port
            returns: true when successful
        '''
        try:
            self.serial_port = serial.Serial(port, baud, timeout=timeout)
            return True
        except Exception as e:
            # TODO: compatible for py 2.x
            print('{0} : {1} open failed'.format(port, baud))
            if self.serial_port is not None:
                if self.serial_port.isOpen():
                    self.serial_port.close()

            self.serial_port = None
            return False

    def close_serial_port(self):
        '''close serial port
        '''
        if self.serial_port is not None:
            if self.serial_port.isOpen():
                self.serial_port.close()

    def write(self, data, is_flush=False):
        '''
        write the bytes data to the port

        return:
                length of data sent via serial port.
                False: Exception when sending data, eg. serial port hasn't been opened.
        '''
        try:
            len_of_data = self.serial_port.write(data)
            if is_flush:
                self.serial_port.flush()
            return len_of_data
        except Exception as e:
            # print(e)
            raise

    def read(self, size=100):
        '''
        read size bytes from the serial port.
        parameters: size - number of bytes to read.
        returns: bytes read from the port.
        return type: bytes
        '''
        try:
            return self.serial_port.read(size)
        except serial.SerialException:
            print(
                'Serial Exception! Please check the serial port connector is stable or not.')
            raise
        except Exception as e:
            # print(e)
            raise

    def open(self, port=False, baud=57600):
        return self.open_serial_port(port, baud, timeout=0.005)

    def close(self):
        return self.close_serial_port()

    def reset_buffer(self):
        self.serial_port.flushInput()
        self.serial_port.flushOutput()
        pass


class SPI(Communicator):
    def __init__(self):
        self.type = 'spi'
        pass
