import os
import time
import json
import threading
import serial
import serial.tools.list_ports
from ..constants import (BAUDRATE_LIST, INTERFACES)
from ..context import APP_CONTEXT
from ..communicator import Communicator


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
    _status = 'idle'
    _is_close = False
    _available_ports = []
    _tried = 0
    _find_options = None

    def __init__(self, options=None):
        super(SerialPort, self).__init__()
        self.type = INTERFACES.UART
        self.serial_port = None  # the active UART
        self.port = None
        self.baud = None
        self.read_size = 100
        self.baudrate_assigned = False
        self.baudrate_list = BAUDRATE_LIST  # default baudrate list
        self.com_port = None
        self.com_port_assigned = False
        self.filter_device_type = None
        self.filter_device_type_assigned = False
        self._connection_history = None

        if options and options.baudrate != 'auto':
            self.baudrate_list = [options.baudrate]
            self.baudrate_assigned = True
        if options and options.com_port != 'auto':
            self.com_port = options.com_port
            self.com_port_assigned = True
        if options and options.device_type != 'auto':
            self.filter_device_type = options.device_type
            self.filter_device_type_assigned = True

    def pause_find(self):
        self._status = 'pause'

    def resume_find(self):
        self._status = 'idle'

    def list_ports(self):
        return self._available_ports

    def set_find_options(self, options):
        self._find_options = options

    def find_device(self, callback, retries=0, not_found_handler=None):
        ''' Finds active ports and then autobauds units
        '''
        self.device = None
        self._is_close = False
        self._available_ports = []
        self._status = 'idle'
        self._tried = 0

        if self.com_port_assigned:
            # find device by assigned port
            self.autobaud([self.com_port])
            if self.device is None:
                raise Exception(
                    '\nCannot connect the device with serial port: {0}. \
                    \nProbable reason: \
                    \n1. The serial port is invalid. \
                    \n2. The device response incorrect format of device info and app info.'
                    .format(self.com_port))
        else:
            while self.device is None:
                if self._is_close:
                    return

                if self._status == 'pause':
                    time.sleep(0.5)
                    continue

                if self._find_options:
                    current_filter_device_type = self.filter_device_type
                    current_filter_device_type_assigned = self.filter_device_type_assigned
                    current_baudrate_list = self.baudrate_list
                    current_baudrate_assigned = self.baudrate_assigned
                    ports = self._available_ports

                    if 'device_type' in self._find_options:
                        self.filter_device_type = self._find_options[
                            'device_type']
                        self.filter_device_type_assigned = True

                    if 'baudrate' in self._find_options:
                        self.baudrate_list = [self._find_options['baudrate']]
                        self.baudrate_assigned = True

                    if 'com_port' in self._find_options:
                        ports = [self._find_options['com_port']]

                    self.autobaud(ports)

                    if retries == 0:
                        self._find_options = None

                    self.filter_device_type = current_filter_device_type
                    self.filter_device_type_assigned = current_filter_device_type_assigned
                    self.baudrate_list = current_baudrate_list
                    self.baudrate_assigned = current_baudrate_assigned

                else:
                    if self.try_last_port():
                        break
                    self._available_ports = self.find_ports()
                    self.autobaud(self._available_ports)

                self._tried += 1

                if retries > 0 and self._tried >= retries:
                    if self._find_options:
                        self._find_options = None

                    if not self.device and not_found_handler:
                        not_found_handler()
                    return

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
            if self.try_from_history(port):
                for td in self.threadList:
                    td.stop()
                return True

            for baud in self.baudrate_list:
                APP_CONTEXT.get_logger().logger.info(
                    "try {0}:{1}".format(port, baud))
                try:
                    serial_port = serial.Serial(port, baud, timeout=0.1)
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
                    ret = self.confirm_device(
                        serial_port, self.filter_device_type)
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
                        self.update_connection_history({
                            'port': serial_port.port,
                            'baud': serial_port.baudrate,
                            'device_type': self.device.type
                        })

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
        thread_num = (len(ports) if (len(ports) < 4) else 4)
        ports_list = [[] for i in range(thread_num)]
        for i, port in enumerate(ports):
            ports_list[i % thread_num].append(port)
        for i in range(thread_num):
            t = StoppableThread(target=self.thread_for_ping,
                                name=ports_list[i][0],
                                args=(ports_list[i], ))
            t.start()

            self.threadList.append(t)

        # make sure every thread is stopped
        while self.device is None:
            if self._is_close:
                return

            if self._status == 'pause':
                return

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
        parsed_json = None
        try:
            if not os.path.isfile(self.connection_file_path):
                return False

            # if self._connection_history is None:
            with open(self.connection_file_path) as json_data:
                parsed_json = json.load(json_data)

            if not self._is_valid_connection_history(parsed_json):
                return False

            self._connection_history = parsed_json

            last_connection_index = self._connection_history['last']
            last_connection = self._connection_history['history'][last_connection_index]

            if last_connection:
                port = last_connection['port']
                baud_rate = self.baudrate_list[0] if self.baudrate_assigned \
                    else last_connection['baud']
                device_type = self.filter_device_type if self.filter_device_type_assigned \
                    else last_connection['device_type']

                APP_CONTEXT.get_logger().logger.info(
                    'try to use last connected port {} {}'.format(port, baud_rate))

                self.open_serial_port(port=port, baud=baud_rate, timeout=0.1)

                if self.serial_port is not None:
                    ret = self.confirm_device(self.serial_port, device_type)
                    if not ret:
                        self.serial_port.close()
                        return False
                    else:
                        self.update_connection_history({
                            'port': port,
                            'baud': baud_rate,
                            'device_type': device_type
                        })
                        return True
                else:
                    return False
        except Exception as ex:
            print(ex)
            return False

    def try_from_history(self, port):
        APP_CONTEXT.get_logger().logger.info(
            'try to use connected port {} in history'.format(port))

        history_connection_index = self._find_port_in_connection_history(port)

        if history_connection_index == -1:
            return False

        history_connection = self._connection_history['history'][history_connection_index]
        if history_connection:
            port = history_connection['port']
            baud_rate = self.baudrate_list[0] if self.baudrate_assigned \
                else history_connection['baud']
            device_type = self.filter_device_type if self.filter_device_type_assigned \
                else history_connection['device_type']
            # baud_rate = history_connection['baud']
            # device_type = history_connection['device_type']
            self.open_serial_port(port=port, baud=baud_rate, timeout=0.1)

            if self.serial_port is not None:
                ret = self.confirm_device(self.serial_port, device_type)
                if ret:
                    # update connection history
                    self.update_connection_history({
                        'port': port,
                        'baud': baud_rate,
                        'device_type': device_type
                    }, history_connection_index)
                    return True
                else:
                    self.serial_port.close()
                    return False
        return False

    def update_connection_history(self, connection, index=None):
        if self._connection_history is None:
            self._connection_history = {'history': []}

        if index is None:
            index = self._find_port_in_connection_history(connection['port'])

        # query connection with port
        # if found update, else append new one
        if index > -1:
            self._connection_history['last'] = index
            self._connection_history['history'][index] = connection
        elif index == -1:
            self._connection_history['history'].append(connection)
            self._connection_history['last'] = len(
                self._connection_history['history']) - 1

        try:
            with open(self.connection_file_path, 'w') as outfile:
                json.dump(self._connection_history, outfile)
        except:
            pass

    def _is_valid_connection_history(self, parsed_json):
        return parsed_json.__contains__('last') and parsed_json.__contains__('history')

    def _find_port_in_connection_history(self, port):
        exist_index = -1
        if self._connection_history:
            for index, connection in enumerate(self._connection_history['history']):
                if connection['port'] == port:
                    exist_index = index
                    break

        return exist_index

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

    def can_write(self):
        return self.serial_port and self.serial_port.isOpen()

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
                'Serial Exception! Please check the serial port connector is stable or not.\n')
            raise
        except Exception as ex:
            # print(e)
            raise

    def open(self, port=False, baud=57600):
        return self.open_serial_port(port, baud, timeout=0.1)

    def close(self):
        self._is_close = True
        return self.close_serial_port()

    def reset_buffer(self):
        '''
        reset buffer
        '''
        self.serial_port.flushInput()
        self.serial_port.flushOutput()
