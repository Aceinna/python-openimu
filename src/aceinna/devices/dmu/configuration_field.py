from typing import List
from ..parsers.dmu_field_parser import (encode_value, decode_value)


class ConfigurationField(object):
    '''
    Configuration Field
    '''

    def __init__(self, name, field_id, field_type):
        self.name = name
        self.field_id = field_id
        self.field_type = field_type

    def parse(self, payload):
        '''
        Parse payload
        '''
        # return: value, parsed, error
        value = decode_value(self.field_type, payload)
        return value, True, None

    def encode(self, value):
        return encode_value(self.field_type, value)


class ConfigruationFieldDefines:
    '''
    A list of fields could be parsed
    '''

    def __init__(self):
        self._list = dict()

    def load(self, json):
        self._list.clear()
        for item in json:
            param_id = item['paramId']
            param_name = item['name']
            param_type = item['type']
            self._list[param_id] = ConfigurationField(
                param_name, param_id, param_type)

    def get_fields(self) -> List[ConfigurationField]:
        return self._list.values()

    def find(self, paramId: int) -> ConfigurationField:
        return self._list.get(paramId)


CONFIGURATION_FIELD_DEFINES_SINGLETON = ConfigruationFieldDefines()
