from ..base.uart_base import OpenDeviceBase
from ..configs.openimu_predefine import *


class Provider(OpenDeviceBase):
    def __init__(self, communicator):
        self.communicator = communicator
        pass

    def ping(self):
        device_info_text = self.internal_input_command('pG')
        app_info_text = self.internal_input_command('gV')

        print(self.device_info)
        print(self.app_info)
        if device_info_text.find('OpenRTK') > -1:
            return True
        return False

    def build_device_info(self, text):
        split_text = text.split(' ')
        self.device_info = {
            'name': split_text[0],
            'pn': split_text[1],
            'firmware_version': split_text[2],
            'sn': split_text[3]
        }

    def build_app_info(self, text):
        split_text = text.split(' ')
        self.app_info = {
            'app_name': split_text[1],
            'version': split_text[2]
        }


    def load_properties(self):
        self.app_config_folder = os.path.join(
            os.getcwd(), 'setting', 'openrtk')

        if not os.path.exists(self.app_config_folder):
            print('downloading config json files from github, please waiting for a while')
            os.makedirs(self.app_config_folder)

            filepath = self.app_config_folder + '/' + json_file_name

            try:
                r = requests.get(url)
                with open(filepath, "wb") as code:
                    code.write(r.content)
            except Exception as e:
                print(e)

        # Load the basic openimu.json(IMU application)
        with open(os.path.join(self.app_config_folder, json_file_name)) as json_data:
            self.properties = json.load(json_data)

        # TODO: maybe we need a base config file
        pass

    def start_stream(self):
        pass

    def stop_stream(self):
        pass

    def start_log(self):
        pass

    def stop_log(self):
        pass

    def get_parameters(self):
        pass

    def set_parameters(self):
        pass

    def get_parameter(self):
        pass

    def set_parameter(self):
        pass

    def upgrade(self):
        pass

    def on(self, data_type, callback):
        pass
