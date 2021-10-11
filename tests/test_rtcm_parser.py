import sys
import os
#import unittest

try:
    from aceinna.core.gnss import RTCMParser
    # from aceinna.devices.openrtk.uart_provider import Provider as OpenRTKUartProvider
    # from aceinna.devices.openrtk.lan_provider import Provider as OpenRTKLANProvider
    # from aceinna.devices.rtkl.uart_provider import Provider as OpenRTKLUartProvider
except:
    sys.path.append('./src')
    from aceinna.core.gnss import RTCMParser

global parsed_packet_count
parsed_packet_count = 0


def handle_parsed_data(data):
    global parsed_packet_count
    parsed_packet_count += len(data)


rtcm_parser = RTCMParser()
rtcm_parser.on('parsed', handle_parsed_data)

rtcm_file_path = '/Users/songyiwei/projects/runtime-log/app/server/data/OpenRTK330L-1975000205/1624346077621/rtcm_rover.bin' #os.path.join(os.getcwd(), 'data', 'collect', 'rtcm_base_2021_05_29_09_23_54.bin')

with open(rtcm_file_path, 'rb') as buf_r:
    s = 0
    while True:
        tmp_data = buf_r.read(1024)
        if tmp_data:
            s += 1
            rtcm_parser.receive(tmp_data)
        else:
            break
    print('Found header count:{0}, Parsed parcket count:{1}, CRC passed count:{2}, CRC failed count:{3}'.format(
        rtcm_parser.found_header_count,
        parsed_packet_count,
        rtcm_parser.crc_passed_count,
        rtcm_parser.crc_failed_count
    ))
    print('All is read, read times:', s)
