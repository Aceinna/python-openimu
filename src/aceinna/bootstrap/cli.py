"""
Command line entry
"""
import os
import sys
import time
import threading
from os import getpid
import psutil
# from .web import Webserver
from ..models import WebserverArgs

from ..core.driver import (Driver, DriverEvents)
from ..core.device_context import DeviceContext
from ..core.tunnel_web import WebServer
from ..core.tunnel_base import TunnelEvents

from ..framework import AppLogger
from ..framework.utils import resource
from ..framework.context import APP_CONTEXT


class CommandLine:
    '''Command line entry class
    '''
    options = None
    _tunnel = None
    _driver = None
    webserver_running = False
    supported_commands = []
    input_string = None
    current_command = None

    def __init__(self, **kwargs):
        self._build_options(**kwargs)

        # self.communication = 'uart'
        # self.device_provider = None
        # self.communicator = None

        # self.webserver = Webserver(**kwargs)

    def listen(self):
        '''
        Prepare components, initialize the application
        '''
        # prepare driver
        threading.Thread(target=self._prepare_driver).start()
        # prepage logger
        self._prepare_logger()

    def handle_discovered(self, device_provider):
        device_context = DeviceContext(device_provider)
        APP_CONTEXT.device_context = device_context

        if self._tunnel:
            self._tunnel.notify('discovered')

    def handle_lost(self):
        if self._tunnel:
            self._tunnel.notify('lost')

    def handle_upgrade_finished(self):
        if self._tunnel:
            self._tunnel.notify(
                'continous', 'upgrade_complete', {'success': True})

    def handle_upgrade_fail(self, code, message):
        if self._tunnel:
            self._tunnel.notify('continous', 'upgrade_complete', {
                                'success': False, 'code': code, 'message': message})

    def handle_error(self, error, message):
        if self._tunnel:
            self._tunnel.notify('lost')

    def handle_request(self, method, converted_method, parameters):
        result = self._driver.execute(converted_method, parameters)
        if self._tunnel:
            self._tunnel.notify('invoke', method, result)

    def handle_receive_continous_data(self, packet_type, data):
        if self._tunnel:
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

        self.setup_command_handler()

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

    def setup_command_handler(self):
        '''
        Prepare command
        '''
        self.supported_commands = self._driver.execute('get_command_lines')

        while True:
            token = input(">>")
            self.input_string = token.split(" ")

            if token.strip() == 'exit':
                break

            if self.webserver_running and token.strip() != 'stop':
                print("server is on-going, please stop it")
                continue

            for command in self.supported_commands:
                if command['name'] == self.input_string[0]:
                    self.current_command = command
                    eval('self.%s()' % (command['function']))
                    break
            else:
                self.help_handler()

        self.exit_handler()
        return True

    def start_webserver(self):
        '''
        Start websocket server
        '''
        import tornado.ioloop
        if sys.version_info[0] > 2:
            import asyncio
            asyncio.set_event_loop(asyncio.new_event_loop())

        event_loop = tornado.ioloop.IOLoop.current()

        self._tunnel = WebServer(self.options, event_loop)
        self._tunnel.on(TunnelEvents.Request, self.handle_request)
        self._tunnel.setup()

    def _build_options(self, **kwargs):
        self.options = WebserverArgs(**kwargs)

    # command handler
    def help_handler(self):
        '''
        Help handler
        '''
        if len(self.supported_commands) > 0:
            print("Usage: ")
            for command in self.supported_commands:
                print(command['name'] + " : " + command['description'])
        else:
            print("No more command line.")

    def connect_handler(self):
        '''
        Connect to device, may no need it later
        '''
        print(self._driver.execute('get_device_info'))

    def upgrade_handler(self):
        '''upgrade command is used for firmware upgrade and followed by file name
        '''
        input_args = len(self.input_string)
        if input_args == 1:
            print("Usage:")
            print("upgrade file_name")
        else:
            file_name = self.input_string[1]
            # TODO: check device is idel
            self._driver.execute('upgrade_framework', file_name)
        return True

    def record_handler(self):
        '''record command is used to save the outputs into local machine
        '''
        # TODO: check device is idel
        if APP_CONTEXT.device_context.runtime_status != 'LOGGING':
            self._driver.execute('start_data_log')
        return True

    def stop_handler(self):
        '''record command is used to save the outputs into local machine
        '''
        # TODO: check device is idel
        if APP_CONTEXT.device_context.runtime_status == 'LOGGING':
            self._driver.execute('stop_data_log')

        if self.webserver_running:
            self._tunnel.stop_ws_server()
            self.webserver_running = False
        return True

    def get_handler(self):
        '''
        Get parameter of device
        '''
        input_args = len(self.input_string)
        conf = self._driver.execute('get_conf')

        input_params_properties = conf['data']['inputParams']
        select_param = None
        if (input_args == 1):
            print("Usage: get [options]")
            print("Option: ")
            i = 2
            while i < len(input_params_properties):
                print(input_params_properties[i]['argument'])
                i += 1
            return True
        else:
            i = 2
            while i < len(input_params_properties):
                select_param = input_params_properties[i]
                if (select_param['argument'] == self.input_string[1]):
                    break
                i += 1
                if (i == len(input_params_properties)):
                    print("Usage: get [options]")
                    print("Option: ")
                    i = 2
                    while i < len(input_params_properties):
                        print(input_params_properties[i]['argument'])
                        i += 1
                    return True

        param = self._driver.execute(
            'get_param', {'paramId': select_param['paramId']})
        print(param['data']['value'])
        return True

    def set_handler(self):
        '''
        Set parameter of device
        '''
        input_args = len(self.input_string)
        conf = self._driver.execute('get_conf')
        input_params_properties = conf['data']['inputParams']
        select_param = None
        not_in_options = False
        options = []

        if input_args == 1:
            print("Usage: set <options> <values>")
            i = 2
            while i < len(input_params_properties):
                print(input_params_properties[i]['argument'])
                i += 1
            return True
        else:
            i = 2
            while i < len(input_params_properties):
                select_param = input_params_properties[i]
                if (select_param['argument'] == self.input_string[1]):
                    break
                i += 1

        if input_args == 2:
            if i == len(input_params_properties):
                print("Usage: set <options> <values>")
                i = 2
                while i < len(input_params_properties):
                    print(input_params_properties[i]['argument'])
                    i += 1
            else:
                print("Usage: set " + select_param['argument'] + " <values>")
                print("values: ")
                print(select_param['options'])
            return True

        if select_param.__contains__('options'):
            for item in select_param['options']:
                if isinstance(item, dict):
                    options.append(int(item['key']))
                else:
                    options.append(item)

        if select_param['type'] == 'int64':
            self.input_string[2] = int(self.input_string[2])

        if select_param['type'] == "char8" and self.input_string[2] not in select_param['options']:
            not_in_options = True

        if select_param['type'] == "int64" and\
                self.input_string[2] not in options:
            not_in_options = True

        if not_in_options:
            print("Usage: set " + select_param['argument'] + " <values>")
            print("values: ")
            print(select_param['options'])
            return True

        conf = self._driver.execute('set_param', {
            'paramId': select_param['paramId'],
            'value': self.input_string[2]
        })

        # TODO: display a response message to user

        return True

    def save_handler(self):
        '''
        Save device configuration
        '''
        self._driver.execute('save_config')
        return True

    def server_start_handler(self):
        '''
        start a websocket server
        '''
        threading.Thread(target=self.start_webserver).start()
        self.webserver_running = True
        return True

    def exit_handler(self):
        '''
        Exit current process
        '''
        # self.webserver.stop()
        # self.webserver_running = False
        pid = getpid()
        process = psutil.Process(pid)
        process.kill()

    def run_handler(self):
        '''used by customers
        '''
        return True
