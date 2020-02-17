"""
A base class for an entry instance
"""
from abc import ABCMeta, abstractmethod

class BootstrapBase:
    '''Bootstrap base
    '''
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def listen(self):
        '''start to work
        '''

    @abstractmethod
    def stop(self):
        '''stop working
        '''
