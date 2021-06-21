from ..devices.base.provider_base import OpenDeviceBase


class DeviceStatus:
    Idle = 'IDLE'
    MagAlign = 'MAG_ALIGN'
    Upgrading = 'UPGRADING'
    Logging = 'LOGGING'


class DeviceContext:
    _provider = None

    def __init__(self, device_provider):
        self._provider = device_provider

    @property
    def connected(self):
        ''' If the device can be detected
        '''
        if not self._provider:
            return False

        return self._provider.connected

    def check_allow_method(self, method):
        ''' Check if the method is belong to the provider
        '''
        if not self._provider:
            return False

        return hasattr(self._provider, method)

    @property
    def runtime_status(self):
        ''' Retrive the runtime status of the device
        '''
        if not self.connected:
            raise Exception(
                'Cannot access runtime status, when the device is disconnected')

        operation_status = self._provider.get_operation_status()
        if operation_status:
            return operation_status

        return DeviceStatus.Idle

    @property
    def device_type(self):
        return self._provider.type

    @property
    def properties(self):
        return self._provider.properties

    @property
    def get_log_info(self):
        return self._provider.get_log_info()

    def update_provider(self, device_provider):
        ''' It is better to update the provider when device is changed
        '''
        self._provider = device_provider
