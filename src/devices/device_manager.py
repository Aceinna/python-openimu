from .openimu.uart_provider import Provider as OpenIMUProvider
from .openrtk.uart_provider import Provider as OpenRTKProvider


class DeviceManager:
    device_list = []

    def __init__():
        pass

    @staticmethod
    def ping(communicator, new_ping=False):
        if new_ping:
            DeviceManager.device_list = []

        if communicator.type == 'uart':
            if len(DeviceManager.device_list) == 0:
                DeviceManager.device_list.append(OpenIMUProvider(communicator))
                DeviceManager.device_list.append(OpenRTKProvider(communicator))
                
        for device in DeviceManager.device_list:
            can_ping = device.ping()
            if can_ping:
                return device
        return None
