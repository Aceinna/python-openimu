import os
import logging
from logging import handlers


class MessageStoreHandler(logging.Handler):
    def __init__(self, store):
        logging.Handler.__init__(self)
        self._store = store

    def mapLogRecord(self, record):
        return record.__dict__

    def emit(self, record):
        msg = self.mapLogRecord(record)
        self._store.append(msg)


class AppLogger(object):
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'crit': logging.CRITICAL
    }

    def __init__(self, filename, level='info', when='D',
                 backCount=1, gen_file=False, console_log=False,
                 fmt='%(asctime)s - %(levelname)s: %(message)s'):
                #  fmt='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'):
        self._store = None
        self.logger = logging.getLogger(__file__)
        self.format_str = logging.Formatter(fmt)
        self.logger.setLevel(self.level_relations.get(level))
        self.logger.propagate = False
        if console_log:
            console_output = logging.StreamHandler()
            console_output.setFormatter(self.format_str)
            self.logger.addHandler(console_output)

        if gen_file:
            folder_path = os.path.dirname(filename)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            daily_file_output = handlers.TimedRotatingFileHandler(
                filename=filename, when=when, backupCount=backCount, encoding='utf-8')
            daily_file_output.setFormatter(self.format_str)
            self.logger.addHandler(daily_file_output)

    def enable_msg_store_handler(self, store):
        if not self._store:
            self._store = MessageStoreHandler(store)
            self._store.setFormatter(self.format_str)
            self.logger.addHandler(self._store)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)
