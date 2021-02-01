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
    _print_logger=None

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

    def set_print_logger(self,logger):
        self._print_logger = logger

    def get_print_logger(self):
        if not self._print_logger:
            self._print_logger = AppLogger(filename='default')
        return self._print_logger


APP_CONTEXT = AppContext()
