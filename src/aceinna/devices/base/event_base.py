class EventBase(object):
    '''
    Event Object Base
    '''

    def __init__(self):
        self.listeners = {}

    def on(self, event_type, handler):
        '''
        Listen event
        '''
        if not self.listeners.__contains__(event_type):
            self.listeners[event_type] = []

        self.listeners[event_type].append(handler)

    def emit(self, event_type, *args, **kwargs):
        '''
        Trigger event
        '''
        if not self.listeners.keys().__contains__(event_type):
            return

        handlers = self.listeners[event_type]
        if handlers is not None and len(handlers) > 0:
            for handler in handlers:
                handler(*args, **kwargs)
