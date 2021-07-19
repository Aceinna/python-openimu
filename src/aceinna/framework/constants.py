# Device
DEVICE_TYPES = ['IMU', 'RTK', 'DMU']
BAUDRATE_LIST = [460800, 115200, 57600, 230400, 38400]
DEFAULT_PORT_RANGE = [8000, 8001, 8002, 8003]


class APP_TYPE:
    DEFAULT = 'default'
    CLI = 'cli'
    RECEIVER = 'receiver'
    LOG_PARSER = 'log-parser'


class INTERFACES(object):
    UART = 'uart'
    ETH = 'eth'
    ETH_100BASE_T1 = '100base-t1'

    def list():
        return [INTERFACES.UART, INTERFACES.ETH, INTERFACES.ETH_100BASE_T1]
