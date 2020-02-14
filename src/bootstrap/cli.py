"""
Command line entry
"""
from .base import BootstrapBase


class CommandLine(BootstrapBase):
    '''Command line entry class
    '''
    def __init__(self, options):
        super().__init__(options)
        print('cli init')

    def listen(self):
        print('cli listen')

    def stop(self):
        print('stop')
