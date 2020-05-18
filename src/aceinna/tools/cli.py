import os
import sys
import argparse

try:
    from aceinna.bootstrap.cli import CommandLine
    from aceinna.framework.constants import BAUDRATE_LIST
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.bootstrap.cli import CommandLine
    from aceinna.framework.constants import BAUDRATE_LIST


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
    parser.add_argument("--console-log", dest='console_log', action='store_true',
                        help="Output log on console", default=False)
    parser.add_argument("--debug", dest='debug', action='store_true',
                        help="Log debug information", default=False)
    parser.add_argument("--with-data-log", dest='with_data_log', action='store_true',
                        help="Contains internal data log (OpenIMU only)", default=False)
    parser.add_argument("--with-raw-log", dest='with_raw_log', action='store_true',
                        help="Contains raw data log (OpenRTK only)", default=False)
    return parser.parse_args()


def main():
    '''start'''
    input_args = receive_args()
    command_line = CommandLine(
        device_type=input_args.device_type,
        com_port=input_args.com_port,
        port=input_args.port,
        baudrate=input_args.baudrate,
        console_log=input_args.console_log,
        debug=input_args.debug,
        with_data_log=input_args.with_data_log,
        with_raw_log=input_args.with_raw_log
    )
    command_line.listen()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:  # response for KeyboardInterrupt such as Ctrl+C
        print('User stop this program by KeyboardInterrupt! File:[{0}], Line:[{1}]'.format(
            __file__, sys._getframe().f_lineno))
        sys.exit()
    except:  # pylint: disable=bare-except
        os._exit(1)
