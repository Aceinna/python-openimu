from .ping.dmu import ping as ping_dmu
from .ping.open import ping as ping_opendevice
from .openimu.uart_provider import Provider as OpenIMUUartProvider
from .openrtk.uart_provider import Provider as OpenRTKUartProvider
from .dmu.uart_provider import Provider as DMUUartProvider
from ..framework.context import APP_CONTEXT


def create_provider(device_type, communicator):
    if communicator.type == 'uart':
        if device_type == 'OpenIMU':
            return OpenIMUUartProvider(communicator)
        if device_type == 'OpenRTK':
            return OpenRTKUartProvider(communicator)
        if device_type == 'DMU':
            return DMUUartProvider(communicator)

    if communicator.type == 'lan':
        if device_type == 'OpenRTK':
            return OpenRTKLANProvider(communicator)

    return None


class DeviceManager:
    '''
    Manage devices
    '''
    device_list = []

    @staticmethod
    def build_provider(communicator, ping_info):
        if ping_info is None:
            return None

        device_type = ping_info['device_type']
        device_info = ping_info['device_info']
        app_info = ping_info['app_info']

        provider = None
        # find provider from cached device_list
        for index in range(len(DeviceManager.device_list)):
            exist_device = DeviceManager.device_list[index]
            if exist_device['device_type'] == device_type and \
                    exist_device['communicator_type'] == communicator.type:
                provider = exist_device['provider']
                break

        if provider is None:
            provider = create_provider(device_type, communicator)

            if provider is None:
                return None

            DeviceManager.device_list.append({
                'device_type': device_type,
                'communicator_type': communicator.type,
                'provider': provider
            })

        format_device_info = provider.update_device_info(device_info, app_info)
        
        print(format_device_info)

        APP_CONTEXT.get_logger().logger.info(
            'Connected Device info {0}'.format(format_device_info))

        return provider

    @staticmethod
    def ping(communicator, *args):
        if communicator.type == 'uart':
            actual_communicator = args[0]
            filter_device_type = args[1]

            if filter_device_type == None or filter_device_type == 'IMU' or filter_device_type == 'RTK':
                APP_CONTEXT.get_logger().logger.debug('Checking if is OpenRTK/OpenIMU device...')
                ping_result = ping_opendevice(
                    actual_communicator, filter_device_type)
                if ping_result is not None:
                    return DeviceManager.build_provider(communicator, ping_result)

            if filter_device_type == None or filter_device_type == 'DMU':
                APP_CONTEXT.get_logger().logger.debug('Checking if is DMU device...')
                ping_result = ping_dmu(actual_communicator, filter_device_type)
                if ping_result is not None:
                    return DeviceManager.build_provider(communicator, ping_result)

        if communicator.type == 'lan':
            actual_communicator = args[0]

            APP_CONTEXT.get_logger().logger.debug('Checking if is OpenRTK device...')
            ping_result = ping_opendevice(actual_communicator, None)
            if ping_result is not None:
                return DeviceManager.build_provider(communicator, ping_result)

        return None
