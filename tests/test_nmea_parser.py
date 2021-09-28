import re
import traceback
import time
import cProfile

GPZDA_DATA_LEN = 39

def nmea_checksum(data):
    nmea_str = data[1:len(data) - 2]
    nmeadata = nmea_str[0:len(nmea_str)-3]
    cksum = nmea_str[len(nmea_str)-2:len(nmea_str)]

    calc_cksum = 0
    for s in nmeadata:
        calc_cksum ^= ord(s)
    return int(cksum, 16), calc_cksum

def nmea_checksum_v1(data):
    data = data.replace("\r", "").replace("\n", "").replace("$", "")
    nmeadata, cksum = re.split('\*', data)
    calc_cksum = 0
    for s in nmeadata:
        calc_cksum ^= ord(s)
    return int(cksum, 16), calc_cksum

def parse_nmea_v1(raw_data):
    print('v1')
    print('start', time.time())

    nmea_buffer = []
    nmea_sync = 0

    if raw_data[0] != 0x24:
        return

    for bytedata in raw_data:
        if bytedata == 0x24:
            nmea_buffer = []
            nmea_sync = 0
            nmea_buffer.append(bytedata)
        else:
            nmea_buffer.append(bytedata)
            if nmea_sync == 0:
                if bytedata == 0x0D:
                    nmea_sync = 1
            elif nmea_sync == 1:
                if bytedata == 0x0A:
                    try:
                        str_nmea = bytes(nmea_buffer).decode()
                        cksum, calc_cksum = nmea_checksum(str_nmea)
                        if cksum == calc_cksum:
                            if str_nmea.find("$GPGGA") != -1:
                                pass
                    except Exception as e:
                        pass
                nmea_buffer = []
                nmea_sync = 0

    print('end  ', time.time())

def parse_nmea_v2(raw_data):
    print('v2')
    print('start', time.time())
    if data[0] != 0x24 or data[1] != 0x47 or data[2] != 0x50:
        return

    temp_str_nmea = data.decode('utf-8')
    if (temp_str_nmea.find("\r\n", len(temp_str_nmea)-2, len(temp_str_nmea)) != -1):
        str_nmea = temp_str_nmea
    elif(temp_str_nmea.find("\r\n", GPZDA_DATA_LEN-2, GPZDA_DATA_LEN) != -1):
        str_nmea = temp_str_nmea[0:GPZDA_DATA_LEN]
    else:
        return

    try:
        cksum, calc_cksum = nmea_checksum(str_nmea)
        if cksum == calc_cksum:
            if str_nmea.find("$GPGGA", 0, 6) != -1:
                pass
    except Exception as e:
        print('NMEA fault:{0}'.format(e))
    print('end  ', time.time())

if __name__ == '__main__':
    data = '$GPGGA,042547.00,3129.6667218,N,12021.7694487,E,4,24,0.6,119.227,M,0.000,M,2.0,*7f\r\n'.encode()
    cProfile.run("parse_nmea_v1(data)")
    cProfile.run("parse_nmea_v2(data)")
    #parse_nmea_v1(data)
    #parse_nmea_v2(data)


