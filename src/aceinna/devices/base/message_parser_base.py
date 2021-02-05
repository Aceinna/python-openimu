from abc import ABCMeta, abstractmethod
from . import EventBase
from ...framework.utils import helper

class MessageParserBase(EventBase):
    '''
        Message parser base
    '''
    __metaclass__ = ABCMeta

    properties = None
    run_command = ''

    def __init__(self, configuration):
        super(MessageParserBase, self).__init__()
        self.properties = configuration

    @abstractmethod
    def set_run_command(self, command):
        '''
        set current run command
        '''

    @abstractmethod
    def analyse(self, data_block):
        '''
        Analyse the data per byte
        '''

    def set_configuration(self, configuration):
        '''
        load configuration
        '''
        self.properties = configuration

    def get_packet_info(self, raw_command):
        '''
        Build packet info
        '''
        packet_type, payload, _ = helper.parse_command_packet(raw_command)
        return {
            'packet_type': packet_type,
            'data': payload,
            'raw': raw_command
        }
