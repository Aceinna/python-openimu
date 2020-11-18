import functools
from .message_center import (DeviceMessage)


def with_device_message(func):
    '''
    This is a decorator for method with DeviceMessage, it would looks like
    code: yield message_center.build(command=command_line)
    '''

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        generator_func = func(*args, **kwargs)
        global generator_result
        generator_result = None

        def check_result():
            global generator_result
            while not generator_result:
                continue

            if generator_result:
                next_device_message = generator_func.send(generator_result)
                if isinstance(next_device_message, DeviceMessage):
                    generator_result = None
                    next_device_message.on('finished', on_resolve)
                    next_device_message.send()
                    return check_result()
                else:
                    return next_device_message

        def on_resolve(*args, **kwargs):
            global generator_result
            generator_result = {
                'packet_type': kwargs['packet_type'],
                'data': kwargs['data'],
                'error': kwargs['error'],
                'raw': kwargs['raw']
            }

        try:
            device_message = generator_func.send(None)
            if isinstance(device_message, DeviceMessage):
                device_message.on('finished', on_resolve)
                device_message.send()
                return check_result()
            else:
                return device_message
        except StopIteration as ex:
            value = {
                'packetType': 'error',
                'data': 'No Response'
            }

            if hasattr(ex, 'value'):
                value = ex.value
            return value

    return wrapper
