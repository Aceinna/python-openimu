from .openimu.uart_provider import Provider as OpenIMUProvider
from .openrtk.uart_provider import Provider as OpenRTKProvider


class DeviceManager:
    '''
    Manage devices
    '''
    device_list = []

    @staticmethod
    def ping(communicator, *args):
        '''
        Find the matched device
        '''
        filter_device_type = args[0]

        if communicator.type == 'uart':
            if len(DeviceManager.device_list) == 0:
                DeviceManager.device_list.append(OpenIMUProvider(communicator))
                DeviceManager.device_list.append(OpenRTKProvider(communicator))

        for device in DeviceManager.device_list:
            if filter_device_type and device.type != filter_device_type:
                continue

            can_ping = device.ping()
            if can_ping:
                return device
        return None
