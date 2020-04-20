import functools
from .message_center import (DeviceMessage, EventMessage)


def with_device_message(func):
    '''
    This is a decorator for method with DeviceMessage, it would looks like
    code: yield message_center.build(command=command_line)
    '''
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        event_message = EventMessage()
        generator_func = func(*args, **kwargs)

        def on_resolve(packet_type, data, error):
            try:
                next_device_message = generator_func.send({
                    'packet_type': packet_type,
                    'data': data,
                    'error': error
                })

                if isinstance(device_message, DeviceMessage):
                    next_device_message.on('finished', on_resolve)
                    next_device_message.send()
            except StopIteration as ex:
                event_message.set_result(ex.value)

        try:
            device_message = generator_func.send(None)
            if isinstance(device_message, DeviceMessage):
                device_message.on('finished', on_resolve)
                device_message.send()
        except StopIteration as ex:
            event_message.set_result(ex.value)

        return event_message

    return wrapper
