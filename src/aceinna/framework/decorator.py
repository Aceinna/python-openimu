import os
import sys
import argparse
import traceback
from functools import wraps
from typing import TypeVar
from .constants import (DEVICE_TYPES, BAUDRATE_LIST)
from .utils.print import print_red
from .utils.resource import is_dev_mode


T = TypeVar('T')


def _build_args():
    """parse input arguments
    """
    parser = argparse.ArgumentParser(
        description='Aceinna python driver input args command:', allow_abbrev=False)

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
    parser.add_argument("-s", "--set-user-para", dest='set_user_para', action='store_true',
                        help="set user parameters (OpenRTK only)", default=False)
    parser.add_argument("-n", "--ntrip-client", dest='ntrip_client', action='store_true',
                        help="enable ntrip client (OpenRTK only)", default=False)
    parser.add_argument("--cli", dest='use_cli', action='store_true',
                        help="start as cli mode", default=False)
    parser.add_argument("-f", dest='force_bootloader', action='store_true',
                        help="Force to bootloader", default=False)


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
            # APP.stop()
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
