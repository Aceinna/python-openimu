"""
Communicator
"""
import sys
import os
import time
import json
import serial
import serial.tools.list_ports
import threading
from ..devices import DeviceManager
from .constants import BAUDRATE_LIST
from .context import APP_CONTEXT
from .utils.resource import (
    get_executor_path
)
if sys.version_info[0] > 2:
    from queue import Queue
else:
    from Queue import Queue

import inspect
import ctypes


class CommunicatorFactory:
    '''
    Communicator Factory
    '''
    @staticmethod
    def create(method, options):
        '''
        Initial communicator instance
        '''
        if method == 'uart':
            return SerialPort(options)
        elif method == 'spi':
            return SPI(options)
        else:
            raise Exception('no matched communicator')


class Communicator(object):
    '''Communicator base
    '''

    def __init__(self):
        executor_path = get_executor_path()
        setting_folder_name = 'setting'
        self.setting_folder_path = os.path.join(
            executor_path, setting_folder_name)
        self.connection_file_path = os.path.join(
            self.setting_folder_path, 'connection.json')
        self.read_size = 0
        self.device = None
        self.threadList = []

    def find_device(self, callback):
        '''
        find device, then invoke callback
        '''
        callback()

    def open(self):
        '''
        open
        '''

    def close(self):
        '''
        close
        '''

    def write(self, data, is_flush=False):
        '''
        write
        '''

    def read(self, size):
        '''
        read
        '''

    def confirm_device(self, *args):
        '''
        validate the connected device
        '''
        device = DeviceManager.ping_with_port(self, *args)
        if device != None and self.device == None:
            self.device = device
            return True
        return False

class StoppableThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class SerialPort(Communicator):
    '''
    Serial Port
    '''

    def __init__(self, options=None):
        super(SerialPort, self).__init__()
        self.type = 'uart'
        self.serial_port = None  # the active UART
        self.port = None
        self.baud = None
        self.read_size = 100
        self.baudrate_assigned = False
        # self.baudrateList = [115200]  # for test
        self.baudrate_list = BAUDRATE_LIST  # default baudrate list
        self.com_port = None
        self.com_port_assigned = False
        self.filter_device_type = None
        self.filter_device_type_assigned = False

        if options and options.baudrate != 'auto':
            self.baudrate_list = [options.baudrate]
            self.baudrate_assigned = True
        if options and options.com_port != 'auto':
            self.com_port = options.com_port
            self.com_port_assigned = True
        if options and options.device_type != 'auto':
            self.filter_device_type = options.device_type
            self.filter_device_type_assigned = True

    def find_device(self, callback):
        ''' Finds active ports and then autobauds units
        '''
        self.device = None
        if self.com_port_assigned:
            # find device by assigned port
            self.autobaud([self.com_port])
            if self.device is None:
                raise Exception(
                    '\nCannot connect the device with serial port: {0}. \
                    \nProbable reason: \
                    \n1. The serial port is invalid. \
                    \n2. The device response incorrect format of device info and app info.'.format(self.com_port))
        else:
            while self.device is None:
                if self.try_last_port():
                    break

                num_ports = self.find_ports()
                self.autobaud(num_ports)
                time.sleep(0.5)
        callback(self.device)

    def find_ports(self):
        '''
        Find available ports
        '''
        port_list = list(serial.tools.list_ports.comports())
        ports = [p.device for p in port_list]

        result = []

        for port in ports:
            if "Bluetooth" in port:
                continue
            else:
                # print('Check if is a used port ' + port)
                ser = None
                try:
                    ser = serial.Serial(port, exclusive=True)
                    if ser:
                        ser.close()
                        result.append(port)
                except Exception as ex:
                    APP_CONTEXT.get_logger().logger.debug(
                        'actual port exception %s', ex)
                    APP_CONTEXT.get_logger().logger.info(
                        'port:%s is in use', port)
        return result

    def thread_for_ping(self, ports):
        # for port in ports:
        serial_port = None
        for port in ports:
            for baud in self.baudrate_list:
                # print("try {0}:{1}".format(port, baud))
                APP_CONTEXT.get_logger().logger.info(
                    "try {0}:{1}".format(port, baud))
                try:
                    serial_port = serial.Serial(
                        port, baud, timeout=0.1)
                except Exception as ex:
                    APP_CONTEXT.get_logger().logger.info(
                        '{0} : {1} open failed'.format(port, baud))
                    if serial_port is not None:
                        if serial_port.isOpen():
                            serial_port.close()
                    for td in self.threadList:
                        if td.name == ports[0]:
                            td.stop()
                    return False

                if serial_port is not None and serial_port.isOpen():
                    ret = self.confirm_device(port, serial_port, self.filter_device_type)

                    if not ret:
                        serial_port.close()
                        time.sleep(0.1)
                        for td in self.threadList:
                            if td.name == ports[0]:
                                if td.stopped():
                                    return False
                                break
                        continue
                    else:
                        self.serial_port = serial_port
                        self.save_last_port()
                        # Assume max_len of a frame is less than 300 bytes.
                        for td in self.threadList:
                            td.stop()
                        return True
        for td in self.threadList:
            if td.name == ports[0]:
                td.stop()
        return False

    def autobaud(self, ports):
        '''Autobauds unit - first check for stream_mode/continuous data, then check by polling unit
           Converts resets polled unit (temporarily) to 100Hz ODR
           :returns:
                true when successful
        '''
        APP_CONTEXT.get_logger().logger.info('start to connect serial port')

        # print('find ports: {0}'.format(ports))
        DeviceManager.reset_ping()
        thread_num = (len(ports) if (len(ports) < 4) else 4)
        ports_list = [[] for i in range(thread_num)]
        for i, port in enumerate(ports):
            ports_list[i%thread_num].append(port)

        for i in range(thread_num):
            # print('{0} {1}'.format(i, ports_list[i]))
            t = StoppableThread(
                target=self.thread_for_ping, name=ports_list[i][0], args=(ports_list[i],))
            t.start()

            self.threadList.append(t)

        while self.device is None:
            is_threads_stop = True
            for td in self.threadList:
                if not td.stopped():
                    is_threads_stop = False
                    break
            if is_threads_stop:
                break

        for td in self.threadList:
            td.join()
        self.threadList.clear()

    def try_last_port(self):
        '''try to open serial port based on the port and baud read from connection.json.
           try to find frame header in serial data.
           returns: True if find header
                    False if not find header.
        '''
        connection = None
        try:
            if not os.path.isfile(self.connection_file_path):
                return False

            with open(self.connection_file_path) as json_data:
                connection = json.load(json_data)
            connection['baud'] = self.baudrate_list[0] if self.baudrate_assigned \
                else connection['baud']
            APP_CONTEXT.get_logger().logger.info('try to use last connected port {} {}'.format(
                connection['port'], connection['baud']))
            if connection:
                self.open_serial_port(
                    port=connection['port'], baud=connection['baud'], timeout=0.1)
                if self.serial_port is not None:
                    ret = self.confirm_device(connection['port'], self.serial_port, self.filter_device_type)
                    if not ret:
                        self.close()
                        return False
                    else:
                        self.save_last_port()
                        # Assume max_len of a frame is less than 300 bytes.
                        return True
                else:
                    return False
        except Exception as ex:
            print(ex)
            return False

    def save_last_port(self):
        '''
        save connected port info
        '''

        if not os.path.exists(self.setting_folder_path):
            try:
                os.mkdir(self.setting_folder_path)
            except:
                return

        connection = {"port": self.serial_port.port,
                      "baud": self.serial_port.baudrate}
        try:
            with open(self.connection_file_path, 'w') as outfile:
                json.dump(connection, outfile)
        except:
            pass

    def open_serial_port(self, port=None, baud=115200, timeout=0.1):
        ''' open serial port
            returns: true when successful
        '''
        try:
            self.serial_port = serial.Serial(
                port, baud, timeout=timeout, exclusive=True)
            return True
        except Exception as ex:
            APP_CONTEXT.get_logger().logger.info(
                '{0} : {1} open failed'.format(port, baud))
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
        except Exception as ex:
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
        except Exception as ex:
            # print(e)
            raise

    def open(self, port=False, baud=57600):
        return self.open_serial_port(port, baud, timeout=0.1)

    def close(self):
        return self.close_serial_port()

    def reset_buffer(self):
        '''
        reset buffer
        '''
        self.serial_port.flushInput()
        self.serial_port.flushOutput()


class SPI(Communicator):
    '''SPI'''

    def __init__(self, options=None):
        super().__init__()
        self.type = 'spi'
