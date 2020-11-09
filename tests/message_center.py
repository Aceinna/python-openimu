import os
import sys
import json
import time

try:
    from aceinna.devices.message_center import DeviceMessageCenter
    from aceinna.devices.parser_manager import ParserManager
    from aceinna.framework.utils import helper
    from mocker.communicator import MockCommunicator
    from mocker.devices import helper as test_helper
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    # sys.path.append('./tests')
    from aceinna.devices.message_center import DeviceMessageCenter
    from aceinna.devices.parser_manager import ParserManager
    from aceinna.framework.utils import helper
    from mocker.communicator import MockCommunicator
    from mocker.devices import helper as test_helper


global MOCK_COMMUNICATOR
global MESSAGE_CENTER

MOCK_COMMUNICATOR = False
MESSAGE_CENTER = None

DEVICE_TYPE = APP_NAME = 'IMU'
APP_FILE_PATH = os.path.join(
    os.getcwd(), 'setting', 'openimu', APP_NAME, 'openimu.json')
PROPERTIES = None
with open(APP_FILE_PATH) as json_data:
    PROPERTIES = json.load(json_data)


def setup_message_center():
    global MESSAGE_CENTER
    global MOCK_COMMUNICATOR

    # port = '/dev/cu.usbserial-AK005M29'
    # baud = 115200
    # uart = serial.Serial(port, baud, timeout=0.1)
    MOCK_COMMUNICATOR = MockCommunicator(options={'device': DEVICE_TYPE})

    MESSAGE_CENTER = DeviceMessageCenter(MOCK_COMMUNICATOR)
    parser = ParserManager.build(
        DEVICE_TYPE, 'uart', PROPERTIES)
    MESSAGE_CENTER.set_parser(parser)
    #MESSAGE_CENTER.on('continuous_message', handle_message)
    MESSAGE_CENTER.setup()


def close_message_center():
    MESSAGE_CENTER.stop()
    MOCK_COMMUNICATOR.close()


def handle_message(packet_type, data):
    # parse continuous data
    print(packet_type, data)


def receive_messasge(packet_type, data, error):
    print(packet_type, data, error)


def build_and_send(command, **params):
    properties = params.get('properties')
    param_id = params.get('param_id')
    param_value = params.get('param_value')
    delay = params.get('delay')

    cli = helper.build_input_packet(
        command, properties=properties, param=param_id, value=param_value)
    if delay and delay > 0:
        msg = MESSAGE_CENTER.build(
            command=test_helper.wrap_delay_response_command(cli, delay), timeout=1)
    else:
        msg = MESSAGE_CENTER.build(command=cli, timeout=2)
    msg.on('finished', receive_messasge)
    msg.send()


if __name__ == '__main__':
    setup_message_center()

    # ping device
    build_and_send('pG')
    # get device version with delay response
    build_and_send('gV', delay=3)
    # ping device
    build_and_send('gA')

    # read the parameter
    build_and_send('gP', properties=PROPERTIES, param_id=3)
    # change parameter
    build_and_send('uP', properties=PROPERTIES, param_id=3, param_value='s1')
    # valid the change
    build_and_send('gP', properties=PROPERTIES, param_id=3)

    # send a invalid response command
    build_and_send('NA')
    # check if still work
    build_and_send('gP', properties=PROPERTIES, param_id=3)

    time.sleep(5)
    # stop message center after 1s
    close_message_center()
