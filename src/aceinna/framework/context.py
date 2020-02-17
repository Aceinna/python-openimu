"""
Context
"""
class AppContext:
    '''
    App Context
    '''
    _active_app = None

    def __init__(self):
        pass

    def set_app(self, app):
        '''
        app setter
        '''
        self._active_app = app

    def get_app(self):
        '''
        app getter
        '''
        return self._active_app


APP_CONTEXT = AppContext()
