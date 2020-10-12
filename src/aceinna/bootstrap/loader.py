
"""
Application Loader
"""
from .cli import CommandLine
from .web import Webserver
#from ..framework.context import APP_CONTEXT


class Loader:
    '''Bootstrap Factory
    '''
    @staticmethod
    def create(platform, options):
        '''Initial bootstrap instance
        '''
        if platform == 'web':
            active_app = Webserver(**options)

        if platform == 'cli':
            active_app = CommandLine(**options)

        if active_app is None:
            raise Exception('no matched bootstrap')

        #APP_CONTEXT.set_app(active_app)

        return active_app
