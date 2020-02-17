
import sys
try:
    from aceinna.models.args import WebserverArgs
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.models.args import WebserverArgs


def test_web_args():
    define_port = 8001
    web_args = WebserverArgs(port=define_port)
    assert web_args.port == define_port

if __name__ == '__main__':
    test_web_args()
