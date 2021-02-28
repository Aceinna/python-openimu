# from .ping.dmu import ping as ping_dmu
# from .ping.open import ping as ping_opendevice
# from .ping.ins2000 import ping as ping_ins2000
from .ping import ping_tool
from .openimu.uart_provider import Provider as OpenIMUUartProvider
from .openrtk.uart_provider import Provider as OpenRTKUartProvider
from .rtkl.uart_provider import Provider as RTKLUartProvider
from .openrtk.lan_provider import Provider as OpenRTKLANProvider
from .dmu.uart_provider import Provider as DMUUartProvider
from .ins2000.uart_provider import Provider as INS2000UartProvider
from ..framework.context import APP_CONTEXT
from ..framework.utils.print import print_green


def create_provider(device_type, communicator):
    if communicator.type == 'uart':
        if device_type == 'OpenIMU':
            return OpenIMUUartProvider(communicator)
        if device_type == 'OpenRTK':
            return OpenRTKUartProvider(communicator)
        if device_type == 'RTKL':
            return RTKLUartProvider(communicator)
        if device_type == 'DMU':
            return DMUUartProvider(communicator)
        if device_type == 'INS2000':
            return INS2000UartProvider(communicator)

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
    def build_provider(communicator, device_access, ping_info):
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
                provider.communicator = communicator
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

        format_device_info = provider.bind_device_info(
            device_access, device_info, app_info)

        # print(format_device_info)
        print_green(format_device_info)

        APP_CONTEXT.get_logger().logger.info(
            'Connected Device info {0}'.format(format_device_info))

        return provider

    @staticmethod
    def ping(communicator, *args):
        '''
            Find device with ping command
            uart: communicator, device_type
            lan: communicator
        '''
        if communicator.type == 'uart':
            device_access = args[0]
            filter_device_type = args[1]

            ping_result = ping_tool.do_ping(
                communicator.type, device_access, filter_device_type)
            if ping_result is not None:
                return DeviceManager.build_provider(communicator, device_access, ping_result)

            # if filter_device_type is None or filter_device_type in ['IMU', 'RTK', 'RTKL']:
            #     APP_CONTEXT.get_logger().logger.debug(
            #         'Checking if is OpenRTK/OpenIMU/RTK330L device...')
            #     ping_result = ping_opendevice(
            #         device_access, filter_device_type)
            #     if ping_result is not None:
            #         return DeviceManager.build_provider(communicator, device_access, ping_result)

            # if filter_device_type is None or filter_device_type == 'DMU':
            #     APP_CONTEXT.get_logger().logger.debug('Checking if is DMU device...')
            #     ping_result = ping_dmu(device_access, filter_device_type)
            #     if ping_result is not None:
            #         return DeviceManager.build_provider(communicator, device_access, ping_result)

            # if filter_device_type is None or filter_device_type == 'INS2000':
            #     APP_CONTEXT.get_logger().logger.debug('Checking if is INS2000 device...')
            #     ping_result = ping_ins2000(device_access, filter_device_type)
            #     if ping_result is not None:
            #         return DeviceManager.build_provider(communicator, device_access, ping_result)

        if communicator.type == 'lan':
            device_access = args[0]

            ping_result = ping_tool.do_ping(communicator.type, device_access,
                                            None)
            if ping_result is not None:
                return DeviceManager.build_provider(communicator, device_access, ping_result)

        return None
