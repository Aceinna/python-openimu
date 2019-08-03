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
        command = imu.imu_properties['MagCommands'][0]['start']

        if self.version < 3:
            C = command.decode("hex")
        else:
            C = bytes.fromhex(command)

        print (C)
        imu.write(C)
        # time.sleep(0.05)

    def abort(self):
        # C = "55556D61010691E8".decode("hex")
        command = imu.imu_properties['MagCommands'][1]['abort']
        if self.version < 3:
            C =command.decode("hex")
        else:
            C = bytes.fromhex(command)
        imu.write(C)

    def save(self):
        # C = "55556d610105A18B".decode("hex")
        command = imu.imu_properties['MagCommands'][3]['save']
        if self.version < 3:
            C = command.decode("hex")
        else:
            C = bytes.fromhex(command)

        imu.write(C)

    def status(self):
        # C = "55556D610100F12E".decode("hex")
        command = imu.imu_properties['MagCommands'][2]['status']
        if self.version < 3:
            C = command.decode("hex")
        else:
            C = bytes.fromhex(command)

        imu.write(C)

        returnedStatus = imu.ser.readline().strip()
        print (binascii.hexlify(returnedStatus))

        if self.version < 3:
            decodedStatus = binascii.hexlify(returnedStatus)
        else:
            decodedStatus = str(binascii.hexlify(returnedStatus), 'utf-8')

        if 'f12e' in decodedStatus:
            return 1
