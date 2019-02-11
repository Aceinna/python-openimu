import json 
import struct

class InputPacket:

    def __init__(self, imu_properties, name, param = False, value = False):
        
        self.name = name
        self.imu_properties = imu_properties

        # get name byte pair
        name_bytes =  list(struct.unpack('BB', bytearray(name, 'utf-8')))

        if not param and not value:
            S = [0x55, 0x55] + name_bytes + [0]  
            self.bytes = S + self.calc_crc(S[2:4] + [0x00])  
        else:
            payload = self.unpack_payload(param, value)
            S = [0x55, 0x55] + name_bytes + [len(payload)] + payload
            self.bytes = S + self.calc_crc(S[2:S[4]+5])   

    def unpack_payload(self, param = False, value = False):
        input_packet = next((x for x in self.imu_properties['userMessages']['inputPackets'] if x['name'] == self.name), None)
        if input_packet != None:
            if input_packet['inputPayload']['type'] == 'paramId':
                return list(struct.unpack("4B", struct.pack("<L", param)))
            elif input_packet['inputPayload']['type'] == 'userParameter':
                payload = list(struct.unpack("4B", struct.pack("<L", param)))
                if self.imu_properties['userConfiguration'][param]['type'] == 'char8':
                    length = len(value)
                    payload += list(struct.unpack('{0}B'.format(length), bytearray(value,'utf-8')))
                    for i in range(8-length):
                        payload += [0x00]
                elif self.imu_properties['userConfiguration'][param]['type'] == 'int64':
                    payload += list(struct.unpack("8B", struct.pack("<q", value)))
                return payload
    
    def calc_crc(self,payload):
        '''Calculates 16-bit CRC-CCITT
        '''
        crc = 0x1D0F
        for bytedata in payload:
           crc = crc^(bytedata << 8) 
           for i in range(0,8):
                if crc & 0x8000:
                    crc = (crc << 1)^0x1021
                else:
                    crc = crc << 1

        crc = crc & 0xffff
        crc_msb = (crc & 0xFF00) >> 8
        crc_lsb = (crc & 0x00FF)
        return [ crc_msb, crc_lsb ]
