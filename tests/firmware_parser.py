import sys
try:
    from aceinna.devices.openrtk.firmware_parser import parser
    from aceinna.models import InternalCombineAppParseRule
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.devices.openrtk.firmware_parser import parser
    from aceinna.models import InternalCombineAppParseRule


def test_parse_content():
    '''Test parse firmware content
    '''
    parser_rules = [
        InternalCombineAppParseRule('rtk', 'rtk_start:', 4),
        InternalCombineAppParseRule('sdk', 'sdk_start:', 4),
    ]

    firmware_content = open('./tests/all.bin', 'rb').read()
    result = parser(firmware_content, parser_rules)

    print(result)


if __name__ == '__main__':
    test_parse_content()
