from abc import ABCMeta, abstractmethod
from . import EventBase


class UpgradeWorkerBase(EventBase):
    '''
        Upgrade worker base
    '''
    __metaclass__ = ABCMeta

    def __init__(self):
        super(UpgradeWorkerBase, self).__init__()
        self._key = None
        self._is_stopped = False

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, value):
        self._key = value

    @property
    def is_stopped(self):
        return self._is_stopped

    @abstractmethod
    def get_upgrade_content_size(self):
        '''get the size of upgrade content'''
        return 0

    @abstractmethod
    def work(self):
        '''do the work'''

    @abstractmethod
    def stop(self):
        '''stop work'''
