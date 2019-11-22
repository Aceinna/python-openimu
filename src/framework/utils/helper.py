import json
import struct

COMMAND_START = [0x55, 0x55]


def build_input_packet(name, properties=None, param=False, value=False):
    name_bytes = list(struct.unpack('BB', bytearray(name, 'utf-8')))

    if not param and not value:
        S = COMMAND_START + name_bytes + [0]
        packet = S + calc_crc(S[2:4] + [0x00])
    else:
        payload = unpack_payload(properties, param, value)
        S = COMMAND_START + name_bytes + [len(payload)] + payload
        packet = S + calc_crc(S[2:S[4]+5])
    return packet


def unpack_payload(name, properties, param=False, value=False):
    input_packet = next(
        (x for x in properties['userMessages']['inputPackets'] if x['name'] == name), None)

    if self.name == 'ma':
        input_action = next(
            (x for x in input_packet['inputPayload'] if x['actionName'] == param), None)
        return [input_action['actionID']]
    elif input_packet != None:
        if input_packet['inputPayload']['type'] == 'paramId':
            return list(struct.unpack("4B", struct.pack("<L", param)))
        elif input_packet['inputPayload']['type'] == 'userParameter':
            payload = list(struct.unpack("4B", struct.pack("<L", param)))
            if properties['userConfiguration'][param]['type'] == 'char8':
                length = len(value)
                payload += list(struct.unpack('{0}B'.format(length),
                                              bytearray(value, 'utf-8')))
                for i in range(8-length):
                    payload += [0x00]
            elif properties['userConfiguration'][param]['type'] == 'int64':
                payload += list(struct.unpack("8B", struct.pack("<q", value)))
            elif properties['userConfiguration'][param]['type'] == 'double':
                payload += list(struct.unpack("8B",
                                              struct.pack("<d", float(value))))
            return payload


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
