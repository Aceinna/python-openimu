
#import src.bootstrap.cli as CommandLine
#import src.bootstrap.web as Webserver
from .cli import CommandLine
from .web import Webserver

instance = None


def create(type, options):
    if type == 'web':
        instance = Webserver(options)

    if type == 'cli':
        instance = CommandLine(options)

    if instance == None:
        print('no matched bootstrap')

    return instance


def get_active_instance():
    if instance is not None:
        return instance
    else:
        raise Exception('no actived app instance')
