
import sys
try:
    from aceinna.devices.message_center import DeviceMessageCenter
    from aceinna.bootstrap import Webserver
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.devices.message_center import DeviceMessageCenter
    from aceinna.bootstrap import Webserver

def simple_start():
    app = Webserver()
    app.listen()


def parameters_start():
    app = Webserver(
        device_type='IMU',
        com_port='COM1',
        port=8001,
        baudrate=115200,
        debug=True)
    app.listen()


if __name__ == '__main__':
    simple_start()
