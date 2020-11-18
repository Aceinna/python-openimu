"""
Command line entry
"""
#import asyncio
import threading
from os import getpid
import psutil
from .web import Webserver
from ..models import WebserverArgs
from ..framework.communicator import CommunicatorFactory


class CommandLine:
    '''Command line entry class
    '''

    def __init__(self, **kwargs):
        self.communication = 'uart'
        self.device_provider = None
        self.communicator = None
        self.supported_commands = []
        self.input_string = None
        self.current_command = None
        self._build_options(**kwargs)
        self.webserver = Webserver(**kwargs)
        self.webserver_running = False

    def listen(self):
        # find device
        '''
        Start to find device
        '''
        self.detect_device(self.device_discover_handler)

    def detect_device(self, callback):
        '''find if there is a connected device'''
        if self.communicator is None:
            self.communicator = CommunicatorFactory.create(
                self.communication, self.options)

        self.communicator.find_device(callback)

    def device_discover_handler(self, device_provider):
        '''
        Handler after device discovered
        '''
        # check if device is in bootloader
        # TODO: if in bootloader, only allow upgrade

        # TODO: if a normal device, allow other commands

        # load device provider
        self.webserver.set_communicator(self.communicator)
        self.webserver.load_device_provider(device_provider)
        # setup command
        #self.device_provider = device_provider
        self.setup_command_handler()

    def setup_command_handler(self):
        '''
        Prepare command
        '''
        self.supported_commands = self.webserver.device_provider.get_command_lines()

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

    def start_webserver(self, current_loop):
        '''
        Start websocket server
        '''
        # asyncio.set_event_loop(asyncio.new_event_loop())
        self.webserver.start_webserver(current_loop)

        # if not current_loop.is_running():
        #     current_loop.run_forever()

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
        print(self.webserver.device_provider.get_device_info())

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
            self.webserver.device_provider.upgrade_framework(file_name)
        return True

    def record_handler(self):
        '''record command is used to save the outputs into local machine
        '''
        # TODO: check device is idel
        if not self.webserver.device_provider.is_logging:
            self.webserver.device_provider.start_data_log()
        return True

    def stop_handler(self):
        '''record command is used to save the outputs into local machine
        '''
        # TODO: check device is idel
        if self.webserver.device_provider.is_logging:
            self.webserver.device_provider.stop_data_log()

        if self.webserver_running:
            self.webserver.stop_ws_server()
            self.webserver_running = False
        return True

    def get_handler(self):
        '''
        Get parameter of device
        '''
        input_args = len(self.input_string)
        conf = self.webserver.device_provider.get_conf()
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

        param = self.webserver.device_provider.get_param(
            {'paramId': select_param['paramId']})
        print(param['data']['value'])
        return True

    def set_handler(self):
        '''
        Set parameter of device
        '''
        input_args = len(self.input_string)
        conf = self.webserver.device_provider.get_conf()
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

        self.webserver.device_provider.set_param({
            'paramId': select_param['paramId'],
            'value': self.input_string[2]
        })

        # TODO: display a response message to user

        return True

    def save_handler(self):
        '''
        Save device configuration
        '''
        self.webserver.device_provider.save_config()
        return True

    def server_start_handler(self):
        '''
        start a websocket server
        '''
        # self.webserver.start_websocket_server()
        loop = None #asyncio.get_event_loop()
        webserver_thread = threading.Thread(
            target=self.start_webserver, args=(loop,))
        webserver_thread.start()
        self.webserver_running = True
        return True

    def exit_handler(self):
        '''
        Exit current process
        '''
        # self.webserver.stop()
        #self.webserver_running = False
        pid = getpid()
        process = psutil.Process(pid)
        process.kill()

    def run_handler(self):
        '''used by customers
        '''
        return True
