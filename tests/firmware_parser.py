import sys
try:
    from aceinna.framework.utils.firmware_parser import parser
    from aceinna.models import InternalCombineAppParseRule
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.framework.utils.firmware_parser import parser
    from aceinna.models import InternalCombineAppParseRule


def test_parse_content():
    '''Test parse firmware content
    '''
    parser_rules = [
        InternalCombineAppParseRule('rtk', 'rtk_start:', 4),
        InternalCombineAppParseRule('ins', 'ins_start:', 4),
        InternalCombineAppParseRule('sdk', 'sdk_start:', 4),
    ]

    firmware_content = open('./other/rtk_ins_sta9100.bin', 'rb').read()
    result = parser(firmware_content, parser_rules)

    for _, rule in enumerate(result):
        content = result[rule]
        content_len = len(content)
        print(rule, content_len, content_len % 16)


if __name__ == '__main__':
    test_parse_content()
