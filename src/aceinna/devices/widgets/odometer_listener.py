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
    speed_rr = (data[4] * 256 + data[5]) * 0.01 + offset
    speed_rl = (data[6] * 256 + data[7]) * 0.01 + offset
    return (speed_rr + speed_rl)/2*1000/3600


def parse_gear(data):
    gear = data & 0x3F
    # P = 32
    if gear == 32:
        return 0

    # R = 16
    if gear == 16:
        return -1

    # N = 8
    if gear == 8:
        return 0

    # D = 0
    if gear == 0:
        return 1

    return 0


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


class WindowsCANReceiver(EventBase):
    def __init__(self, options: CanOptions) -> None:
        super(WindowsCANReceiver, self).__init__()

        self.can = can.interface.Bus(
            channel=options.channel, bustype='canalystii', bitrate=options.bitrate)
        # set up Notifier
        simple_listener = SimpleListener(self)
        self.notifier = can.Notifier(self.can, [simple_listener])


class SimpleListener(can.Listener):
    _receiver = None

    def __init__(self, receiver: WindowsCANReceiver) -> None:
        super().__init__()
        self._receiver = receiver

    def on_message_received(self, msg):
        self._receiver.emit('data', msg)

    def on_error(self, exc):
        print(exc)


class OdometerListener(EventBase):
    _receiver = None
    _wheel_speed: float = 0
    _gear: int = 0
    _received = False

    def __init__(self, options: CanOptions):
        super(OdometerListener, self).__init__()
        self._receiver = WindowsCANReceiver(options)
        self._receiver.on('data', self._msg_handler)

        # start a thread to output data in a duration
        threading.Thread(target=self._emit_data).start()

    def _emit_data(self):
        while True and self._received:
            self.emit('data', self._wheel_speed * self._gear)
            time.sleep(0.05)

    def _msg_handler(self, msg):
        if msg.arbitration_id == 0xAA:
            self._received = True
            self._wheel_speed = parse_wheel_speed(msg.data)

        if msg.arbitration_id == 0x3BC:
            self._received = True
            self._gear = parse_gear(msg.data)
