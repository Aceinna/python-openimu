import sys
import time
try:
    from openimu import OpenIMU
except:
    print('load openimu from parent path')
    sys.path.append('.')
    from openimu import OpenIMU

if __name__ == "__main__":
    imu = OpenIMU()
    imu.find_device()
    imu.openimu_get_all_param()
    imu.start_log()
    time.sleep(20)
    imu.stop_log()
