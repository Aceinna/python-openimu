import json 
import struct
import sys

class BootloaderInputPacket:

    def __init__(self, imu_properties, name, data_len = False, addr = False, data = False):
        
        self.name = name
        self.imu_properties = imu_properties

        # get name byte pair
        name_bytes =  list(struct.unpack('BB', bytearray(name, 'utf-8')))

        if not data_len and not addr and not data:
            S = [0x55, 0x55] + name_bytes + [0]  
            self.bytes = S + self.calc_crc(S[2:4] + [0x00])  
        else:
            payload = self.block_payload(data_len, addr, data)
            S = [0x55, 0x55] + name_bytes + [data_len+5] + payload
            self.bytes = S + self.calc_crc(S[2:S[4]+5])   

    def block_payload(self, data_len, addr, data):
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