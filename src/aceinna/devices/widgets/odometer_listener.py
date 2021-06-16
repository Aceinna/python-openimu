import os
import sys
import can
import time
import threading
import random
from ...core.event_base import EventBase


def parse_wheel_speed(data):
    '''
    Parse WHEEL_SPEEDS info from Toyota Corolla.

    in: CAN msg
    out: in [km/h]
        WHEEL_SPEED_FR
        WHEEL_SPEED_FL
        WHEEL_SPEED_RR
        WHEEL_SPEED_RL

    dbc: MSB, unsigned
        BO_ 170 WHEEL_SPEEDS: 8 XXX
        SG_ WHEEL_SPEED_FR : 7|16@0+ (0.01,-67.67) [0|250] "kph" XXX
        SG_ WHEEL_SPEED_FL : 23|16@0+ (0.01,-67.67) [0|250] "kph" XXX
        SG_ WHEEL_SPEED_RR : 39|16@0+ (0.01,-67.67) [0|250] "kph" XXX
        SG_ WHEEL_SPEED_RL : 55
        |16@0+ (0.01,-67.67) [0|250] "kph" XXX
    '''
    offset = -67.67
    speed_fr = (data[0] * 256 + data[1]) * 0.01 + offset
    speed_fl = (data[2] * 256 + data[3]) * 0.01 + offset
    speed_rr = (data[4] * 256 + data[5]) * 0.01 + offset
    speed_rl = (data[6] * 256 + data[7]) * 0.01 + offset
    return (speed_fr, speed_fl, speed_rr, speed_rl)


def parse_msg(message_type, data):
    parse_result = None
    if message_type == 'WHEEL_SPEED':
        parse_result = parse_wheel_speed(data)

    if not parse_result:
        return True, None

    return False, parse_result


class CanOptions:
    _channel: str
    _bitrate: int

    def __init__(self, channel: str, bitrate: int) -> None:
        self._channel = channel
        self._bitrate = bitrate

    @property
    def channel(self):
        return self._channel

    @property
    def bitrate(self):
        return self._bitrate


class mock_can_message:
    arbitration_id = 0
    data = []


def mock_speed_message():
    speed_data = []
    for _ in range(8):
        speed_data.append(random.randint(1, 255))

    msg = mock_can_message()
    msg.arbitration_id = 0xAA
    msg.data = speed_data
    return msg


is_linux = sys.platform == 'linux'


class OdometerListener(EventBase):
    def __init__(self, options: CanOptions):
        super(OdometerListener, self).__init__()

        if not is_linux:
            return

        # close can0
        os.system('sudo ifconfig {0} down'.format(options.channel))
        # set bitrate of can0
        os.system('sudo ip link set {0} type can bitrate {1}'.format(
            options.channel, options.bitrate))
        # open can0
        os.system('sudo ifconfig {0} up'.format(options.channel))
        # os.system('sudo /sbin/ip link set can0 up type can bitrate 250000')
        # show details can0 for debug.
        # os.system('sudo ip -details link show can0')

        # set up can interface.
        # socketcan_native socketcan_ctypes
        self.can0 = can.interface.Bus(
            channel=options.channel, bustype='socketcan_ctypes')
        # set up Notifier
        self.notifier = can.Notifier(self.can0, [self.msg_handler])

    def msg_handler(self, msg):
        if msg.arbitration_id == 0xAA:
            parse_error, parse_result = parse_msg('WHEEL_SPEED', msg.data)
            if parse_error:
                return
            self.emit('data', parse_result)

    # def __init__(self, options: CanOptions):
    #     super(OdometerListener, self).__init__()
    #     threading.Thread(target=self._receive).start()

    # def _receive(self):
    #     while True:
    #         message = mock_speed_message()
    #         if message.arbitration_id == 0xAA:
    #             parse_error, parse_result = parse_msg('WHEEL_SPEED', message.data)
    #             if parse_error:
    #                 return
    #             self.emit('data', parse_result)
    #         time.sleep(0.001)
