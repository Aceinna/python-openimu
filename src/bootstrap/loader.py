
#import src.bootstrap.cli as CommandLine
#import src.bootstrap.web as Webserver
from .cli import CommandLine
from .web import Webserver
from ..framework.context import app_context


class Loader:
    def create(type, options):
        if type == 'web':
            active_app = Webserver(options)

        if type == 'cli':
            active_app = CommandLine(options)

        if active_app == None:
            raise Exception('no matched bootstrap')

        app_context.set_app(active_app)

        return active_app
