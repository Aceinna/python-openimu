from .openimu.uart_provider import Provider as OpenIMUProvider
from .openimu.uart_provider import Provider as OpenRTKProvider


class DeviceManager:
    def __init__():
        pass

    @staticmethod
    def ping(communicator):
        device_list = []
        if communicator.type =='uart':
            device_list.append(OpenIMUProvider(communicator))
            device_list.append(OpenRTKProvider(communicator))

        for device in device_list:
            can_ping = device.ping()
            if can_ping:
                return device
        return None
