import os
import re
import time
import json
import struct
import datetime
import threading
from ..base import OpenDeviceBase
from ..decorator import with_device_message
from ...framework.utils import (helper, resource)
from . import dmu_helper
from .configuration_field import CONFIGURATION_FIELD_DEFINES_SINGLETON
from .eeprom_field import EEPROM_FIELD_DEFINES_SINGLETON
from ..upgrade_workers import (
    FirmwareUpgradeWorker,
    JumpBootloaderWorker,
    JumpApplicationWorker,
    UPGRADE_EVENT
)

ID = [0x49, 0x44]
VR = [0x56, 0x52]
S0 = [0x53, 0x30]


class Provider(OpenDeviceBase):
    '''
    DMU UART provider
    '''

    def __init__(self, communicator, *args):
        super(Provider, self).__init__(communicator)
        self.type = 'DMU'
        self.server_update_rate = 50
        self.is_logging = False
        self.is_mag_align = False
        self.bootloader_baudrate = 57600
        # self.device_info = None
        # self.app_info = None
        self.app_config_folder = ''
        self.parameters = None
        self.enable_data_log = True
        self.is_backup = False
        self.is_restore = False
        self.is_app_matched = False
        self.is_conf_loaded = False
        self.connected = True
        self.device_info = None
        self.app_info = None
        self.prepare_folders()

    def prepare_folders(self):
        '''
        Prepare folder
        '''
        '''
        Prepare folders for data storage and configuration
        '''
        executor_path = resource.get_executor_path()
        setting_folder_name = 'setting'
        config_file_name = 'dmu.json'
        data_folder_path = os.path.join(executor_path, 'data')
        if not os.path.isdir(data_folder_path):
            os.makedirs(data_folder_path)

        self.setting_folder_path = os.path.join(
            executor_path, setting_folder_name, 'dmu')

        config_file_path = os.path.join(
            self.setting_folder_path, config_file_name)

        if not os.path.isfile(config_file_path):
            if not os.path.isdir(self.setting_folder_path):
                os.makedirs(self.setting_folder_path)

            app_config_content = resource.get_content_from_bundle(
                setting_folder_name, os.path.join('dmu', config_file_name))

            with open(config_file_path, "wb") as code:
                code.write(app_config_content)

    @property
    def is_in_bootloader(self):
        ''' Check if the connected device is in bootloader mode
        '''
        if not self.device_info or not self.device_info.__contains__('name'):
            return False

        if 'bootloader' in self.device_info['name'].lower():
            return True
        return False

    def bind_device_info(self, device_access, device_info, app_info):
        self._build_device_info(device_info)
        self._build_app_info(app_info)
        self.connected = True

        device_string = '{0} {1} {2}'.format(
            self.device_info['name'], self.device_info['pn'], self.device_info['sn'])
        return '# Connected {0} #\n\rDevice: {1} \n\rFirmware: {2}'\
            .format('DMU', device_string, self.device_info['firmware_version'])

    def _build_device_info(self, data_buffer):
        '''
        Build device info
        '''
        if data_buffer is None:
            return False

        serial_num = int.from_bytes(struct.pack(
            '4B', *data_buffer[0:4]), byteorder='big')

        mode_string_len = len(data_buffer[4:])
        model_string = struct.pack('{0}B'.format(
            mode_string_len), *data_buffer[4:]).decode()

        split_text = model_string.split(' ')

        self.device_info = {
            'name': split_text[0],
            'pn': split_text[1],
            'firmware_version': split_text[2],
            'sn': serial_num
        }

    def _build_app_info(self, data_buffer):
        '''
        Build app info
        '''
        if data_buffer is None:
            return False

        version_string = '{0}.{1}.{2}.{3}.{4}'.format(*data_buffer)

        self.app_info = {
            'app_name': 'DMU',
            'version': version_string
        }
        return True

    def load_properties(self):
        # Load config from user working path
        local_config_file_path = os.path.join(os.getcwd(), 'dmu.json')
        if os.path.isfile(local_config_file_path):
            with open(local_config_file_path) as json_data:
                self.properties = json.load(json_data)
                return

        app_file_path = os.path.join(
            self.setting_folder_path, 'dmu.json')

        with open(app_file_path) as json_data:
            self.properties = json.load(json_data)
            CONFIGURATION_FIELD_DEFINES_SINGLETON.load(
                self.properties['userConfiguration'])
            EEPROM_FIELD_DEFINES_SINGLETON.load()

    def after_setup(self):
        self.is_conf_loaded = False
        if hasattr(self.communicator, 'serial_port'):
            self.original_baudrate = self.communicator.serial_port.baudrate

    def on_read_raw(self, data):
        pass

    def on_receive_output_packet(self, packet_type, data, *args, **kwargs):
        '''
        Listener for getting output packet
        '''
        self.add_output_packet(packet_type, data)

    def get_log_info(self):
        '''
        Build information for log
        '''
        if not self.parameters:
            self.get_params()

        input_params = self.properties['userConfiguration']
        packet_rate = next(
            (item['value'] for item in self.parameters if item['name'] == 'Packet Rate'), '100')

        value_mapping = next(
            (item['options'] for item in input_params if item['name'] == 'Packet Rate'), [])

        packet_rate_value = next(
            (item['value'] for item in value_mapping if item['key'] == str(packet_rate)), '0')

        return {
            "type": 'IMU',
            "model": self.device_info['name'],
            "logInfo": {
                "pn": self.device_info['pn'],
                "sn": self.device_info['sn'],
                "sampleRate": packet_rate_value,
                "appVersion": self.device_info['firmware_version'],
                "imuProperties": json.dumps(self.properties)
            }
        }

    def before_jump_app_command(self):
        self.communicator.serial_port.baudrate = self.bootloader_baudrate


    def after_jump_app_command(self):
        self.communicator.serial_port.baudrate = self.original_baudrate

    def before_write_content(self):
        self.communicator.serial_port.baudrate = self.bootloader_baudrate
        self.communicator.serial_port.reset_input_buffer()

    def firmware_write_command_generator(self, data_len, current, data):
        command_WA = 'WA'
        message_bytes = []
        message_bytes.extend(struct.pack('>I', current))
        message_bytes.extend(struct.pack('B', data_len))
        message_bytes.extend(data)
        return helper.build_packet(command_WA, message_bytes)

    def get_upgrade_workers(self, firmware_content):
        firmware_worker = FirmwareUpgradeWorker(
            self.communicator, firmware_content,
            self.firmware_write_command_generator)
        firmware_worker.on(UPGRADE_EVENT.BEFORE_WRITE,
                           lambda: self.before_write_content())
        firmware_worker.on(
            UPGRADE_EVENT.FIRST_PACKET, lambda: time.sleep(8))

        jump_bootloader_command = helper.build_bootloader_input_packet(
            'JI')
        jump_bootloader_worker = JumpBootloaderWorker(
            self.communicator,
            command=jump_bootloader_command,
            listen_packet='JI',
            wait_timeout_after_command=3)

        jump_application_command = helper.build_bootloader_input_packet('JA')
        jump_application_worker = JumpApplicationWorker(
            self.communicator,
            command=jump_application_command,
            listen_packet='JA',
            wait_timeout_after_command=3)
        jump_application_worker.on(UPGRADE_EVENT.BEFORE_COMMAND, self.before_jump_app_command)
        jump_application_worker.on(UPGRADE_EVENT.AFTER_COMMAND, self.after_jump_app_command)

        return [jump_bootloader_worker, firmware_worker, jump_application_worker]

    def get_device_connection_info(self):
        return {
            'modelName': self.device_info['name'],
            'deviceType': self.type,
            'serialNumber': self.device_info['sn'],
            'partNumber': self.device_info['pn'],
            'firmware': self.device_info['firmware_version']
        }

    def get_operation_status(self):
        if self.is_logging:
            return 'LOGGING'

        if self.is_upgrading:
            return 'UPGRADING'

        if self.is_mag_align:
            return 'MAG_ALIGN'

        return 'IDLE'

    def get_device_info(self, *args):  # pylint: disable=unused-argument
        '''
        Get device information
        '''
        return {
            'packetType': 'deviceInfo',
            'data':  [
                {'name': 'Product Name',
                 'value': self.device_info['name']},
                {'name': 'PN', 'value': self.device_info['pn']},
                {'name': 'Firmware Version',
                 'value': self.device_info['firmware_version']},
                {'name': 'SN', 'value': self.device_info['sn']}
            ]
        }

    @with_device_message
    def get_conf(self, *args):  # pylint: disable=unused-argument
        '''
        Get json configuration
        '''
        outputs = self.properties['userMessages']['outputPackets']
        input_params = self.properties['userConfiguration']

        if self.is_conf_loaded:
            yield {
                'packetType': 'conf',
                'data': {
                    'outputs': outputs,
                    'inputParams': input_params
                }
            }
        # read product configuration
        eeprom_field = EEPROM_FIELD_DEFINES_SINGLETON.find(0x71C)
        command_line = dmu_helper.build_read_eeprom_cli(eeprom_field)
        result = yield self._message_center.build(command=command_line, timeout=3)

        data = result['data']

        if data:
            packet_types = dmu_helper.build_continous_packet_types(
                data['value']['architechture'],
                data['value']['algorithm'],
                data['value']['mags'])

            if self.device_info['name'].__contains__('INS330BI'):
                packet_types.append('E3')

            for item in input_params:
                if item['name'] == 'Packet Type':
                    # product_configuration['continuous_packet_types']
                    item['options'] = packet_types
                    self.is_conf_loaded = True
                    break

        yield {
            'packetType': 'conf',
            'data': {
                'outputs': outputs,
                'inputParams': input_params
            }
        }

    @with_device_message
    def get_params(self, *args):  # pylint: disable=unused-argument
        '''
        Get all parameters
        '''
        fields = CONFIGURATION_FIELD_DEFINES_SINGLETON.get_fields()
        command_line = dmu_helper.build_read_fields_packets(fields)
        result = yield self._message_center.build(command=command_line, timeout=3)

        data = result['data']

        if data:
            self.parameters = data
            yield {
                'packetType': 'inputParams',
                'data': data
            }
        yield {
            'packetType': 'error',
            'data': 'No Response'
        }

    @with_device_message
    def get_param(self, params, *args):  # pylint: disable=unused-argument
        '''
        Update paramter value
        '''
        field = CONFIGURATION_FIELD_DEFINES_SINGLETON.find(params['paramId'])
        if field is None:
            yield {
                'packetType': 'error',
                'data': 'Invalid Parameter'
            }

        command_line = dmu_helper.build_read_fields_packets([field])

        result = yield self._message_center.build(command=command_line)

        data = result['data']
        error = result['error']

        if error:
            yield {
                'packetType': 'error',
                'data': 'No Response'
            }

        if data:
            yield {
                'packetType': 'inputParam',
                'data': data[0]
            }
        yield {
            'packetType': 'error',
            'data': 'No Response'
        }

    def set_params(self, params, *args):  # pylint: disable=unused-argument
        raise Exception('Not implement set params.')

    @with_device_message
    def set_param(self, params, *args):  # pylint: disable=unused-argument
        '''
        Update paramter value
        '''
        configuration_field = CONFIGURATION_FIELD_DEFINES_SINGLETON.find(
            params['paramId'])

        if configuration_field.name == 'Unknown':
            yield {
                'packetType': 'error'
            }

        if configuration_field is None:
            yield {
                'packetType': 'error'
            }

        command_line = dmu_helper.build_write_filed_cli(
            configuration_field, params['value'])

        result = yield self._message_center.build(command=command_line)

        error = result['error']
        data = result['data']
        if error:
            yield {
                'packetType': 'error',
                'data': {
                    'error': error
                }
            }

        yield {
            'packetType': 'success',
            'data': {
                'error': data
            }
        }

    @with_device_message
    def save_config(self, *args):  # pylint: disable=unused-argument
        '''
        Save configuration
        '''
        # read current configuration fields, then write field to eeprom
        fields = CONFIGURATION_FIELD_DEFINES_SINGLETON.get_fields()
        command_line = dmu_helper.build_read_fields_packets(fields)
        result = yield self._message_center.build(command=command_line, timeout=3)

        data = result['data']
        values = [item['value'] for item in data]
        # print('saved values', values)

        command_line = dmu_helper.build_write_fileds_cli(fields, values, True)
        result = yield self._message_center.build(command=command_line, timeout=3)

        data = result['data']
        error = result['error']
        if data:
            yield {
                'packetType': 'success',
                'data': data
            }

        yield {
            'packetType': 'success',
            'data': error
        }

    @with_device_message
    def run_command(self, params, *args):
        ''' run raw command
        '''
        bytes_str_in_array = re.findall('([a-f|0-9|A-F]{2})', params)

        command_line = bytes([int(item, 16) for item in bytes_str_in_array])

        result = yield self._message_center.build(command=command_line, timeout=2)

        error = result['error']
        raw = result['raw']

        if error:
            yield {
                'packetType': 'error',
                'data': {
                    'error': 'Runtime Error',
                    'message': 'The device cannot response the command'
                }
            }

        yield {
            'packetType': 'success',
            'data': raw
        }

    def upgrade_framework(self, params, *args):  # pylint: disable=invalid-name
        '''
        upgrade framework
        '''
        file = ''
        if isinstance(params, str):
            file = params

        if isinstance(params, dict):
            file = params['file']

        # start a thread to do upgrade
        if not self.is_upgrading:
            self.is_upgrading = True
            self._message_center.pause()

            if self._logger is not None:
                self._logger.stop_user_log()

            thead = threading.Thread(
                target=self.thread_do_upgrade_framework, args=(file,))
            thead.start()
            print("Upgrade DMU firmware started at:[{0}].".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        return {
            'packetType': 'success'
        }
