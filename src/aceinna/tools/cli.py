from aceinna.bootstrap import Loader
from aceinna.framework.decorator import (
    receive_args, handle_application_exception)


@handle_application_exception
@receive_args
def main(**kwargs):
    '''
    Work as command line, with WebSocket and UART
    '''
    application = Loader.create('cli', vars(kwargs['options']))
    application.listen()


if __name__ == '__main__':
    main()
