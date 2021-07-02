import struct
import time
from . import Parameter
from .base import DeviceBase
from .helper import (parse_command_packet, build_output_packet)
from aceinna.devices.parsers.open_field_parser import (
    decode_value, encode_value)


def pack_str(value):
    return struct.pack('{0}B'.format(
        len(value)), *value.encode('UTF-8'))


def build_sensor_data_array(path):
    array_data = []
    raw_data = []
    packet_start = [0x55, 0x55]
    read_index = 0
    is_read_end = False
    message = None

    with open(path, 'rb') as data_bytes:
        raw_data = data_bytes.read()

    raw_data_len = len(raw_data)
    while not is_read_end:
        try_packet_start = [
            raw_data[read_index],
            raw_data[read_index+1]
        ]

        if packet_start == try_packet_start:
            # find one sensor data
            message = []
            message.extend(try_packet_start)

            # packet type
            message.extend(raw_data[read_index+2:read_index+4])

            # payload length
            payload_len = raw_data[read_index+4]
            payload_start_index = read_index+5
            message.extend([payload_len])

            # payload
            crc_index = payload_start_index+payload_len

            message.extend(
                raw_data[payload_start_index: crc_index])

            # crc
            message.extend(
                raw_data[crc_index: crc_index+2])

            array_data.append(message)

            read_index = read_index+len(message)
        else:
            read_index += 1

        if read_index >= raw_data_len-1:
            break

    return array_data


class RTKLMocker(DeviceBase):
    '''A mocker runing IMU Application'''

    def __init__(self, **kwargs):
        super(RTKLMocker, self).__init__()
        self._ping_str = 'RTK330LA OpenIMU330BI 5020-3021-01 1.1.8 SN:1975000034'
        self._version_str = 'RTK_INS App v2.0.0, BootLoader v1.1.1'
        self._data_index = 0
        self._total_data_len = 0
        # setup device configuration
        self._params = {
            '0': Parameter('data_crc', 'uint64', 0),
            '1': Parameter('data_size', 'uint64', 0),
            '2': Parameter('baud_rate', 'int64', 115200),
            '3': Parameter('packet_type', 'char8', 'z1'),
            '4': Parameter('packet_rate', 'uint64', 100),
            '5': Parameter('accel_lpf', 'int64', 25),
            '6': Parameter('rate_lpf', 'int64', 25),
            '7': Parameter('orientation', 'char8', '+X+Y+Z')
        }
        self._prepare_data()

    def _prepare_data(self):
        # read the bin, and parse the data in array

        self._sensor_data = {
            'z1': build_sensor_data_array('./tests/mocker/devices/z1.raw'),
            's1': build_sensor_data_array('./tests/mocker/devices/s1.raw')
        }
        packet_type = self._find_parameter('packet_type').value
        self._total_data_len = len(self._sensor_data[packet_type])

    def handle_command(self, cli):
        packet_type, payload, error, delay = parse_command_packet(cli)
        output_packet = []
        if delay and delay > 0:
            time.sleep(delay)

        if error:
            packet_type = '\x00\x00'
            output_packet = bytes([])

        if packet_type == 'pG':
            output_packet = pack_str(self._ping_str)
        if packet_type == 'gV':
            output_packet = pack_str(self._version_str)
        if packet_type == 'gA':
            for item in self._params:
                data_type = self._params[item].data_type
                value = self._params[item].value
                output_packet.extend(encode_value(data_type, value))

            output_packet = bytes(output_packet)
        if packet_type == 'gP':
            param_id = struct.unpack('<L', payload[0:4])[0]

            define_parameter = self._params[str(param_id)]

            data_type = define_parameter.data_type
            value = define_parameter.value
            output_packet.extend(payload[0:4])
            output_packet.extend(encode_value(data_type, value))
            output_packet = bytes(output_packet)
        if packet_type == 'sC':
            output_packet = bytes([])
        if packet_type == 'uP':
            param_id = struct.unpack('<L', payload[0:4])[0]
            define_parameter = self._params[str(param_id)]

            update_value = decode_value(
                define_parameter.data_type, payload[4:12])
            define_parameter.value = update_value

            output_packet = struct.pack('i', 0)
        if packet_type == 'rD':
            output_packet = bytes([])

        return build_output_packet(packet_type, output_packet)

    def gen_sensor_data(self):
        # read a line from prepare data return one packet
        while True:
            packet_type = self._find_parameter('packet_type').value
            sensor_data = self._sensor_data[packet_type]
            yield bytes(sensor_data[self._data_index % self._total_data_len])
            self._data_index += 1
            if self._data_index >= self._total_data_len:
                self._data_index = 0
