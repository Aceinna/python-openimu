import sys
try:
    from aceinna.bootstrap import Default
    from aceinna.framework.decorator import handle_application_exception
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.bootstrap import Default
    from aceinna.framework.decorator import handle_application_exception

@handle_application_exception
def simple_start():
    app = Default()
    app.listen()

@handle_application_exception
def parameters_start():
    app = Default(
        device_type='IMU',
        com_port='COM1',
        port=8001,
        baudrate=115200,
        debug=True)
    app.listen()


if __name__ == '__main__':
    simple_start()
    # parameters_start()
