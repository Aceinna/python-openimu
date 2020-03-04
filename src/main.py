"""
Development Entry
"""
import os
import sys
import argparse
import traceback
from aceinna.bootstrap import Webserver
from aceinna.framework.constants import BAUDRATE_LIST

IS_WINDOWS = sys.platform.__contains__(
    'win32') or sys.platform.__contains__('win64')
IS_LATER_PY_38 = sys.version_info > (3, 8)


def receive_args():
    """parse input arguments
    """
    parser = argparse.ArgumentParser(
        description='Aceinna python driver input args command:')
    # parser.add_argument("-host", type=str, help="host type", default='web')
    # for host as web
    parser.add_argument("-p", "--port", type=int,
                        help="Webserver port")
    parser.add_argument("--device-type", type=str,
                        help="Open Device Type")
    parser.add_argument("-b", "--baudrate", type=int,
                        help="Baudrate for uart", choices=BAUDRATE_LIST)
    parser.add_argument("-c", "--com-port", type=str,
                        help="COM Port")
    parser.add_argument("--debug", type=bool,
                        help="Log debug information", default=False)
    parser.add_argument("--with-data-log", type=bool,
                        help="Contains internal data log (OpenIMU only)", default=False)
    parser.add_argument("--with-raw-log", type=bool,
                        help="Contains raw data log (OpenRTK only)", default=False)
    return parser.parse_args()


if __name__ == '__main__':
    setattr(sys, '__dev__', True)
    # compatible code for windows python 3.8
    if IS_WINDOWS and IS_LATER_PY_38:
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    ARGS = receive_args()
    try:
        APP = Webserver(
            device_type=ARGS.device_type,
            com_port=ARGS.com_port,
            port=ARGS.port,
            baudrate=ARGS.baudrate,
            debug=ARGS.debug,
            with_data_log=ARGS.with_data_log,
            with_raw_log=ARGS.with_raw_log)
        APP.listen()
    except KeyboardInterrupt:  # response for KeyboardInterrupt such as Ctrl+C
        print('User stop this program by KeyboardInterrupt! File:[{0}], Line:[{1}]'.format(
            __file__, sys._getframe().f_lineno))
        APP.stop()
        sys.exit()
    except:  # pylint: disable=bare-except
        traceback.print_exc()  # For development
        os._exit(1)
