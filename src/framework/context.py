class AppContext:
    _active_app = None

    def __init__(self):
        pass

    def set_app(self, app):
        self._active_app = app

    def get_app(self):
        return self._active_app


app_context = AppContext()
