import struct

VALID_OPEN_PACKET_TYPES = ['pG', 'uC', 'uP', 'uA', 'uB',
                           'sC', 'rD',
                           'gC', 'gA', 'gB', 'gV', 'gP',
                           '\x15\x15', '\x00\x00', 'ma', 'NA',
                           'JI', 'JA', 'WA',
                           'RE', 'WE', 'UE', 'LE', 'SR']

VALID_CLOSURE_PACKET_TYPES = ['PK', 'GP', 'SF', 'WF', 'GF', 'RF', 'RE', 'NA']


def is_command_start(command_start):
    return struct.unpack('2B', command_start) == (0x55, 0x55)


def is_valid_packet_type(packet_type, is_open):
    packet_type = packet_type.decode()
    if is_open:
        return VALID_OPEN_PACKET_TYPES.__contains__(packet_type)
    else:
        return VALID_CLOSURE_PACKET_TYPES.__contains__(packet_type)


def parse_command_packet(data, is_open=True):
    packet_type = ''
    payload = []
    error = False
    delay = 0

    raw_command_start = data[0:2]
    raw_packet_type = data[2:4]

    if is_command_start(raw_command_start) and \
       is_valid_packet_type(raw_packet_type, is_open):
        packet_type = raw_packet_type.decode()
        payload_len = data[4]  # struct.unpack('b', data[4])[0]
        payload = data[5:payload_len+5]
        crc = data[payload_len+5:payload_len+7]
        if payload_len+7 < len(data):
            try:
                delay_raw = data[payload_len+7:]
                delay = struct.unpack('<i', delay_raw)[0]
            except Exception as ex:
                print(ex)
                delay = 0
    else:
        error = True

    return packet_type, payload, error, delay


def build_output_packet(packet_type, payload):
    packed_command_start = struct.pack('2B', *[0x55, 0x55])
    packed_packet_type = packet_type.encode()
    payload_len = bytes([len(payload)])
    packed_crc = bytes(calc_crc(packed_packet_type+payload_len+payload))

    return packed_command_start + \
        packed_packet_type + \
        payload_len + \
        payload + \
        packed_crc


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


def wrap_delay_response_command(cli, delay):
    cli.extend(struct.pack("<i", delay))
    return cli
