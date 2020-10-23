import os
import sys
import json
import time
import serial

try:
    from aceinna.devices.message_center import DeviceMessageCenter
    from aceinna.devices.parser_manager import ParserManager
    from aceinna.framework.utils import helper
    from mocker.communicator import MockCommunicator
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    # sys.path.append('./tests')
    from aceinna.devices.message_center import DeviceMessageCenter
    from aceinna.devices.parser_manager import ParserManager
    from aceinna.framework.utils import helper
    from mocker.communicator import MockCommunicator


global HAS_DATA_FLAG
global MESSAGE_CENTER

HAS_DATA_FLAG = False
MESSAGE_CENTER = None

DEVICE_TYPE = APP_NAME = 'IMU'
APP_FILE_PATH = os.path.join(
    os.getcwd(), 'setting', 'openimu', APP_NAME, 'openimu.json')
PROPERTIES = None
with open(APP_FILE_PATH) as json_data:
    PROPERTIES = json.load(json_data)


def setup_message_center():
    global MESSAGE_CENTER

    # port = '/dev/cu.usbserial-AK005M29'
    # baud = 115200
    # uart = serial.Serial(port, baud, timeout=0.1)
    mock_communicator = MockCommunicator(options={'device': DEVICE_TYPE})

    MESSAGE_CENTER = DeviceMessageCenter(mock_communicator)
    parser = ParserManager.build(
        DEVICE_TYPE, 'uart', PROPERTIES)
    MESSAGE_CENTER.set_parser(parser)
    #MESSAGE_CENTER.on('continuous_message', handle_message)
    MESSAGE_CENTER.setup()


def handle_message(packet_type, data):
    # parse continuous data
    print(packet_type, data)


def receive_messasge(packet_type, data, error):
    print(packet_type, data, error)


if __name__ == '__main__':
    setup_message_center()
    CLI = helper.build_input_packet('pG')
    pG_MSG = MESSAGE_CENTER.build(command=CLI, timeout=1)
    pG_MSG.on('finished', receive_messasge)
    pG_MSG.send()

    CLI = helper.build_input_packet('gV')
    gV_MSG = MESSAGE_CENTER.build(command=CLI, timeout=1)
    gV_MSG.on('finished', receive_messasge)
    gV_MSG.send()

    CLI = helper.build_input_packet('gA')
    gA_MSG = MESSAGE_CENTER.build(command=CLI, timeout=1)
    gA_MSG.on('finished', receive_messasge)
    gA_MSG.send()
    while True:
        pass
