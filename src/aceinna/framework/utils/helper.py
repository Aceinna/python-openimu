"""
Helper
"""
import struct
import sys
from .dict_extend import Dict

if sys.version_info[0] > 2:
    from queue import Queue
else:
    from Queue import Queue

COMMAND_START = [0x55, 0x55]


def build_packet(message_type, message_bytes=[]):
    '''
    Build final packet
    '''
    packet = []
    packet.extend(bytearray(message_type, 'utf-8'))

    msg_len = len(message_bytes)
    packet.append(msg_len)
    final_packet = packet + message_bytes
    # print(message_type, final_packet)
    return COMMAND_START + final_packet + calc_crc(final_packet)


def build_input_packet(name, properties=None, param=False, value=False):
    '''
    Build input packet
    '''
    packet = []

    if not param and not value:
        packet = build_packet(name)
    else:
        payload = unpack_payload(name, properties, param, value)
        packet = build_packet(name, payload)
    return packet


def build_bootloader_input_packet(name, data_len=False, addr=False, data=False):
    '''
    Build bootloader input packet
    '''
    if not data_len and not addr and not data:
        packet = build_packet(name)
    else:
        payload = block_payload(data_len, addr, data)
        packet = build_packet(name, payload)
    return packet


def build_read_eeprom_input_packet(start, word_len):
    '''
    Build RE command
    '''
    payload = []
    payload.append((start & 0xFF00) >> 8)
    payload.append(start & 0x00FF)
    payload.append(word_len)
    packet = build_packet('RE', payload)
    return packet


def build_write_eeprom_input_packet(start, word_len, data):
    '''
    Build WE command
    '''
    name_bytes = list(struct.unpack('BB', bytearray('WE', 'utf-8')))
    payload = []
    payload.append((start & 0xFF00) >> 8)
    payload.append(start & 0x00FF)
    payload.append(word_len)
    payload.extend(data)
    command = COMMAND_START + name_bytes + [word_len*2+3] + payload
    packet = command + calc_crc(command[2:command[4]+5])
    return packet


def build_unlock_eeprom_packet(sn):
    '''
    Build UE command
    '''
    sn_crc = calc_crc(sn)
    payload = sn_crc
    packet = build_packet('UE', payload)
    return packet


def build_lock_eeprom_packet():
    '''
    Build UE command
    '''
    packet = build_packet('LE')
    return packet


def unpack_payload(name, properties, param=False, value=False):
    '''
    Unpack payload
    '''
    input_packet = next(
        (x for x in properties['userMessages']['inputPackets'] if x['name'] == name), None)

    if name == 'ma':
        input_action = next(
            (x for x in input_packet['inputPayload'] if x['actionName'] == param), None)
        return [input_action['actionID']]
    elif input_packet is not None:
        if input_packet['inputPayload']['type'] == 'paramId':
            return list(struct.unpack("4B", struct.pack("<L", param)))
        elif input_packet['inputPayload']['type'] == 'userParameter':
            payload = list(struct.unpack("4B", struct.pack("<L", param)))
            if properties['userConfiguration'][param]['type'] == 'uint64':
                payload += list(struct.unpack("8B", struct.pack("<Q", value)))
            elif properties['userConfiguration'][param]['type'] == 'int64':
                payload += list(struct.unpack("8B", struct.pack("<q", value)))
            elif properties['userConfiguration'][param]['type'] == 'double':
                payload += list(struct.unpack("8B",
                                              struct.pack("<d", float(value))))
            elif properties['userConfiguration'][param]['type'] == 'uint32':
                payload += list(struct.unpack("4B", struct.pack("<I", value)))
            elif properties['userConfiguration'][param]['type'] == 'int32':
                payload += list(struct.unpack("4B", struct.pack("<i", value)))
            elif properties['userConfiguration'][param]['type'] == 'float':
                payload += list(struct.unpack("4B", struct.pack("<f", value)))
            elif properties['userConfiguration'][param]['type'] == 'uint16':
                payload += list(struct.unpack("2B", struct.pack("<H", value)))
            elif properties['userConfiguration'][param]['type'] == 'int16':
                payload += list(struct.unpack("2B", struct.pack("<h", value)))
            elif properties['userConfiguration'][param]['type'] == 'uint8':
                payload += list(struct.unpack("1B", struct.pack("<B", value)))
            elif properties['userConfiguration'][param]['type'] == 'int8':
                payload += list(struct.unpack("1B", struct.pack("<b", value)))
            elif 'char' in properties['userConfiguration'][param]['type']:
                c_len = int(properties['userConfiguration']
                            [param]['type'].replace('char', ''))
                if isinstance(value, int):
                    length = len(str(value))
                    payload += list(struct.unpack('{0}B'.format(length),
                                                  bytearray(str(value), 'utf-8')))
                else:
                    length = len(value)
                    payload += list(struct.unpack('{0}B'.format(length),
                                                  bytearray(value, 'utf-8')))
                for i in range(c_len-length):
                    payload += [0x00]
            elif properties['userConfiguration'][param]['type'] == 'ip4':
                ip_address = value.split('.')
                ip_address_v4 = list(map(int, ip_address))
                for i in range(4):
                    payload += list(struct.unpack("1B",
                                                  struct.pack("<B", ip_address_v4[i])))
            elif properties['userConfiguration'][param]['type'] == 'ip6':
                ip_address = value.split('.')
                payload += list(struct.unpack('6B',
                                              bytearray(ip_address, 'utf-8')))

            return payload


