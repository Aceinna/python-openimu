
#import src.bootstrap.cli as CommandLine
#import src.bootstrap.web as Webserver
from .cli import CommandLine
from .web import Webserver
from ..framework.context import active_app


class Loader:
    def create(type, options):
        if type == 'web':
            active_app = Webserver(options)

        if type == 'cli':
            active_app = CommandLine(options)

        if active_app == None:
            print('no matched bootstrap')

        return active_app

    def get_active_instance():
        if active_app is not None:
            return active_app
        else:
            raise Exception('no actived app instance')
