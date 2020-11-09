import struct
from abc import ABCMeta, abstractmethod


def bytes2binstr(b, n=None):
    s = ''.join(f'{x:08b}' for x in b)
    return s if n is None else s[:n + n // 8 + (0 if n % 8 else -1)]


def getbytes(bits):
    done = False
    while not done:
        byte = 0
        for _ in range(0, 8):
            try:
                bit = next(bits)
            except StopIteration:
                bit = 0
                done = True
            byte = (byte << 1) | bit
        yield byte


class EEPROMField(object):
    '''
    EEPROM Field
    '''

    def __init__(self, name, address, word_len=1):
        self.name = name
        self.address = address
        self.word_len = word_len

    @abstractmethod
    def parse(self, payload):
        '''
        Parse payload
        '''
        # return: value, parsed, error
        return payload, False, None


class ProductConfigurationField(EEPROMField):
    def __init__(self, name, address, word_len=1):
        super(ProductConfigurationField, self).__init__(
            name, address, word_len=1)

    def parse(self, payload):
        # return: value, parsed, error
        bytes_value = struct.pack('BB', *payload)
        bit_value = bytes2binstr(bytes_value)

        parsed_value = {
            'mags': int(bit_value[-1]),
            'gps': int(bit_value[-2]),
            'algorithm': int(bit_value[-3]),
            'ext_aiding': int(bit_value[-4]),
            'architechture': int(bit_value[-8:-4], 2)
        }

        return parsed_value, True, None


EEPROM_ADDRESS_DEFINES = [
    {
        "address": 0x71C,
        "instance": ProductConfigurationField('Product Configuration', 0x71C)
    }
]


class EEPROMFieldDefines:
    '''
    A list of fields could be parsed
    '''

    def __init__(self):
        self._list = dict()
        self._default_field = EEPROMField('default', -1)

    def load(self):
        self._list.clear()
        for item in EEPROM_ADDRESS_DEFINES:
            self._list[item['address']] = item['instance']

    def find(self, address: int) -> EEPROMField:
        exist_field = self._list.get(address)

        if not exist_field:
            exist_field = self._default_field

        return exist_field


EEPROM_FIELD_DEFINES_SINGLETON = EEPROMFieldDefines()
