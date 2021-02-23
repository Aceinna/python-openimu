from .event_base import EventBase
from ..framework.communicator import CommunicatorFactory
from ..models import WebserverArgs


DEFAULT_PROTOCOL = 'uart'


class DriverEvents:
    ''' Driver Events
    '''
    Discovered = 'DISCOVERED'
    Lost = 'LOST'
    UpgradeStart = 'UPGRADE_START'
    UpgradeFail = 'UPGRADE_FAIL'
    UpgradeProgress = 'UPGRADE_PROGRESS'
    UpgradeFinished = 'UPGRADE_FINISHED'
    Continous = 'CONTINOUS'
    Error = 'ERROR'


class Driver(EventBase):
    ''' Aceinna Device Interface
    '''

    def __init__(self, options):
        super(Driver, self).__init__()
        self._options = options
        self._communicator = None
        self._device_provider = None
        self._with_exception = False
        # self._build_options(**options)
        self._protcol = self._options.protocol.lower() \
            if self._options.protocol is not None else DEFAULT_PROTOCOL

    def _device_discover_handler(self, device_provider):
        '''
        Handler after device discovered
        '''
        # close the exception provider
        if self._with_exception:
            self._device_provider.close()
            self._with_exception = False

        # load device provider
        self._load_device_provider(device_provider)
        # dicovered device
        self.emit(DriverEvents.Discovered, device_provider)

    def _device_upgrade_restart_handler(self, device_provider):
        '''
        Handler after device upgrade complete
        '''
        self._device_provider = device_provider
        self._device_provider.upgrade_completed(self._options)
        self.emit(DriverEvents.UpgradeFinished)

    def _load_device_provider(self, device_provider):
        '''
        Load device provider
        '''
        self._device_provider = device_provider
        self._device_provider.setup(self._options)
        self._device_provider.on('exception', self._handle_device_exception)
        self._device_provider.on(
            'upgrade_restart', self._handle_device_upgrade_restart)
        self._device_provider.on(
            'continous', self._handle_receive_continous_data)

    def _handle_device_exception(self, error, message):
        # TODO: check the error type
        self.emit(DriverEvents.Error, error, message)
        self._with_exception = True
        # detect the device again if the error is communication lost
        # allow user to set if auto detect if there is an communication error
        self._device_provider.reset()
        self._communicator.find_device(self._device_discover_handler)

    def _handle_device_upgrade_restart(self):
        self._communicator.find_device(self._device_upgrade_restart_handler)

    def _handle_receive_continous_data(self, packet_type, data):
        self.emit(DriverEvents.Continous, packet_type, data)

    def detect(self):
        ''' Detect aceinna device
        '''
        '''find if there is a connected device'''
        if self._communicator is None:
            self._communicator = CommunicatorFactory.create(
                self._protcol, self._options)

        self._communicator.find_device(self._device_discover_handler)

    def execute(self, method, parameters=None):
        ''' Execute command on device
        '''
        return getattr(self._device_provider, method, None)(parameters)
