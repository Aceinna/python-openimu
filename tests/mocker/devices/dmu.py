import struct
import time
from . import Parameter
from .base import DeviceBase
from .helper import (parse_command_packet, build_output_packet)
from aceinna.devices.parsers.dmu_field_parser import (
    decode_value, encode_value)

PRODUCT_CONFIG_ADDRESS = [0x07, 0x1c]


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


class DMUMocker(DeviceBase):
    '''A mocker runing DMU Application'''

    def __init__(self, **kwargs):
        super(DMUMocker, self).__init__()
        self._sn = '2008705635'
        self._ping_str = 'IMU381ZA-400 5020-1383-01'
        self._version = [0, 0, 0, 0, 0]
        self._data_index = 0
        self._total_data_len = 0
        # setup device configuration
        self._params = {
            '1': Parameter('packet_rate', 'uint16', 1),
            '2': Parameter('baud_rate', 'uint16', 5),
            '3': Parameter('packet_type', 'char8', 'S1'),
            '5': Parameter('accel_lpf', 'lpf', 25),
            '6': Parameter('rate_lpf', 'lpf', 25),
            '7': Parameter('orientation', 'orientation', '+X+Y+Z')
        }
        self._prepare_data()

    def _prepare_data(self):
        # read the bin, and parse the data in array

        self._sensor_data = {
            'S1': build_sensor_data_array('./tests/mocker/devices/Scale1.raw')
        }
        packet_type = self._find_parameter('packet_type').value
        self._total_data_len = len(self._sensor_data[packet_type])

    def handle_command(self, cli):
        packet_type, payload, error, delay = parse_command_packet(cli, False)
        # print(cli)
        output_packet = []
        if delay and delay > 0:
            time.sleep(delay)

        if error:
            packet_type = '\x00\x00'
            output_packet = bytes([])

        if packet_type == 'PK':
            output_packet = bytes([])
        if packet_type == 'GP':
            # id
            if payload.decode() == 'ID':
                # response SN(4B), model string
                packet_type = 'ID'
                output_packet.extend(struct.pack('>I', int(self._sn)))
                output_packet.extend(pack_str(self._ping_str))
            # version
            if payload.decode() == 'VR':
                packet_type = 'VR'
                output_packet = self._version
            output_packet = bytes(output_packet)
        if packet_type == 'SF' or packet_type == 'WF':
            # set value for field(s)
            param_len = payload[0]
            params_payload = payload[1:]

            output_packet.extend([param_len])

            for i in range(param_len):
                current_index = i*4
                param_id = params_payload[current_index:current_index+2]
                param_value = params_payload[current_index+2:current_index+4]
                parsed_param_id = decode_value('int16', param_id)
                define_parameter = self._params[str(parsed_param_id)]
                parsed_param_value = decode_value(
                    define_parameter.data_type, param_value)

                define_parameter.value = parsed_param_value

                output_packet.extend(param_id)

            output_packet = bytes(output_packet)
        if packet_type == 'GF' or packet_type == 'RF':
            # get value from field(s)

            param_len = payload[0]
            params_payload = payload[1:]

            output_packet.extend([param_len])

            for i in range(param_len):
                current_index = i*2
                param_id = params_payload[current_index:current_index+2]
                parsed_param_id = decode_value('int16', param_id)
                define_parameter = self._params[str(parsed_param_id)]
                param_value = encode_value(
                    define_parameter.data_type, define_parameter.value)
                output_packet.extend(param_id)
                output_packet.extend(param_value)

            output_packet = bytes(output_packet)


        if packet_type == 'RE':
            # only response product configuration
            start_address = list(struct.unpack('BB', payload[0:2]))
            word_len = payload[2]

            output_packet.extend(start_address)
            output_packet.extend([word_len])

            if start_address == PRODUCT_CONFIG_ADDRESS:
                output_packet.extend([0x00, 0x81])

            output_packet = bytes(output_packet)

        if packet_type == 'NA':
            output_packet = bytes([])
            return build_output_packet('\x00\x00', output_packet)

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
