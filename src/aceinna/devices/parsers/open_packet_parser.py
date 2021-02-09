import sys
import struct
import collections
from . import filter_nan
from .open_field_parser import decode_value
from ...framework.utils.print import print_yellow
from ...framework.context import APP_CONTEXT
# from .dmu_field_parser import decode_value

# input packet
error_decode_packet = 0


def string_parser(payload, user_configuration):
    error = False
    data = ''
    try:
        if sys.version_info < (3, 0):
            data = str(struct.pack(
                '{0}B'.format(len(payload)), *payload))
        else:
            data = str(struct.pack(
                '{0}B'.format(len(payload)), *payload), 'utf-8')
    except UnicodeDecodeError:
        data = ''

    return data, error


def get_all_parameters_parser(payload, user_configuration):
    '''
    gA parser
    '''
    error = False
    data = []
    data_len = 0
    for parameter in user_configuration:
        param_id = parameter['paramId']
        param_type = parameter['type']
        name = parameter['name']

        if param_type == 'uint8' or param_type == 'int8':
            value = decode_value(
                param_type, payload[data_len:data_len + 1])
            data_len = data_len + 1
        elif param_type == 'uint16' or param_type == 'int16':
            value = decode_value(
                param_type, payload[data_len:data_len + 2])
            data_len = data_len + 2
        elif param_type == 'uint32' or param_type == 'int32' or param_type == 'float':
            value = decode_value(
                param_type, payload[data_len:data_len + 4])
            data_len = data_len + 4
        elif param_type == 'uint64' or param_type == 'int64' or param_type == 'double':
            value = decode_value(
                param_type, payload[data_len:data_len + 8])
            data_len = data_len + 8
        elif param_type == 'ip4':
            value = decode_value(
                param_type, payload[data_len:data_len + 4])
            data_len = data_len + 4
        elif param_type == 'ip6':
            value = decode_value(
                param_type, payload[data_len:data_len + 6])
            data_len = data_len + 6
        elif 'char' in param_type:
            ctype_n = param_type.replace('char', '')
            ctype_l = int(ctype_n)
            value = decode_value(
                param_type, payload[data_len:data_len + ctype_l])
            data_len = data_len + ctype_l
        else:
            print(
                "no [{0}] when unpack_input_packet".format(param_type))
            value = False
        data.append(
            {"paramId": param_id, "name": name, "value": value})

    return data, error


def get_parameters_by_block_parser(payload, user_configuration):
    '''
    gB parser
    '''
    data = []
    error = False

    start_param_id = payload[0]
    end_param_id = payload[1]
    data_len = 2

    for i in range(start_param_id, end_param_id+1, 1):
        exist_param_conf = next((param_conf for param_conf in user_configuration
                                 if param_conf['paramId'] == i), None)
        if exist_param_conf:
            param_type = exist_param_conf['type']

            if param_type == 'uint8' or param_type == 'int8':
                value = decode_value(
                    param_type, payload[data_len:data_len + 1])
                data_len = data_len + 1
            elif param_type == 'uint16' or param_type == 'int16':
                value = decode_value(
                    param_type, payload[data_len:data_len + 2])
                data_len = data_len + 2
            elif param_type == 'uint32' or param_type == 'int32' or param_type == 'float':
                value = decode_value(
                    param_type, payload[data_len:data_len + 4], exist_param_conf)
                data_len = data_len + 4
            elif param_type == 'uint64' or param_type == 'int64' or param_type == 'double':
                value = decode_value(
                    param_type, payload[data_len:data_len + 8])
                data_len = data_len + 8
            elif param_type == 'ip4':
                value = decode_value(
                    param_type, payload[data_len:data_len + 4])
                data_len = data_len + 4
            elif param_type == 'ip6':
                value = decode_value(
                    param_type, payload[data_len:data_len + 6])
                data_len = data_len + 6
            elif 'char' in param_type:
                ctype_n = param_type.replace('char', '')
                ctype_l = int(ctype_n)
                value = decode_value(
                    param_type, payload[data_len:data_len + ctype_l])
                data_len = data_len + ctype_l
            else:
                print(
                    "no [{0}] when unpack_input_packet".format(param_type))
                value = False

            data.append({
                "paramId": i,
                "name": exist_param_conf['name'],
                "value": value
            })

    return data, error


