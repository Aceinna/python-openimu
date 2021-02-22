import os
import sys
import json
import time
import unittest

try:
    from aceinna.devices.message_center import DeviceMessageCenter
    from aceinna.devices.parser_manager import ParserManager
    from aceinna.framework.utils import helper
    from aceinna.devices.decorator import with_device_message
    from aceinna.devices.parsers.open_field_parser import (
        decode_value, encode_value)
    from mocker.communicator import MockCommunicator
    from mocker.devices import helper as test_helper
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    # sys.path.append('./tests')
    from aceinna.devices.message_center import DeviceMessageCenter
    from aceinna.devices.parser_manager import ParserManager
    from aceinna.framework.utils import helper
    from aceinna.devices.decorator import with_device_message
    from aceinna.devices.parsers.open_field_parser import (
        decode_value, encode_value)
    from mocker.communicator import MockCommunicator
    from mocker.devices import helper as test_helper

global MOCK_COMMUNICATOR
global MESSAGE_CENTER

MOCK_COMMUNICATOR = False
MESSAGE_CENTER = None

DEVICE_TYPE = APP_NAME = 'IMU'
APP_FILE_PATH = os.path.join(
    os.getcwd(), 'src', 'aceinna', 'setting', 'OpenIMU300ZI', APP_NAME, 'openimu.json')
PROPERTIES = None
with open(APP_FILE_PATH) as json_data:
    PROPERTIES = json.load(json_data)


def setup_message_center():
    global MESSAGE_CENTER
    global MOCK_COMMUNICATOR

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


@with_device_message
def send_ping_command():
    command_line = helper.build_input_packet('pG')
    result = yield MESSAGE_CENTER.build(command=command_line)
    return result


@with_device_message
def send_get_all_parameters_command():
    command_line = helper.build_input_packet('gA')
    result = yield MESSAGE_CENTER.build(command=command_line)
    return result


@with_device_message
def send_get_parameter_command():
    # get packet type
    command_line = helper.build_input_packet(
        'gP', properties=PROPERTIES, param=3)
    result = yield MESSAGE_CENTER.build(command=command_line)
    return result


@with_device_message
def send_get_version_command():
    delay = 2
    command_line = helper.build_input_packet('gV')
    result = yield MESSAGE_CENTER.build(
        command=command_line)
    return result


@with_device_message
def send_get_version_timeout_command():
    delay = 2
    command_line = helper.build_input_packet('gV')
    result = yield MESSAGE_CENTER.build(
        command=test_helper.wrap_delay_response_command(command_line, delay), timeout=1)
    return result


@with_device_message
def send_invalid_response_message():
    command_line = helper.build_input_packet('NA')
    result = yield MESSAGE_CENTER.build(
        command=command_line)
    return result


class TestDeviceMessageWrapper(unittest.TestCase):
    '''
    Test send command with decorator
    '''

    def test_one_message(self):
        setup_message_center()

        result = send_ping_command()
        self.assertFalse(result['error'], 'Got result')

        close_message_center()

    def test_more_same_messages(self):
        setup_message_center()

        result1 = send_ping_command()
        result2 = send_ping_command()
        result3 = send_ping_command()
        command_result = [
            result1['packet_type'], result1['error'],
            result2['packet_type'], result2['error'],
            result3['packet_type'], result3['error']
        ]
        expect_result = ['pG', False, 'pG', False, 'pG', False]
        self.assertEqual(command_result, expect_result, 'Got more result')

        close_message_center()

    def test_more_different_messages(self):
        setup_message_center()

        result1 = send_ping_command()
        result2 = send_get_all_parameters_command()
        result3 = send_get_parameter_command()
        command_result = [
            result1['packet_type'], result1['error'],
            result2['packet_type'], result2['error'],
            result3['packet_type'], result3['error']
        ]
        expect_result = [
            'pG', False, 'gA', False, 'gP', False
        ]
        self.assertEqual(command_result, expect_result,
                         'Got more different result')

        close_message_center()

    def test_timeout_message(self):
        setup_message_center()

        result = send_get_version_timeout_command()
        self.assertTrue(result['error'] == 'Timeout', 'Got timeout result')

        close_message_center()

    def test_get_message_after_timeout_message(self):
        setup_message_center()

        result1 = send_ping_command()
        result2 = send_get_version_timeout_command()
        # for test, wait 1s, if it is a timeout command, but we should handle the timeout error
        time.sleep(1)
        result3 = send_get_parameter_command()
        command_result = [
            result1['packet_type'],
            result2['packet_type'],
            result2['error'],
            result3['packet_type'],
            result3['error'],
        ]
        expect_result = ['pG', 'gV', 'Timeout', 'gP', False]
        self.assertEqual(command_result, expect_result,
                         'Got result after timeout')
        close_message_center()

    def test_get_message_if_first_is_timeout(self):
        setup_message_center()

        result1 = send_ping_command()
        result2 = send_get_version_timeout_command()
        # for test, wait 1s, if it is a timeout command, but we should handle the timeout error
        time.sleep(1)
        result3 = send_get_version_command()
        command_result = [
            result1['packet_type'],
            result2['packet_type'],
            result2['error'],
            result3['packet_type'],
            result3['error']
        ]
        expect_result = ['pG', 'gV', 'Timeout', 'gV', False]
        self.assertEqual(command_result, expect_result,
                         'Got result after timeout')
        close_message_center()

    def test_invalid_response_message(self):
        setup_message_center()

        result = send_invalid_response_message()
        self.assertEqual(result['packet_type'], 'NA')

        close_message_center()


if __name__ == '__main__':
    unittest.main()
