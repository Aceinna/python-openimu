
"""
Application Loader
"""
from .receiver import Receiver as ReceiverApp
from .cli import CommandLine as CommandLineApp
from .default import Default as DefaultApp
from .log_parser import LogParser as LogParserApp
from .. import VERSION
from ..framework.constants import APP_TYPE

class Loader:
    '''Bootstrap Factory
    '''
    @staticmethod
    def create(platform, options):
        '''Initial bootstrap instance
        '''
        print("[Info] Python driver version: {0} ".format(VERSION))

        active_app = None
        if platform == APP_TYPE.DEFAULT:
            active_app = DefaultApp(**options)

        if platform == APP_TYPE.CLI:
            active_app = CommandLineApp(**options)

        if platform == APP_TYPE.RECEIVER:
            active_app = ReceiverApp(**options)

        if platform == APP_TYPE.LOG_PARSER:
            active_app = LogParserApp(**options)

        if active_app is None:
            raise ValueError('no matched bootstrap')

        return active_app
