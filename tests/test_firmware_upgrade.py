import os
import sys
import time
try:
    from aceinna.models import WebserverArgs
    from aceinna.core.driver import (Driver, DriverEvents)
    from aceinna.framework import AppLogger
    from aceinna.framework.utils import resource
    from aceinna.framework.context import APP_CONTEXT

except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.models import WebserverArgs
    from aceinna.core.driver import (Driver, DriverEvents)
    from aceinna.framework import AppLogger
    from aceinna.framework.utils import resource
    from aceinna.framework.context import APP_CONTEXT

setattr(sys, '__dev__', True)

def build_firmware_list():
    files = []
    for item in os.scandir('./upgrade'):
        if item.is_file() and '.bin' in item.name:
            files.append(item.path)

    files.sort()
    return files


def get_file(loop_times=1):
    file_list = build_firmware_list()
    current_loop = 0

    while current_loop < loop_times:
        item_index = 0
        while item_index < len(file_list):
            yield file_list[item_index]
            item_index += 1

        item_index -= 1

        while item_index > 0:
            yield file_list[item_index-1]
            item_index -= 1
        current_loop += 1


generator = get_file(1)


def gen_upgrade_file_name():
    try:
        return next(generator)
    except:
        return None


class TestApp:
    driver: Driver
    device_lost: bool
    firmware_file: str

    def __init__(self):
        self.firmware_file = ''
        self.device_lost = False
        self.driver = None

    def do_upgrade(self):
        return
        firmware_file_path = gen_upgrade_file_name()
        print('Plan to upgrade:', firmware_file_path)
        if firmware_file_path:
            self.driver.execute('upgrade_framework', firmware_file_path)
        else:
            print('Upgrade done.')
            os._exit(1)

    def handle_discovered(self, device_provider):
        if self.device_lost:
            return

        self.do_upgrade()

    def handle_lost(self):
        self.device_lost = True
        os._exit(1)

    def handle_upgrade_finished(self):
        print('Finish upgrade')

        # continue upgrade next firmeware
        self.do_upgrade()

    def handle_upgrade_fail(self, code, message):
        print('Upgrade fail', code, message)

        # continue upgrade next firmeware
        self.do_upgrade()

    def handle_error(self, error, message):
        print('driver encounter error')
        print(message)

    def start(self):
        self._prepare_logger()

        self.driver = Driver(WebserverArgs())
        self.driver.on(DriverEvents.Discovered, self.handle_discovered)
        self.driver.on(DriverEvents.Lost, self.handle_lost)
        self.driver.on(DriverEvents.UpgradeFinished,
                       self.handle_upgrade_finished)
        self.driver.on(DriverEvents.UpgradeFail, self.handle_upgrade_fail)
        self.driver.on(DriverEvents.Error, self.handle_error)
        self.driver.detect()

    def _prepare_logger(self):
        '''
        Set default log handler: console logger, file logger
        '''
        executor_path = resource.get_executor_path()
        log_level = 'info'

        APP_CONTEXT.set_logger(
            AppLogger(
                filename=os.path.join(executor_path, 'loggers', 'test.log'),
                gen_file=True,
                level=log_level,
                console_log=False
            ))


def print_path():
    file_path = gen_upgrade_file_name()
    if file_path:
        print(file_path)
        print_path()


if __name__ == '__main__':
    TestApp().start()
    # print_path()
