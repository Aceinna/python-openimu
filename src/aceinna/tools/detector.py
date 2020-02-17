from ..models.args import DetectorArgs
from ..framework.communicator import CommunicatorFactory

class Detector(object):
    '''
    Device Detector
    '''
    def __init__(self, **kwargs):
        self.communication = 'uart'
        self.communicator = None
        self._build_options(**kwargs)

    def find(self, callback):
        '''find if there is a connected device'''
        print('start to find device')
        if self.communicator is None:
            self.communicator = CommunicatorFactory.create(
                self.communication, self.options)

        self.communicator.find_device(callback)

    def _build_options(self, **kwargs):
        self.options = DetectorArgs(**kwargs)