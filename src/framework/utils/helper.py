import json
import struct
import sys

COMMAND_START = [0x55, 0x55]


def build_input_packet(name, properties=None, param=False, value=False):
    name_bytes = list(struct.unpack('BB', bytearray(name, 'utf-8')))

    if not param and not value:
        S = COMMAND_START + name_bytes + [0]
        packet = S + calc_crc(S[2:4] + [0x00])
    else:
        payload = unpack_payload(name, properties, param, value)
        S = COMMAND_START + name_bytes + [len(payload)] + payload
        packet = S + calc_crc(S[2:S[4]+5])
    return packet

def build_bootloader_input_packet(name, properties=None, data_len = False, addr = False, data = False):
    name_bytes =  list(struct.unpack('BB', bytearray(name, 'utf-8')))

    if not data_len and not addr and not data:
        S = COMMAND_START + name_bytes + [0]  
        packet = S + calc_crc(S[2:4] + [0x00])  
    else:
        payload = block_payload(data_len, addr, data)
        S = COMMAND_START + name_bytes + [len(payload)] + payload
        packet = S + calc_crc(S[2:S[4]+5])   
    return packet

def unpack_payload(name, properties, param=False, value=False):
    input_packet = next(
        (x for x in properties['userMessages']['inputPackets'] if x['name'] == name), None)

    if name == 'ma':
        input_action = next(
            (x for x in input_packet['inputPayload'] if x['actionName'] == param), None)
        return [input_action['actionID']]
    elif input_packet != None:
        if input_packet['inputPayload']['type'] == 'paramId':
            return list(struct.unpack("4B", struct.pack("<L", param)))
        elif input_packet['inputPayload']['type'] == 'userParameter':
            payload = list(struct.unpack("4B", struct.pack("<L", param)))
            if properties['userConfiguration'][param]['type'] == 'uint64':
                payload += list(struct.unpack("8B", struct.pack("<Q", value)))
            elif properties['userConfiguration'][param]['type'] == 'int64':
                payload += list(struct.unpack("8B", struct.pack("<q", value)))
            elif properties['userConfiguration'][param]['type'] == 'double':
                payload += list(struct.unpack("8B", struct.pack("<d", float(value))))
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
                c_len = int(properties['userConfiguration'][param]['type'].replace('char', ''))
                length = len(value)
                payload += list(struct.unpack('{0}B'.format(length),
                                              bytearray(value, 'utf-8')))
                for i in range(c_len-length):
                    payload += [0x00]
            elif properties['userConfiguration'][param]['type'] == 'ip4':
                ip = value.split('.')
                ip_4 = list(map(int, ip)) 
                for i in range(4):
                    payload += list(struct.unpack("1B", struct.pack("<B", ip_4[i])))
            elif properties['userConfiguration'][param]['type'] == 'ip6':
                ip = value.split('.')
                payload += list(struct.unpack('6B', bytearray(ip, 'utf-8')))

            return payload


def block_payload(data_len, addr, data):
        C = []
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
            if (sys.version_info > (3, 0)):
                C.insert(len(C), data[i])
            else:
                C.insert(len(C), ord(data[i]))
        return C

def calc_crc(payload):
    '''Calculates 16-bit CRC-CCITT
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
    crc_msb = (crc & 0xFF00) >> 8
    crc_lsb = (crc & 0x00FF)
    return [crc_msb, crc_lsb]


def clear_elements(list_instance):
    if (sys.version_info < (3, 0)):
        list_instance[:]=[]
    else:
        list_instance.clear()
        
