import struct
from . import Parameter
from .base import DeviceBase
from .helper import (parse_packet, build_output_packet)
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
            message= []
            message.extend(try_packet_start)

            # packet type
            message.extend(raw_data[read_index+2:read_index+4])

            # payload length
            payload_len = raw_data[read_index+4]
            payload_start_index = read_index+5
            #print(raw_data[read_index+2:read_index+4],payload_len)
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


class OpenIMUMocker(DeviceBase):
    '''A mocker runing IMU Application'''

    def __init__(self):
        self._ping_str = 'OpenIMU300ZA 5020-3885-02 1.1.2 SN:1808400528'
        self._version_str = 'OpenIMU300ZI IMU 1.1.3'
        self._data_index = 0
        self._total_data_len = 0
        # setup device configuration
        self._params = {
            'data_crc': Parameter('uint64', 0),
            'data_size': Parameter('uint64', 0),
            'baud_rate': Parameter('int64', 115200),
            'packet_type': Parameter('char8', 'z1'),
            'packet_rate': Parameter('uint64', 100),
            'accel_lpf': Parameter('int64', 25),
            'rate_lpf': Parameter('int64', 25),
            'orientation': Parameter('char8', '+X+Y+Z')
        }
        self._prepare_data()

    def _prepare_data(self):
        # read the bin, and parse the data in array

        self._sensor_data = {
            'z1': build_sensor_data_array('./tests/mocker/devices/z1.bin'),
            's1': build_sensor_data_array('./tests/mocker/devices/s1.bin')
        }
        packet_type = self._params['packet_type'].value
        self._total_data_len = len(self._sensor_data[packet_type])

    def handle_command(self, cli):
        packet_type, payload, error = parse_packet(cli)
        output_packet = []
        if error:
            packet_type = 'NAK'

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
            # TODO: should implement
            output_packet = bytes([])
        if packet_type == 'sC':
            output_packet = bytes([])
        if packet_type == 'uP':
            param_id = struct.unpack('<L', payload[0:4])[0]
            key = self._params.keys()[param_id]
            define_parameter = self._params[key]

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
            packet_type = self._params['packet_type'].value
            sensor_data = self._sensor_data[packet_type]
            yield bytes(sensor_data[self._data_index % self._total_data_len])
            self._data_index += 1
            if self._data_index >= self._total_data_len:
                self._data_index = 0
