from abc import ABCMeta, abstractmethod

class BootstrapBase:
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def listen(self):
        pass

    @abstractmethod
    def stop(self):
        pass