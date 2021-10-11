import sys
import time
import os
import signal
import struct

try:
    from aceinna.core.driver import (Driver, DriverEvents)
    from aceinna.models.args import WebserverArgs
    from aceinna.framework.utils import (helper)
    from aceinna.framework.decorator import handle_application_exception
    from aceinna.devices.openrtk.ethernet_provider import Provider as EhternetProvider
    from aceinna.framework.constants import INTERFACES
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.core.driver import (Driver, DriverEvents)
    from aceinna.models.args import WebserverArgs
    from aceinna.framework.utils import (helper)
    from aceinna.framework.decorator import handle_application_exception
    from aceinna.devices.openrtk.ethernet_provider import Provider as EhternetProvider
    from aceinna.framework.constants import INTERFACES

INPUT_PACKETS = [b'\x01\xcc', b'\x02\xcc', b'\x03\xcc', b'\x04\xcc', b'\x01\x0b', b'\x02\x0b']
user_parameters = [0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]


def get_production_info(dest, src, command):
    message_bytes = []

    command_line = helper.build_ethernet_packet(dest, src, command, message_bytes)
    return command_line

def get_user_configuration_parameters(dest, src, command, field_id):
    message_bytes = []

    field_id_bytes = struct.pack('<I', field_id)
    message_bytes.extend(field_id_bytes)

    command_line = helper.build_ethernet_packet(dest, src, command, message_bytes)
    return command_line

def set_user_configuration(dest, src, command, field_id, field_value):
    message_bytes = []

    field_id_bytes = struct.pack('<I', field_id)
    message_bytes.extend(field_id_bytes)

    if (field_id >= 1) and (field_id < 13):
        field_value_bytes = struct.pack('<f', field_value)
        message_bytes.extend(field_value_bytes)
    else:
        field_value_bytes = struct.pack('<B', field_value)
        message_bytes.extend(field_value_bytes)

    command_line = helper.build_ethernet_packet(dest, src, command, message_bytes)
    return command_line

def save_user_configuration(dest, src, command):
    message_bytes = []

    command_line = helper.build_ethernet_packet(dest, src, command, message_bytes)
    return command_line

def set_base_rtcm_data(dest, src, command, rtcm_data = []):
    message_bytes = []

    message_bytes.extend(rtcm_data)

    command_line = helper.build_ethernet_packet(dest, src, command, message_bytes)
    return command_line

def set_vehicle_speed_data(dest, src, command, field_value):
    message_bytes = []

    field_value_bytes = struct.pack('<f', field_value)
    message_bytes.extend(field_value_bytes)

    command_line = helper.build_ethernet_packet(dest, src, command, message_bytes)
    return command_line


def ethernet_command_send_receive(device_provider:EhternetProvider):
    # get production info
    command_line = get_production_info(device_provider.communicator.get_dst_mac(),
                                       device_provider.communicator.get_src_mac(),
                                       list(INPUT_PACKETS[0]))

    if command_line:
        result = device_provider.send_command(command_line.actual_command)
        print('get_production_info:', result)
    else:
        return False

    #  get user configuration parameters
    for i in range(16):
        command_line = get_user_configuration_parameters(device_provider.communicator.get_dst_mac(),
                                                         device_provider.communicator.get_src_mac(),
                                                         list(INPUT_PACKETS[1]),
                                                         i + 1)
        if command_line:
            result = device_provider.send_command(command_line.actual_command)
            print('get_user_configuration_parameters:', result)
        else:
            return False

    # set user configuration
    for i in range(16):
        command_line = set_user_configuration(device_provider.communicator.get_dst_mac(),
                                              device_provider.communicator.get_src_mac(),
                                              list(INPUT_PACKETS[2]),
                                              i + 1,
                                              user_parameters[i])
        if command_line:
            result = device_provider.send_command(command_line.actual_command)
            print('set_user_configuration:', result)
        else:
            return False


    # save user configuration
    command_line = save_user_configuration(device_provider.communicator.get_dst_mac(),
                                       device_provider.communicator.get_src_mac(),
                                       list(INPUT_PACKETS[3]))

    if command_line:
        result = device_provider.send_command(command_line.actual_command)
        print('save_user_configuration:', result)
    else:
        return False

    # set vehicle speed data
    vehicle_speed_value = 80
    command_line = set_vehicle_speed_data(device_provider.communicator.get_dst_mac(),
                                         device_provider.communicator.get_src_mac(),
                                         list(INPUT_PACKETS[4]),
                                         vehicle_speed_value)

    if command_line:
        device_provider.communicator.write(command_line.actual_command)
        print('set_vehicle_speed_data')
    else:
        return False

    # set base rtcm data
    # rtcm_data = [1, 2, 3, 4, 5, 6, 7, 8]
    # command_line = set_base_rtcm_data(device_provider.communicator.get_dst_mac(),
    #                                   device_provider.communicator.get_src_mac(),
    #                                   list(INPUT_PACKETS[5]),
    #                                   rtcm_data)

    # if command_line:
    #     result = device_provider.communicator.write(command_line)
    #     print('set_base_rtcm_data')
    # else:
    #     return False
    return True

def handle_discovered(device_provider):
    result = ethernet_command_send_receive(device_provider)
    if result:
        print('ethernet command test ok.')
    else:
        print('ethernet command test error.')

def kill_app(signal_int, call_back):
    '''Kill main thread
    '''
    os.kill(os.getpid(), signal.SIGTERM)
    sys.exit()

@handle_application_exception
def simple_start():
    driver = Driver(WebserverArgs(
        interface=INTERFACES.ETH_100BASE_T1
    ))
    driver.on(DriverEvents.Discovered, handle_discovered)
    driver.detect()


if __name__ == '__main__':
    simple_start()

    while  True:
        signal.signal(signal.SIGINT, kill_app)




