"""
Application Entry
"""
import os
import sys
import argparse
#import traceback
from src.bootstrap.loader import Loader

IS_WINDOWS = sys.platform.__contains__(
    'win32') or sys.platform.__contains__('win64')
IS_LATER_PY_38 = sys.version_info > (3, 8)

def receive_args():
    """parse input arguments
    """
    parser = argparse.ArgumentParser()
    parser.description = argparse.ArgumentParser(
        description='Aceinna python driver input args command:')
    parser.add_argument("-host", type=str, help="host type", default='web')
    # for host as web
    parser.add_argument("-p", type=int, help="webserver port", default=8000)
    parser.add_argument("-b", type=int, help="baudrate",
                        choices=[38400, 57600, 115200, 230400, 460800])
    parser.add_argument("-nolog", type=int,
                        help="disable internal log", default=True)
    return parser.parse_args()


if __name__ == '__main__':
    # compatible code for windows python 3.8
    if IS_WINDOWS and IS_LATER_PY_38:
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    ARGS = receive_args()
    PLATFORM = ARGS.host
    try:
        APP = Loader.create(PLATFORM, options=ARGS)
        APP.listen()
    except KeyboardInterrupt:  # response for KeyboardInterrupt such as Ctrl+C
        print('User stop this program by KeyboardInterrupt! File:[{0}], Line:[{1}]'.format(
            __file__, sys._getframe().f_lineno))
        APP.stop()
        sys.exit()
    except Exception:
        # traceback.print_exc() # For development
        os._exit(1)
