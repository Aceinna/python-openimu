import sys
import time
try:
    from aceinna.tools import Detector
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.tools import Detector


def on_find_device(device):
    '''
    callback after find device
    '''
    device.setup(None)
    # start log
    device.start_data_log()

    print('Logging...')
    time.sleep(10)
    # stop log
    device.stop_data_log()
    device.close()


def simple_start():
    detector = Detector()
    detector.find(on_find_device)


def parameters_start():
    detector = Detector(
        device_type='IMU',
        com_port='COM1',
        baudrate=115200
    )
    detector.find(on_find_device)

if __name__ == '__main__':
    simple_start()
    # parameters_start()
