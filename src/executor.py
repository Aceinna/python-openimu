"""
Development Entry
"""
import os
import sys
import argparse
import traceback
import signal
import time
from aceinna.bootstrap import Webserver
from aceinna.framework.constants import (DEVICE_TYPES,BAUDRATE_LIST)
from aceinna.framework.utils.print import printRed

IS_WINDOWS = sys.platform.__contains__(
    'win32') or sys.platform.__contains__('win64')
IS_LATER_PY_38 = sys.version_info > (3, 8)


def receive_args():
    """parse input arguments
    """
    parser = argparse.ArgumentParser(
        description='Aceinna python driver input args command:', allow_abbrev=False)
    # parser.add_argument("-host", type=str, help="host type", default='web')
    # for host as web
    parser.add_argument("-l", "--protocol", dest="protocol",
                        help="Protocol(uart or lan)", default='uart', choices=['uart', 'lan'])
    parser.add_argument("-p", "--port", dest='port',  metavar='', type=int,
                        help="Webserver port")
    parser.add_argument("--device-type", dest="device_type", type=str,
                        help="Open Device Type", choices=DEVICE_TYPES)
    parser.add_argument("-b", "--baudrate", dest="baudrate", type=int,
                        help="Baudrate for uart", choices=BAUDRATE_LIST)
    parser.add_argument("-c", "--com-port", dest="com_port", metavar='', type=str,
                        help="COM Port")
    parser.add_argument("--console-log", dest='console_log', action='store_true',
                        help="Output log on console", default=False)
    parser.add_argument("--debug", dest='debug', action='store_true',
                        help="Log debug information", default=False)
    parser.add_argument("--with-data-log", dest='with_data_log', action='store_true',
                        help="Contains internal data log (OpenIMU only)", default=False)
    parser.add_argument("-r", "--with-raw-log", dest='with_raw_log', action='store_true',
                        help="Contains raw data log (OpenRTK only)", default=False)
    parser.add_argument("-s", "--set-user-para", dest='set_user_para', action='store_true',
                        help="set user parameters (OpenRTK only)", default=False)
    parser.add_argument("-n", "--ntrip-client", dest='ntrip_client', action='store_true',
                        help="enable ntrip client (OpenRTK only)", default=False)

    return parser.parse_args()


def kill_app(signal_int, call_back):
    '''Kill main thread
    '''
    os.kill(os.getpid(), signal.SIGTERM)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, kill_app)
    # compatible code for windows python 3.8
    if IS_WINDOWS and IS_LATER_PY_38:
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    ARGS = receive_args()
    try:
        APP = Webserver(
            protocol=ARGS.protocol,
            device_type=ARGS.device_type,
            com_port=ARGS.com_port,
            port=ARGS.port,
            baudrate=ARGS.baudrate,
            console_log=ARGS.console_log,
            debug=ARGS.debug,
            with_data_log=ARGS.with_data_log,
            with_raw_log=ARGS.with_raw_log,
            set_user_para=ARGS.set_user_para,
            ntrip_client=ARGS.ntrip_client)
        APP.listen()
    except KeyboardInterrupt:  # response for KeyboardInterrupt such as Ctrl+C
        print('User stop this program by KeyboardInterrupt! File:[{0}], Line:[{1}]'.format(
            __file__, sys._getframe().f_lineno))
        APP.stop()
        sys.exit()
    except Exception as ex:  # pylint: disable=bare-except
        # traceback.print_exc()  # For development
        printRed('Application Exit Exception: {0}'.format(ex))
        os._exit(1)

    while True:
        time.sleep(10)
