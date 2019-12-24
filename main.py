import sys
import argparse
import traceback
from src.bootstrap.loader import Loader


def receive_args():
    parser = argparse.ArgumentParser()
    parser.description = argparse.ArgumentParser(
        description='Aceinna python driver input args command:')
    parser.add_argument("-host", type=str, help="host type", default='web')
    # for host as web
    parser.add_argument("-p", type=int, help="webserver port", default=8000)
    parser.add_argument("-b", type=int, help="baudrate")
    parser.add_argument("-nolog", type=int,
                        help="disable internal log", default=True)
    return parser.parse_args()


if __name__ == '__main__':
    args = receive_args()
    platform = args.host
    try:
        app = Loader.create(platform, options=args)
        app.listen()
    except KeyboardInterrupt:  # response for KeyboardInterrupt such as Ctrl+C
        print('User stop this program by KeyboardInterrupt! File:[{0}], Line:[{1}]'.format(
            __file__, sys._getframe().f_lineno))
        app.stop()
        sys.exit()
    except Exception as e:
        traceback.print_exc()