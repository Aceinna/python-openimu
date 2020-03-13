"""
Context
"""
from .app_logger import AppLogger


class AppContext:
    '''
    App Context
    '''
    _active_app = None
    _logger = None

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

    def set_logger(self, logger):
        '''
        logger setter
        '''
        self._logger = logger

    def get_logger(self):
        '''
        logger getter
        '''
        if not self._logger:
            self._logger = AppLogger(filename='default')
        return self._logger


APP_CONTEXT = AppContext()
