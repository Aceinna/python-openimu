"""
Command line entry
"""
import sys
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
        self._build_options(**kwargs)
        self.webserver = Webserver(**kwargs)

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
        print(device_provider.getConf())
        #self.setup_command_handler()

    def setup_command_handler(self):
        self.supported_commands = self.device_provider.get_command_lines()

        while True:
            token = input(">>")
            self.input_string = token.split(" ")

            if token.strip() == 'exit':
                break
            # if self.http_server_running == True and token.strip() != 'stop':
            #     print("server is on-going, please stop it")
            #     continue

            for command in self.supported_commands:
                if command['name'] == self.input_string[0]:
                    self.current_command = command
                    eval('self.%s()' % (command['function']))
                    break
            else:
                self._help_handler()

        return True

    def _help_handler(self):
        if len(self.supported_commands) > 0:
            print("Usage: ")
            for command in self.supported_commands:
                print(command['name'] + " : " + command['description'])
        else:
            print("No more command line.")

    def _build_options(self, **kwargs):
        self.options = WebserverArgs(**kwargs)
