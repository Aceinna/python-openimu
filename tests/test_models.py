
import sys
try:
    from aceinna.models.args import (WebserverArgs,DetectorArgs)
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.models.args import (WebserverArgs,DetectorArgs)


def test_web_args():
    define_port = 8001
    web_args = WebserverArgs(port=define_port)
    assert web_args.port == define_port


def test_web_args_with_default():
    '''
        'protocol': 'uart',
        'device_type': 'auto',
        'port': 'auto',
        'baudrate': 'auto',
        'com_port': 'auto',
        'debug': False,
        'with_data_log': False,
        'console_log': False,
        'set_user_para': False,
        'ntrip_client': False
    '''
    web_args = WebserverArgs()
    assert web_args is not None
    assert web_args.protocol == 'uart'
    assert web_args.port == 'auto'
    assert web_args.baudrate == 'auto'
    assert web_args.com_port == 'auto'
    assert web_args.debug == False
    assert web_args.with_data_log == False
    assert web_args.console_log == False
    assert web_args.set_user_para == False
    assert web_args.ntrip_client == False

def test_detect_with_default():
    '''
        'device_type': 'auto',
        'baudrate': 'auto',
        'com_port': 'auto'
    '''
    detect_args = DetectorArgs()
    assert detect_args.device_type == 'auto'
    assert detect_args.com_port == 'auto'
    assert detect_args.baudrate == 'auto'



if __name__ == '__main__':
    test_web_args()
    test_web_args_with_default()
    test_detect_with_default()
