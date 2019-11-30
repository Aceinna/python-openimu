import time
from . import app

helper = app.framework.utils.helper


class Test:
    def discovered_device(self, device):
        print('before ja', device.device_info)
        self.jump_back_app()
        device.ping()
        print('after ja', device.device_info)

    def jump_back_app(self):
        command_line = helper.build_bootloader_input_packet('JA')
        print(command_line)
        self.serial.write(command_line)
        time.sleep(5)
        result = self.serial.read(7)
        print(result)

    def run(self):
        self.serial = app.framework.communicator.SerialPort()
        self.serial.find_device(self.discovered_device)
