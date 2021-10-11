import os
import sys
import argparse
import traceback
import signal
from datetime import datetime, timedelta
from functools import wraps
from typing import TypeVar
from .constants import (DEVICE_TYPES, BAUDRATE_LIST, INTERFACES)
from .utils.print import print_red
from .utils.resource import is_dev_mode


T = TypeVar('T')

INTERFACE_LIST = INTERFACES.list()
MODES = ['default', 'cli', 'receiver']
TYPES_OF_LOG = ['openrtk', 'rtkl', 'ins401']
KML_RATES = [1, 2, 5, 10]


def _build_args():
    """parse input arguments
    """
    parser = argparse.ArgumentParser(
        description='Aceinna python driver input args command:', allow_abbrev=False)

    parser.add_argument("-i", "--interface", dest="interface",  metavar='',
                        help="Interface. Allowed one of values: {0}".format(INTERFACE_LIST), default=INTERFACES.UART, choices=INTERFACE_LIST)
    parser.add_argument("-p", "--port", dest='port',  metavar='', type=int,
                        help="Webserver port")
    parser.add_argument("--device-type", dest="device_type", type=str,
                        help="Open Device Type. Allowed one of values: {0}".format(DEVICE_TYPES), choices=DEVICE_TYPES, metavar='')
    parser.add_argument("-b", "--baudrate", dest="baudrate", type=int, metavar='',
                        help="Baudrate for uart. Allowed one of values: {0}".format(BAUDRATE_LIST), choices=BAUDRATE_LIST)
    parser.add_argument("-c", "--com-port", dest="com_port", metavar='', type=str,
                        help="COM Port")
    parser.add_argument("--console-log", dest='console_log', action='store_true',
                        help="Output log on console", default=False)
    parser.add_argument("--debug", dest='debug', action='store_true',
                        help="Log debug information", default=False)
    parser.add_argument("--with-data-log", dest='with_data_log', action='store_true',
                        help="Contains internal data log (OpenIMU only)", default=False)
    parser.add_argument("-s", "--set-user-para", dest='set_user_para', action='store_true',
                        help="Set user parameters (OpenRTK only)", default=False)
    parser.add_argument("--cli", dest='use_cli', action='store_true',
                        help="start as cli mode", default=False)

    subparsers = parser.add_subparsers(
        title='Sub commands', help='use `<command> -h` to get sub command help', dest="sub_command")
    parse_log_action = subparsers.add_parser(
        'parse', help='A parse log command')
    parse_log_action.add_argument("-t", metavar='', type=str,
                                  help="Type of logs, Allowed one of values: {0}".format(
                                      TYPES_OF_LOG),
                                  default='openrtk',  dest="log_type", choices=TYPES_OF_LOG)
    parse_log_action.add_argument(
        "-p", type=str, help="The folder path of logs", default='./data', metavar='', dest="path")
    # parse_log_action.add_argument(
    #     "-i", type=int, help="Ins kml rate(hz). Allowed one of values: {0}".format(KML_RATES), default=5, metavar='', dest="kml_rate", choices=KML_RATES)

    return parser.parse_args()


def receive_args(func):
    '''
    build arguments in options
    '''
    @wraps(func)
    def decorated(*args, **kwargs):
        options = _build_args()
        kwargs['options'] = options
        func(*args, **kwargs)
    return decorated


def handle_application_exception(func):
    '''
    add exception handler
    '''
    @wraps(func)
    def decorated(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except KeyboardInterrupt:  # response for KeyboardInterrupt such as Ctrl+C
            print('User stop this program by KeyboardInterrupt! File:[{0}], Line:[{1}]'.format(
                __file__, sys._getframe().f_lineno))
            os.kill(os.getpid(), signal.SIGTERM)
            sys.exit()
        except Exception as ex:  # pylint: disable=bare-except
            if is_dev_mode():
                traceback.print_exc()  # For development
            print_red('Application Exit Exception: {0}'.format(ex))
            os._exit(1)
    return decorated


def skip_error(T: type):
    '''
    add websocket error handler
    '''
    def outer(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except T:
                pass
        return decorated
    return outer


def throttle(seconds=0, minutes=0, hours=0):
    throttle_period = timedelta(seconds=seconds, minutes=minutes, hours=hours)

    def throttle_decorator(fn):
        time_of_last_call = datetime.min

        @wraps(fn)
        def wrapper(*args, **kwargs):
            nonlocal time_of_last_call
            now = datetime.now()
            if now - time_of_last_call > throttle_period:
                time_of_last_call = now
                return fn(*args, **kwargs)
        return wrapper
    return throttle_decorator
