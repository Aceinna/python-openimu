from .dmu import ping as ping_dmu
from .open import ping as ping_opendevice
from .ins2000 import ping as ping_ins2000
from ...framework.context import APP_CONTEXT


def do_ping(communicator_type, device_access, filter_device_type):
    if communicator_type == 'uart':
        if filter_device_type is None or filter_device_type in ['IMU', 'RTK', 'RTKL']:
            APP_CONTEXT.get_logger().logger.debug(
                'Checking if is OpenRTK/OpenIMU/RTK330L device...')
            ping_result = ping_opendevice(
                device_access, filter_device_type)
            if ping_result:
                return ping_result

        if filter_device_type is None or filter_device_type == 'DMU':
            APP_CONTEXT.get_logger().logger.debug('Checking if is DMU device...')
            ping_result = ping_dmu(device_access, filter_device_type)
            if ping_result:
                return ping_result

        if filter_device_type is None or filter_device_type == 'INS2000':
            APP_CONTEXT.get_logger().logger.debug('Checking if is INS2000 device...')
            ping_result = ping_ins2000(device_access, filter_device_type)
            if ping_result:
                return ping_result

    if communicator_type == 'lan':
        APP_CONTEXT.get_logger().logger.debug('Checking if is OpenRTK device...')
        ping_result = ping_opendevice(device_access, None)
        if ping_result:
            return ping_result

    return None
