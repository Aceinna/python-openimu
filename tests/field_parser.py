import sys
try:
    from aceinna.devices.parsers.open_field_parser import encode_value
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.devices.parsers.open_field_parser import encode_value


def test_encode_value():
    '''Test encode value
    '''
    param_id=10
    int8_result = encode_value('int8', param_id)
    print('int8 encode result:{0}'.format(int8_result))

    uint32_result = encode_value('uint32', param_id)
    print('uint32 encode result:{0}'.format(uint32_result))

    char8_result = encode_value('char8', param_id)
    print('char8 encode result:{0}'.format(char8_result))


if __name__ == '__main__':
    test_encode_value()
