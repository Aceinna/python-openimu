"""
Development Entry
"""
import os
import sys
import signal
import time
from aceinna.bootstrap import Loader
from aceinna.framework.decorator import (
    receive_args, handle_application_exception)

IS_WINDOWS = sys.platform.__contains__(
    'win32') or sys.platform.__contains__('win64')
IS_LATER_PY_38 = sys.version_info > (3, 8)


def kill_app(signal_int, call_back):
    '''Kill main thread
    '''
    os.kill(os.getpid(), signal.SIGTERM)


@handle_application_exception
@receive_args
def from_command_line(**kwargs):
    '''
    Work as command line, with WebSocket and UART
    '''
    sub_command = kwargs['options'].sub_command
    option_mode = 'cli'

    if sub_command == 'parse':
        option_mode = 'log-parser'

    application = Loader.create(option_mode, vars(kwargs['options']))
    application.listen()


@handle_application_exception
@receive_args
def start_app(**kwargs):
    '''
    Start the application with specified parameters
    '''
    sub_command = kwargs['options'].sub_command
    option_mode = 'default'

    if kwargs['options'].use_cli:
        option_mode = 'cli'

    if sub_command == 'parse':
        option_mode = 'log-parser'

    application = Loader.create(option_mode, vars(kwargs['options']))
    application.listen()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, kill_app)
    # compatible code for windows python 3.8
    if IS_WINDOWS and IS_LATER_PY_38:
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    start_app()

    while True:
        time.sleep(10)
