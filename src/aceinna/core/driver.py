import time
import serial
from .event_base import EventBase
from ..framework.communicator import CommunicatorFactory
from ..devices import DeviceManager
from ..framework.utils.print import print_red

DEFAULT_PROTOCOL = 'uart'

BAUDRATE_MAPPING = {'IMU': 57600}


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
        self._protcol = self._options.protocol.lower() \
            if self._options.protocol is not None else DEFAULT_PROTOCOL

        # self._handler_manager = HandlerManager()
        # self._handler_manager.setup()

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

    def _device_upgrade_failed_handler(self, code, reason):
        self.emit(DriverEvents.UpgradeFail, code, reason)

    def _device_upgrade_restart_handler(self, device_provider):
        '''
        Handler after device upgrade complete
        '''
        self._device_provider = device_provider
        self._device_provider.upgrade_completed(self._options)
        self.emit(DriverEvents.UpgradeFinished)

    def _device_not_found_handler(self):
        if self._device_provider:
            self._device_provider.close()
            self._device_provider = None

        self.emit(DriverEvents.UpgradeFail, 'UPGRADE.FAILED.002',
                  'Cannot detect device after upgrade firmware')
        self.emit(DriverEvents.Lost)
        print_red('Upgrade fail. The device lost.')
        self._communicator.find_device(self._device_discover_handler)

    def _load_device_provider(self, device_provider):
        '''
        Load device provider
        '''
        self._device_provider = device_provider
        self._device_provider.setup(self._options)
        self._device_provider.on('exception', self._handle_device_exception)
        self._device_provider.on('upgrade_failed',
                                 self._device_upgrade_failed_handler)
        self._device_provider.on('upgrade_restart',
                                 self._handle_device_upgrade_restart)
        self._device_provider.on('continous',
                                 self._handle_receive_continous_data)

    def _handle_device_exception(self, error, message):
        # TODO: check the error type
        self.emit(DriverEvents.Error, error, message)
        self._with_exception = True
        # detect the device again if the error is communication lost
        # allow user to set if auto detect if there is an communication error
        self._device_provider.reset()
        self._communicator.find_device(self._device_discover_handler)

    def _handle_device_upgrade_restart(self):
        self._communicator.set_find_options({
            'com_port': self._communicator.serial_port.port,
            'device_type': self._device_provider.type
        })
        self._communicator.find_device(
            self._device_upgrade_restart_handler,
            retries=2,
            not_found_handler=self._device_not_found_handler)

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
        # return self._handler_manager.route(self, method, parameters)

        if method == 'check_mode':
            mode = -1
            if self._device_provider:
                mode = 1 if self._device_provider.is_in_bootloader else 0

            return {
                'packetType': 'mode',
                'data': mode
            }

        if method == 'list_ports':
            ports = self._communicator.list_ports()
            return {
                'packetType': 'ports',
                'data': ports
            }

        if method == 'force_bootloader':
            port_name = parameters['port']
            device_type = parameters['device_type']

            if self._device_provider:
                return {
                    'packetType': 'success',
                    'data': {
                        'status': 0,
                        'message': 'The device is already connected. There is no need to enter bootloader.'
                    }
                }

            self._communicator.pause_find()

            result = self._process_force_bootloader(port_name, device_type)

            # return fail result
            if result['data']['status'] == 0:
                return result

            self._communicator.set_find_options({
                'com_port': port_name,
                'device_type': device_type,
                'baudrate': BAUDRATE_MAPPING[device_type]
            })
            self._communicator.resume_find()

            while not self._device_provider:
                time.sleep(1)

            return result

        return getattr(self._device_provider, method, None)(parameters)

    def _process_force_bootloader(self, port_name, device_type):
        # OpenRTK has a bootloader switch, no need force enter bootloader

        # communicator open
        serial_port = None
        left_time = 10

        while left_time > 0:
            if not serial_port:
                try:
                    serial_port = serial.Serial(
                        port=port_name,
                        baudrate=BAUDRATE_MAPPING[device_type],
                        timeout=0.1)
                except serial.serialutil.SerialException:
                    serial_port = None

                    time.sleep(0.01)
                    left_time -= 0.01
                    continue

            # send JB commands
            serial_port.write([0x55, 0x55, 0x4A, 0x42, 0x00, 0xA0, 0xCE])
            time.sleep(0.02)
            left_time -= 0.02

        # ping as bootloader
        device_provider = DeviceManager.ping(
            self._communicator, serial_port, device_type)

        if serial_port:
            serial_port.close()

        if device_provider:
            return {
                'packetType': 'success',
                'data': {
                    'status': 1
                }
            }

        return {
            'packetType': 'success',
            'data': {
                'status': 0,
                'message': 'Cannot enter bootloader, please try it again.'
            }
        }
