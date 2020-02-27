"""
Command line entry
"""
import asyncio
import psutil
import threading
from os import getpid
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
        self.webserver_thread = threading.Thread(target=self.start_webserver)
        self.webserver_running = False

    def listen(self):
        # find device
        '''
        Start to find device
        '''
        self.detect_device(self.device_discover_handler)

    def stop(self):
        pass

    def detect_device(self, callback):
        '''find if there is a connected device'''
        print('start to find device')
        if self.communicator is None:
            self.communicator = CommunicatorFactory.create(
                self.communication, self.options)

        self.communicator.find_device(callback)

    def device_discover_handler(self, device_provider):
        '''
        Handler after device discovered
        '''
        # load device provider
        self.webserver.load_device_provider(device_provider)
        # setup command
        # print(device_provider.getConf())
        self.device_provider = device_provider
        self.setup_command_handler()

    def setup_command_handler(self):
        '''
        Prepare command
        '''
        self.supported_commands = self.device_provider.get_command_lines()

        while True:
            token = input(">>")
            self.input_string = token.split(" ")

            if token.strip() == 'exit':
                break

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
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.webserver.start_websocket_server()

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
            self.device_provider.upgradeFramework(file_name)
        return True

    def record_handler(self):
        '''record command is used to save the outputs into local machine
        '''
        # TODO: check device is idel
        # self.device_provider.startLog()
        return True

    def stop_handler(self):
        '''record command is used to save the outputs into local machine
        '''
        # TODO: check device is idel
        # self.device_provider.stopLog()
        return True

    def get_handler(self):
        '''
        Get parameter of device
        '''

    def set_handler(self):
        '''
        Set parameter of device
        '''

    def save_handler(self):
        '''
        Save device configuration
        '''
        self.device_provider.saveConfig()
        return True

    def server_start_handler(self):
        '''
        start a websocket server
        '''
        # self.webserver.start_websocket_server()
        self.webserver_thread.start()
        self.webserver_running = True
        return True

    def exit_handler(self):
        '''
        Exit current process
        '''
        self.webserver.stop()
        pid = getpid()
        process = psutil.Process(pid)
        process.kill()

    def run_handler(self):
        '''used by customers
        '''
        return True
