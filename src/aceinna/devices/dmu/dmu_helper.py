import struct
from typing import List
from .eeprom_field import EEPROMField
from .configuration_field import ConfigurationField
from ...framework.utils import helper

COMMAND_START = [0x55, 0x55]


def build_read_field_packets(field: ConfigurationField, from_eeprom=False) -> bytearray:
    message_type = 'GF' if not from_eeprom else 'RF'

    fields_bytes = []
    field_id_bytes = struct.pack('>h', field.field_id)
    fields_bytes.extend(field_id_bytes)

    return build_packet(message_type, fields_bytes)


def build_read_fields_packets(fields: List[ConfigurationField], from_eeprom=False) -> bytearray:
    message_type = 'GF' if not from_eeprom else 'RF'

    fields_bytes = []
    for field in fields:
        field_id_bytes = struct.pack('>h', field.field_id)
        fields_bytes.extend(field_id_bytes)

    return build_packet(message_type, fields_bytes)


def build_write_filed_cli(field: ConfigurationField, value, write_to_eeprom=False) -> bytearray:
    message_type = 'SF' if not write_to_eeprom else 'WF'

    fields_bytes = []

    field_id_bytes = struct.pack('>h', field.field_id)
    field_value_bytes = field.encode(value)

    fields_bytes.extend(field_id_bytes)
    fields_bytes.extend(field_value_bytes)

    return build_packet(message_type, fields_bytes)


def build_write_fileds_cli(fields: List[ConfigurationField], values, write_to_eeprom=False) -> bytearray:
    message_type = 'SF' if not write_to_eeprom else 'WF'

    fields_bytes = []
    for index, field in enumerate(fields):
        field_id_bytes = struct.pack('>h', field.field_id)
        field_value_bytes = field.encode(values[index])

        fields_bytes.extend(field_id_bytes)
        fields_bytes.extend(field_value_bytes)

    return build_packet(message_type, fields_bytes)


def build_read_eeprom_cli(field: EEPROMField) -> bytearray:
    fields_bytes = []

    start_address_bytes = struct.pack('>h', field.address)

    fields_bytes.extend(start_address_bytes)
    fields_bytes.extend([field.word_len])

    return build_packet('RE', fields_bytes)


def build_write_eeproms_cli():
    pass


def build_packet(message_type, message_bytes=[]):
    '''
    build dmu command packet
    inspired from https://github.com/rishitborad/IMU383_Verification_Scripts/blob/master/IMU383_Uart.py
    '''
    packet = []
    packet.extend(bytearray(message_type, 'utf-8'))

    if message_type == "WF" or message_type == "SF":
        msg_len = 1 + len(message_bytes)
        no_of_fields = int(len(message_bytes)/4)
        packet.append(msg_len)
        packet.append(no_of_fields)
        final_packet = packet + message_bytes
        # print packet
    elif message_type == "RF" or message_type == "GF":
        msg_len = 1 + len(message_bytes)
        no_of_fields = int(len(message_bytes)/2)
        packet.append(msg_len)
        packet.append(no_of_fields)
        final_packet = packet + message_bytes
    else:
        msg_len = len(message_bytes)
        packet.append(msg_len)
        final_packet = packet + message_bytes
    # print(message_type, final_packet)
    return COMMAND_START + final_packet + helper.calc_crc(final_packet)


def build_continous_packet_types(architecture, algorithm, mags):
    '''
    Output Packets      architecture	        algorithm	mags
    S0	                any except 4 and 5	    any	        1
    S2	                any except 4 and 5	    1	        any
    S3	                4 or 5	                any	        any
    A0,A1,	            any except 4 and 5 	    1	        1
    A2,	                any 	                1	        any
    A3	                4 or 5	                any     	any
    A4	                any 	                1	        any
    A5	                4 or 5	                any     	any
    B1,B2	            2 or 3	                any	        any
    N0	                any except 4 and 5	    1	        any
    N1	                any except 4 and 5	    1	        any
    LEGACY500	        any except 4 and 5 	    1	        any
    T1	                4 or 5	                any     	any
    F3	                any except 4 and 5 	    1	        any
    F4	                4 or 5	                any	        any
    F5	                4 or 5	                any	        any
    F6	                4 or 5	                any	        any
    F7	                4 or 5	                any	        any
    KC,KT,KS	        any except 4 and 5 	    any	        any

    default packets
    ID,T0,F1, F2,S1, VR,VA
    '''
    packet_types = []
    default_packet_types = ['S1']  # ['ID','T0','F1','F2','S1','VR','VA']

    packet_types.extend(default_packet_types)

    if architecture != 4 and architecture != 5:
        # packet_types.extend(['KC', 'KT', 'KS'])
        if mags == 1:
            packet_types.append('S0')
        if algorithm == 1:
            packet_types.extend(['S2', 'N0', 'N1'])
        if mags == 1 and algorithm == 1:
            packet_types.extend(['A0', 'A1', 'LEGACY500', 'F3'])

    if architecture == 4 or architecture == 5:
        packet_types.extend(['S3', 'A3', 'A5', 'T1', 'F4', 'F5', 'F6', 'F7'])

    if architecture == 2 or architecture == 3:
        packet_types.extend(['B1', 'B2'])

    if algorithm == 1:
        packet_types.extend(['A2', 'A4'])

    packet_types.sort()
    return packet_types
