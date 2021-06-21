"""
Default App entry
"""
import os
import sys
import time
import threading
from ..models import WebserverArgs

from ..core.driver import (Driver, DriverEvents)
from ..core.device_context import DeviceContext
from ..core.tunnel_web import WebServer
from ..core.tunnel_base import TunnelEvents

from ..framework import AppLogger
from ..framework.utils import resource
from ..framework.context import APP_CONTEXT


class Default:
    '''Default entry class
    '''
    options = None
    _tunnel = None
    _driver = None

    def __init__(self, **kwargs):
        self._build_options(**kwargs)

    def listen(self):
        '''
        Prepare components, initialize the application
        '''
        # prepare driver
        threading.Thread(target=self._prepare_driver).start()
        # prepare tunnel
        threading.Thread(target=self._prepare_tunnel).start()
        # prepage logger
        self._prepare_logger()

    def handle_discovered(self, device_provider):
        device_context = DeviceContext(device_provider)
        APP_CONTEXT.device_context = device_context

        self._tunnel.notify('discovered')

    def handle_lost(self):
        self._tunnel.notify('lost')

    def handle_upgrade_finished(self):
        self._tunnel.notify('continous', 'upgrade_complete', {'success': True})

    def handle_upgrade_fail(self, code, message):
        self._tunnel.notify('continous', 'upgrade_complete', {
                            'success': False, 'code': code, 'message': message})

    def handle_error(self, error, message):
        self._tunnel.notify('lost')

    def handle_request(self, method, converted_method, parameters):
        result = self._driver.execute(converted_method, parameters)
        self._tunnel.notify('invoke', method, result)

    def handle_receive_continous_data(self, packet_type, data):
        self._tunnel.notify('continous', packet_type, data)

    def _prepare_driver(self):
        self._driver = Driver(self.options)

        self._driver.on(DriverEvents.Discovered,
                        self.handle_discovered)

        self._driver.on(DriverEvents.Lost,
                        self.handle_lost)

        self._driver.on(DriverEvents.UpgradeFinished,
                        self.handle_upgrade_finished)

        self._driver.on(DriverEvents.UpgradeFail,
                        self.handle_upgrade_fail)

        self._driver.on(DriverEvents.Error,
                        self.handle_error)

        self._driver.on(DriverEvents.Continous,
                        self.handle_receive_continous_data)

        self._driver.detect()

    def _prepare_tunnel(self):
        import tornado.ioloop
        if sys.version_info[0] > 2:
            import asyncio
            asyncio.set_event_loop(asyncio.new_event_loop())

        event_loop = tornado.ioloop.IOLoop.current()

        self._tunnel = WebServer(self.options, event_loop)
        self._tunnel.on(TunnelEvents.Request, self.handle_request)
        self._tunnel.setup()

    def _prepare_logger(self):
        '''
        Set default log handler: console logger, file logger
        '''
        executor_path = resource.get_executor_path()
        log_level = 'info'
        if self.options.debug:
            log_level = 'debug'

        console_log = self.options.console_log

        APP_CONTEXT.set_logger(
            AppLogger(
                filename=os.path.join(executor_path, 'loggers', 'trace.log'),
                gen_file=True,
                level=log_level,
                console_log=console_log
            ))

        APP_CONTEXT.set_print_logger(
            AppLogger(
                filename=os.path.join(
                    executor_path, 'loggers', 'print_' + time.strftime('%Y%m%d_%H%M%S') + '.log'),
                gen_file=True,
                level=log_level
            ))

    def _build_options(self, **options):
        self.options = WebserverArgs(**options)
