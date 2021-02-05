
"""
Application Loader
"""
from .cli import CommandLine as CommandLineApp
from .default import Default as DefaultApp


class APP_TYPE:
    DEFAULT = 'default'
    CLI = 'cli'


class Loader:
    '''Bootstrap Factory
    '''
    @staticmethod
    def create(platform, options):
        '''Initial bootstrap instance
        '''
        active_app = None
        if platform == APP_TYPE.DEFAULT:
            active_app = DefaultApp(**options)

        if platform == APP_TYPE.CLI:
            active_app = CommandLineApp(**options)

        if active_app is None:
            raise ValueError('no matched bootstrap')

        return active_app
