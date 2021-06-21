from abc import ABCMeta, abstractmethod
from .event_base import EventBase


class TunnelEvents:
    '''Tunnel Events defination
    '''
    Request = 'REQUEST'


class TunnelBase(EventBase):
    ''' Tunnel Base
    '''
    __metaclass__ = ABCMeta

    @abstractmethod
    def setup(self):
        ''' Prepare the tunnel
        '''

    @abstractmethod
    def notify(self, notify_type, *other):
        ''' Notify to clients
        '''
