from .parsers.open_message_parser import UartMessageParser as OpenUartMessageParser
from .parsers.dmu_message_parser import UartMessageParser as DMUUartMessageParser


class ParserManager:
    '''
    Manage Parser
    '''
    device_list = []

    @staticmethod
    def build(device_type, properties):
        '''
        Generate matched parser
        '''
        if device_type == 'DMU':
            return DMUUartMessageParser(properties)
        else:
            return OpenUartMessageParser(properties)
