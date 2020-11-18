import sys
import time

try:
    raise Exception('use local code')
except:
    sys.path.append('./src')
    from aceinna.framework.utils import helper
    from aceinna.devices.decorator import with_device_message
    from aceinna.tools import Detector

global MESSAGE_CENTER
global PROERTIES


def on_find_device(device):
    '''
    callback after find device
    '''
    global MESSAGE_CENTER
    global PROERTIES
    device.setup(None)

    PROERTIES = device.properties
    MESSAGE_CENTER = device._message_center

    #send_ping_command()

    print('1. Request status (command 0)')
    send_mag_status_command()
    time.sleep(1)

    print('2. Start auto alignment (command 1)')
    send_mag_start_command()
    time.sleep(1)

    print('3. Request status')
    send_mag_status_command()
    time.sleep(1)

    print('4. Rotate device around it’s Z-axis until automatic response send back n=by unit (message “CD” or “CB”)')
    while True:
        user_input = input()
        if user_input == 'ok':
            mag_status_result = send_mag_status_command()

            if mag_status_result['data'] == [0]:
                print('5. Request status (command 0) – status 0 returned \n')
                break
            else:
                print('5. Request status (command 0) – status {0} returned, continue rotate \n'.format(
                    mag_status_result['data']))

    time.sleep(1)

    print('6. quest values (command 7) and check them')
    send_mag_request_values_command()
    time.sleep(1)

    print('7.Accept/save values using command 5.')
    send_mag_save_values_command()

    print('---- Going to sleep 5s, to wait the Algorithm reset ----\n')
    time.sleep(3)

    print('8. Send pG')
    send_ping_command()
    time.sleep(1)

    print('9. Send gA')
    send_get_all_parameters_command()
    time.sleep(1)

    device.close()


@with_device_message
def send_ping_command():
    command_line = helper.build_input_packet('pG')
    result = yield MESSAGE_CENTER.build(command=command_line, timeout=3)
    print('pG result: {0}\n'.format(result['data']))
    return result


@with_device_message
def send_get_all_parameters_command():
    command_line = helper.build_input_packet('gA')
    result = yield MESSAGE_CENTER.build(command=command_line)
    print('gA result: {0} \n'.format(result['data']))
    return result


@with_device_message
def send_mag_status_command():
    command_line = helper.build_input_packet(
        'ma', PROERTIES, 'status')  # 0
    result = yield MESSAGE_CENTER.build(command=command_line)
    print('ma status result: {0} \n'.format(result['data']))
    return result


@with_device_message
def send_mag_start_command():
    command_line = helper.build_input_packet(
        'ma',  PROERTIES, 'start')  # 1
    result = yield MESSAGE_CENTER.build(command=command_line)
    print('ma start result: {0} \n'.format(result['data']))
    return result


@with_device_message
def send_mag_request_values_command():
    command_line = helper.build_input_packet(
        'ma',  PROERTIES, 'stored')  # 7
    result = yield MESSAGE_CENTER.build(command=command_line)
    print('ma request values result: {0} \n'.format(result['data']))
    return result


@with_device_message
def send_mag_save_values_command():
    command_line = helper.build_input_packet('ma', PROERTIES, 'save')  # 5
    result = yield MESSAGE_CENTER.build(command=command_line)
    print('ma save values result: {0} \n'.format(result['data']))
    return result


def simple_start():
    detector = Detector()
    detector.find(on_find_device)


if __name__ == '__main__':
    simple_start()