def block_payload(data_len, addr, data):
    '''
    Block payload
    '''
    data_bytes = []
    addr_3 = (addr & 0xFF000000) >> 24
    addr_2 = (addr & 0x00FF0000) >> 16
    addr_1 = (addr & 0x0000FF00) >> 8
    addr_0 = (addr & 0x000000FF)
    data_bytes.insert(len(data_bytes), addr_3)
    data_bytes.insert(len(data_bytes), addr_2)
    data_bytes.insert(len(data_bytes), addr_1)
    data_bytes.insert(len(data_bytes), addr_0)
    data_bytes.insert(len(data_bytes), data_len)
    for i in range(data_len):
        if sys.version_info > (3, 0):
            data_bytes.insert(len(data_bytes), data[i])
        else:
            data_bytes.insert(len(data_bytes), ord(data[i]))
    return data_bytes


def parse_command_packet(raw_command):
    packet_type = ''
    payload = []
    error = False

    raw_command_start = raw_command[0:2]
    raw_packet_type = raw_command[2:4]

    if COMMAND_START == raw_command_start:
        packet_type = bytes(raw_packet_type).decode()
        payload_len = raw_command[4]  # struct.unpack('b', data[4])[0]
        payload = raw_command[5:payload_len+5]
    else:
        error = True

    return packet_type, payload, error


def calc_crc(payload):
    '''
    Calculates 16-bit CRC-CCITT
    '''
    crc = 0x1D0F
    for bytedata in payload:
        crc = crc ^ (bytedata << 8)
        i = 0
        while i < 8:
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            i += 1

    crc = crc & 0xffff
    crc_msb = (crc & 0xFF00) >> 8
    crc_lsb = (crc & 0x00FF)
    return [crc_msb, crc_lsb]


def clear_elements(list_instance):
    '''
    clear list
    '''
    if sys.version_info < (3, 0):
        list_instance[:] = []
    else:
        list_instance.clear()


def dict_to_object(dict_obj):
    '''
    Convert Dict to Object
    '''
    if not isinstance(dict_obj, dict):
        return dict_obj
    inst = Dict()
    for key, val in dict_obj.items():
        inst[key] = dict_to_object(val)
    return inst


def name_convert_camel_to_snake(camel_name):
    '''
    Convert Camel naming to snake case
    '''
    chars = []
    underscore = '_'

    lower_camel_name = camel_name.lower()

    for i, char in enumerate(camel_name):
        add_underscore = False
        lower_char = lower_camel_name[i]
        if char != lower_char:
            add_underscore = True if i > 0 else False

        if add_underscore:
            chars.append(underscore+lower_char)
        else:
            chars.append(lower_char)

    return ''.join(chars)


def _parse_buffer(data_buffer):
    response = {
        'parsed': False,
        'parsed_end_index': 0,
        'result': []
    }
    data_queue = Queue()
    data_queue.queue.extend(data_buffer)

    command_start = [0x55, 0x55]
    parsed_data = []
    is_header_found = False
    packet_type = ''
    data_buffer_len = len(data_buffer)

    while not data_queue.empty():
        if is_header_found:
            # if matched packet, is_header_found = False, parsed_data = []
            if not data_queue.empty():
                packet_type_start = data_queue.get()
            else:
                break

            if not data_queue.empty():
                packet_type_end = data_queue.get()
            else:
                break

            if not data_queue.empty():
                packet_len = data_queue.get()
                packet_type = ''.join(
                    ["%c" % x for x in [packet_type_start, packet_type_end]])
                packet_data = []

                if data_queue.qsize() >= packet_len:
                    # take packet
                    for _ in range(packet_len):
                        packet_data.append(data_queue.get())
                else:
                    break
                # update response
                response['parsed'] = True
                response['result'].append({
                    'type': packet_type,
                    'data': packet_data
                })
                response['parsed_end_index'] += data_buffer_len - \
                    data_queue.qsize()
                data_buffer_len = data_queue.qsize()
                parsed_data = []
                is_header_found = False
            else:
                break
        else:
            byte_item = data_queue.get()
            parsed_data.append(byte_item)

            if len(parsed_data) > 2:
                parsed_data = parsed_data[-2:]

            if parsed_data == command_start:
                # find message start
                is_header_found = True
                parsed_data = []

    return response


def read_untils_have_data(communicator, packet_type, read_length=200, retry_times=20):
    '''
    Get data from limit times of read
    '''
    result = None
    trys = 0
    data_buffer = []

    while trys < retry_times:
        read_data = communicator.read(read_length)

        if read_data is None:
            trys += 1
            continue

        data_buffer_per_time = bytearray(read_data)
        data_buffer.extend(data_buffer_per_time)

        response = _parse_buffer(data_buffer)
        if response['parsed']:
            matched_packet = next(
                (packet['data'] for packet in response['result']
                 if packet['type'] == packet_type), None)
            if matched_packet is not None:
                result = matched_packet
            else:
                # clear buffer to parsed index
                data_buffer = data_buffer[response['parsed_end_index']:]

        if result is not None:
            break

        trys += 1

    return result


def collection_to_dict(collection, key):
    '''
    Convet a collection to dict
    '''
    inst = dict()
    for item in collection:
        actual_key = item[key]
        inst[actual_key] = item
    return inst
