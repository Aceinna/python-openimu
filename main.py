import sys
import argparse
import src.bootstrap.bootstrap_factory as bootstrap_factory

def receive_args():
    parser = argparse.ArgumentParser()
    parser.description = argparse.ArgumentParser(
        description='Aceinna python driver input args command:')
    parser.add_argument("-host", type=str, help="host type", default='web')
    # for host as web
    parser.add_argument("-p", type=int, help="webserver port", default=8123)
    parser.add_argument("-b", type=int, help="baudrate")
    return parser.parse_args()


if __name__ == '__main__':
    args = receive_args()
    platform = args.host
    try:
        app = bootstrap_factory.create(platform, options=args)
        app.listen()
    except KeyboardInterrupt:  # response for KeyboardInterrupt such as Ctrl+C
        print('User stop this program by KeyboardInterrupt! File:[{0}], Line:[{1}]'.format(
            __file__, sys._getframe().f_lineno))
        app.stop()
        #logging.info("User stop this program by KeyboardInterrupt!")
        sys.exit()
    except Exception as e:
        #logging.info("server main function exception:{0}".format(e))
        print(e)
