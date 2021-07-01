import struct
import threading

from ..models import WebserverArgs
from ..core.driver import (Driver, DriverEvents)
from ..core.device_context import DeviceContext

from ..framework.constants import APP_TYPE
from ..framework.context import APP_CONTEXT
from ..framework.utils import helper
from ..framework.decorator import throttle

from ..devices.widgets import(NTRIPClient, OdometerListener, CanOptions)


class Receiver:
    options = None
    _driver = None
    _ntrip_client = None
    _odometer_listener = None

    def __init__(self, **kwargs) -> None:
        self.options = None
        self._driver = None
        self._ntrip_client = None
        self._odometer_listener = None
        self._build_options(**kwargs)
        APP_CONTEXT.mode = APP_TYPE.RECEIVER

    def listen(self):
        '''
        Prepare components, initialize the application
        '''
        # prepare driver
        threading.Thread(target=self._prepare_driver).start()

    def _build_options(self, **kwargs):
        self.options = WebserverArgs(**kwargs)

    def _prepare_driver(self):
        self._driver = Driver(self.options)

        self._driver.on(DriverEvents.Discovered,
                        self.handle_discovered)
        self._driver.on(DriverEvents.Continous,
                        self.handle_receive_continous_data)

        self._driver.detect()

    def handle_discovered(self, device_provider):
        device_context = DeviceContext(device_provider)
        APP_CONTEXT.device_context = device_context

        # prepare ntrip client
        if not self._ntrip_client:
            threading.Thread(target=self._prepare_ntrip_client).start()

        # prepare odometer listener
        if not self._odometer_listener:
            threading.Thread(target=self._prepare_odometer_listener).start()

    def handle_receive_continous_data(self, packet_type, data):
        if packet_type == 'gga':
            self._ntrip_client.send(data)

    def _prepare_ntrip_client(self):
        self._ntrip_client = NTRIPClient(
            APP_CONTEXT.device_context._provider.properties
        )
        self._ntrip_client.on('parsed', self._handle_data_parsed)
        self._ntrip_client.run()

    def _handle_data_parsed(self, data):
        if self._driver._communicator.can_write():
            self._driver._communicator.write(data)

    def _prepare_odometer_listener(self):
        self._odometer_listener = OdometerListener(CanOptions('can0', 500000))
        self._odometer_listener.on('data', self._handle_wheel_speed_data)

    @throttle(seconds=0.01)
    def _handle_wheel_speed_data(self, data):
        avg_speed = (data[2]+data[3])/2
        speed = avg_speed / 3600 * 1000
        command = helper.build_packet('cA', list(
            struct.unpack("4B", struct.pack("<f", speed))))
        self._driver._communicator.write(command)
