from global_vars import imu
from imu_input_packet import InputPacket
import binascii
import sys

class OpenIMUMagneticAlign:
    def __init__(self):
        self.version = sys.version_info[0]
        global imu

    def start(self):
        # C = "55556D610101E10F".decode("hex")
        if self.version < 3:
            C = "55556D610101E10F".decode("hex")
        else:
            C = bytes.fromhex('55556D610101E10F')

        print (C)
        imu.write(C)
        # time.sleep(0.05)

    def abort(self):
        # C = "55556D61010691E8".decode("hex")
        if self.version < 3:
            C = "55556D61010691E8".decode("hex")
        else:
            C = bytes.fromhex('55556D61010691E8')
        imu.write(C)

    def save(self):
        # C = "55556d610105A18B".decode("hex")
        if self.version < 3:
            C = "55556d610105A18B".decode("hex")
        else:
            C = bytes.fromhex('55556d610105A18B')

        imu.write(C)

    def status(self):
        # C = "55556D610100F12E".decode("hex")
        if self.version < 3:
            C = "55556D610100F12E".decode("hex")
        else:
            C = bytes.fromhex('55556D610100F12E')

        imu.write(C)

        returnedStatus = imu.ser.readline().strip()
        print (binascii.hexlify(returnedStatus))

        if self.version < 3:
            decodedStatus = binascii.hexlify(returnedStatus)
        else:
            decodedStatus = str(binascii.hexlify(returnedStatus), 'utf-8')

        if 'f12e' in decodedStatus:
            return 1
