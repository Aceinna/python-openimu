from global_vars import imu
from imu_input_packet import InputPacket
import binascii

class OpenIMUMagneticAlign:
    def __init__(self):
        global imu

    def start(self):
        C = "55556D610101E10F".decode("hex")
        imu.write(C)
        # time.sleep(0.05)

    def abort(self):
        C = "55556D61010691E8".decode("hex")
        imu.write(C)

    def save(self):
        C = "55556d610105A18B".decode("hex")
        imu.write(C)

    def status(selfS):
        C = "55556D610100F12E".decode("hex")
        imu.write(C)

        returnedStatus = imu.ser.readline().strip()
        print  binascii.hexlify(returnedStatus)

        if binascii.hexlify(returnedStatus) == "55556d610100f12e":
            return 1
