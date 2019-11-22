# TODO: command line client
from .base import BootstrapBase


class CommandLine(BootstrapBase):
    def __init__(self, options):
        print('cli init')

    def listen(self):
        print('cli listen')

    def stop(self):
        print('stop')
