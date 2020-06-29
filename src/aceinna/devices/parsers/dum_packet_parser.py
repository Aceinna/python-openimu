import struct
import collections
from ..dmu.configuration_field import CONFIGURATION_FIELD_DEFINES_SINGLETON
from ..dmu.eeprom_field import EEPROM_FIELD_DEFINES_SINGLETON
from .dmu_field_parser import decode_value
# input packet


def read_eeprom_parser(payload):
    read_address = decode_value('uint16', payload[0:2])
    eeprom_data = payload[3:]
    eeprom_field = EEPROM_FIELD_DEFINES_SINGLETON.find(read_address)
    value, parsed, error = eeprom_field.parse(eeprom_data)

    return {
        "name": eeprom_field.name,
        "value": value,
        "parsed": parsed
    }, error


def read_field_parser(payload):
    data = []
    error = False
    number_of_fields = payload[0]
    data_payload = payload[1:]

    for parameter_index in range(number_of_fields):
        parameter_id = decode_value(
            'uint16', data_payload[parameter_index * 4:parameter_index*4+2])

        parameter_value = data_payload[parameter_index *
                                       4+2:parameter_index*4+4]

        configuration_field = CONFIGURATION_FIELD_DEFINES_SINGLETON.find(
            parameter_id)

        value, parsed, error = configuration_field.parse(parameter_value)
        # value = unpack_value(configuration_field.field_type, parameter_value)

        if error:
            break

        data.append({
            "paramId": parameter_id,
            "name": configuration_field.name,
            "value": value,
            "parsed": parsed
        })

    return data, error


def write_field_parser(payload):
    data = 0
    error = False
    field_count = decode_value('uint8', payload[0:1])

    if isinstance(field_count, bool) and not field_count:
        error = True
        data = -1

    return data, error


# output packet

def id_parser(payload, *args):
    '''
    Parse id packet
    '''
    serial_num = int.from_bytes(struct.pack(
        '4B', *payload[0:4]), byteorder='big')

    mode_string_len = len(payload[4:])
    model_string = struct.pack('{0}B'.format(
        mode_string_len), *payload[4:]).decode()

    split_text = model_string.split(' ')

    return {
        'name': split_text[0],
        'pn': split_text[1],
        'sn': serial_num
    }


def version_data_parser(payload, *args):
    '''
    Parse version data
    '''
    version_string = '{0}.{1}.{2}.{3}.{4}'.format(*payload)

    return {
        'app_name': 'DMU',
        'version': version_string
    }


def common_continuous_parser(payload, configuration, scaling):
    '''
    Unpack output packet
    '''
    if configuration is None:
        return

    data = None
    length = 0
    pack_fmt = '>'
    for value in configuration['payload']:
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

    try:
        pack_item = struct.pack(len_fmt, *payload)
        data = struct.unpack(pack_fmt, pack_item)
        out = []

        for idx, item in enumerate(configuration['payload']):
            scaling_setting = None
            scaling_value = 1
            if item.__contains__('scaling'):
                scaling_setting = scaling[item['scaling']]
            if scaling_setting:
                scaling_value = eval(scaling_setting)

            format_value = data[idx]*scaling_value
            out.append((item['name'], format_value))

        format_data = collections.OrderedDict(out)

    except Exception as ex:  # pylint: disable=broad-except
        print(
            "error happened when decode the payload of packets, pls restart driver: {0}"
            .format(ex))

    return format_data


# packet handler
def match_command_handler(packet_type):
    '''
    Find the handler for specified packet
    '''
    parser_dict = {
        'RF': read_field_parser,
        'GF': read_field_parser,
        'SF': write_field_parser,
        'WF': write_field_parser,
        'RE': read_eeprom_parser
    }
    return parser_dict.get(packet_type)


def match_continuous_handler(packet_type):
    parser_dict = {
        'ID': id_parser,
        'VR': version_data_parser
    }
    if not parser_dict.__contains__(packet_type):
        return common_continuous_parser
    return parser_dict.get(packet_type)