def get_parameter_parser(payload, user_configuration):
    '''
    gP Parser
    '''
    data = None
    error = False
    param_id = decode_value('uint32', payload[0:4])

    if param_id is not False:
        param = filter(lambda item: item['paramId'] ==
                       param_id, user_configuration)

        try:
            first_item = next(iter(param), None)
            param_value = decode_value(
                first_item['type'], payload[4:12])
            data = {"paramId": param_id,
                    "name": first_item['name'], "value": param_value}
        except StopIteration:
            error = True
        except Exception:
            error = True
    else:
        error = True

    return data, error


def update_parameter_parser(payload, user_configuration):
    '''
    uP parser
    '''
    error = False
    data = decode_value('uint32', payload[0:4])
    if data:
        error = True
    return data, error


def update_parameters_parser(payload, user_configuration):
    '''
    uB parser
    '''
    error = False
    data = decode_value('uint32', payload[0:4])
    if data:
        error = True
    return data, error


def common_input_parser(payload, user_configuration):
    '''
    General input packet parser
    '''
    return payload, False


def read_eeprom_parser(payload, user_configuration=None):
    return payload[3:], False


# output packet


def common_continuous_parser(payload, configuration):
    '''
    Unpack output packet
    '''
    if configuration is None:
        return

    data = None
    is_list = 0
    length = 0
    pack_fmt = '<'
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

    has_list = configuration.__contains__('isList')
    if has_list:
        is_list = configuration['isList']

    if is_list == 1:
        packet_num = len(payload) // length
        data = []
        for i in range(packet_num):
            payload_c = payload[i*length:(i+1)*length]
            try:
                pack_item = struct.pack(len_fmt, *payload_c)
                item = struct.unpack(pack_fmt, pack_item)
                out = [(value['name'], item[idx])
                       for idx, value in enumerate(configuration['payload'])]
                item = collections.OrderedDict(out)
                data.append(item)
            except Exception as ex:  # pylint: disable=broad-except
                print(
                    "error happened when decode the payload, pls restart driver: {0}"
                    .format(ex))
    else:
        try:
            pack_item = struct.pack(len_fmt, *payload)
            data = struct.unpack(pack_fmt, pack_item)
            out = [(
                value['name'],
                filter_nan(data[idx])
            ) for idx, value in enumerate(configuration['payload'])]

            data = collections.OrderedDict(out)
        except Exception as ex:  # pylint: disable=broad-except
            global error_decode_packet
            error_decode_packet = error_decode_packet + 1
            if error_decode_packet == 100 or error_decode_packet == 400 or error_decode_packet == 700:
                print_yellow(
                    "warning: your firmware may not suitable for this driver, pls update firmware or driver")

            if error_decode_packet % 300 == 0:
                APP_CONTEXT.get_logger().logger.warning(
                    "error happened when decode the payload of packets, pls restart driver: {0}"
                    .format(ex))

    return data


def other_output_parser(payload):
    return payload

# packet handler


def match_command_handler(packet_type):
    '''
    Find the handler for specified packet
    '''
    parser_dict = {
        'pG': string_parser,
        'uC': common_input_parser,  # update_command_parser,
        'uP': update_parameter_parser,
        'uA': common_input_parser,  # update_all_command_parser,
        'sC': common_input_parser,
        'rD': common_input_parser,
        'gC': common_input_parser,  # get_command_parser,
        'gA': get_all_parameters_parser,
        'gP': get_parameter_parser,
        'gB': get_parameters_by_block_parser,
        'gV': string_parser,
        'uB': update_parameters_parser,
        'ma': common_input_parser,
        'RE': read_eeprom_parser,
        'WE': common_input_parser,
        'UE': common_input_parser,
        'LE': common_input_parser,
        'SR': common_input_parser,
        'JI': common_input_parser,
        'JA': common_input_parser,
        'WA': common_input_parser
    }
    return parser_dict.get(packet_type)
