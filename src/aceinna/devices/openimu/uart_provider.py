import os
import re
import sys
import time
import json
import binascii
import math
# import asyncio
import datetime
import threading
import struct
from azure.storage.blob import BlockBlobService
from ...framework.utils import helper
from ...framework.utils import resource
from ..base import OpenDeviceBase
from ..configs.openimu_predefine import (
    APP_STR,
    DEFAULT_PRODUCT_NAME,
    get_openimu_products
)
from ...framework.context import APP_CONTEXT
from ..decorator import with_device_message
from ...framework.configuration import get_config
from ..upgrade_workers import (
    FirmwareUpgradeWorker,
    FIRMWARE_EVENT_TYPE
)
from ...framework.utils.print import print_yellow


class Provider(OpenDeviceBase):
    '''
    OpenIMU UART provider
    '''

    def __init__(self, communicator, *args):
        super(Provider, self).__init__(communicator)
        self.type = 'IMU'
        self.server_update_rate = 50
        self.is_logging = False
        self.is_mag_align = False
        self.bootloader_baudrate = 57600
        self.device_info = None
        self.app_info = None
        self.app_config_folder = ''
        self.parameters = None
        self.enable_data_log = True
        self.prepare_folders()
        self.is_backup = False
        self.is_restore = False
        self.is_app_matched = False
        self.connected = True

    def prepare_folders(self):
        '''
        Prepare folders for data storage and configuration
        '''
        executor_path = resource.get_executor_path()
        setting_folder_name = 'setting'
        config_file_name = 'openimu.json'
        data_folder_path = os.path.join(executor_path, 'data')
        if not os.path.isdir(data_folder_path):
            os.makedirs(data_folder_path)

        # copy contents of app_config under executor path
        self.setting_folder_path = os.path.join(
            executor_path, setting_folder_name)

        all_products = get_openimu_products()

        for product in all_products:
            product_folder = os.path.join(self.setting_folder_path, product)
            if not os.path.isdir(product_folder):
                os.makedirs(product_folder)

            for app_name in all_products[product]:
                app_name_path = os.path.join(product_folder, app_name)
                app_name_config_path = os.path.join(
                    app_name_path, config_file_name)

                if not os.path.isfile(app_name_config_path):
                    if not os.path.isdir(app_name_path):
                        os.makedirs(app_name_path)
                    app_config_content = resource.get_content_from_bundle(
                        setting_folder_name, os.path.join(product, app_name, config_file_name))
                    if app_config_content is None:
                        continue

                    with open(app_name_config_path, "wb") as code:
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

        return '# Connected {0} #\n\rDevice:{1} \n\rFirmware:{2}'\
            .format('OpenIMU', device_info, app_info)

    def _build_device_info(self, text):
        '''
        Build device info
        '''
        split_text = [x for x in text.split(' ') if x != '' and x != '\x00']
        split_len = len(split_text)

        if split_len < 3:
            self.device_info = {
                'name': split_text[0],
                'product_name': split_text[0],
                'pn': '-',
                'firmware_version': '-',
                'sn': '-'
            }
            return

        # consier as bootloader
        if split_len == 3:
            pre_sn = split_text[2].split(':')
            serial_num = pre_sn[1] if len(pre_sn) == 2 else pre_sn[0]
            self.device_info = {
                'name': split_text[0],
                'product_name': split_text[0],
                'pn': split_text[1],
                'firmware_version': '-',
                'sn': serial_num
            }
            return

        pre_sn = split_text[-1].split(':')
        serial_num = pre_sn[1] if len(pre_sn) == 2 else ''

        self.device_info = {
            'name': ' '.join(split_text[0:-3]),
            'product_name': split_text[0],
            'pn': split_text[-3],
            'firmware_version': split_text[-2],
            'sn': serial_num
        }

    def _build_app_info(self, text):
        '''
        Build app info
        '''
        # check if J1939 in text
        product_name = ''
        app_version = text
        can_indicator = '_J1939'
        if can_indicator in app_version:
            app_version = app_version.replace(can_indicator, '')

        split_text = [x for x in app_version.split(' ') if x != '']
        app_name = next(
            (item for item in APP_STR if item in split_text), None)

        if len(split_text) == 3:
            product_name = split_text[0]

        if not app_name:
            app_name = 'IMU'
            self.is_app_matched = False
        else:
            self.is_app_matched = True

        self.app_info = {
            'app_name': app_name,
            'version': text,
            'product_name': product_name
        }

    def load_properties(self):
        # Load config from user working path
        local_config_file_path = os.path.join(os.getcwd(), 'openimu.json')
        if os.path.isfile(local_config_file_path):
            with open(local_config_file_path) as json_data:
                self.properties = json.load(json_data)
                return

        # Load the openimu.json based on its app
        product_name = self.app_info['product_name'] if self.app_info['product_name'] else self.device_info['product_name']
        app_name = self.app_info['app_name']
        app_file_path = os.path.join(
            self.setting_folder_path, product_name, app_name, 'openimu.json')

        if not os.path.isfile(app_file_path):
            app_file_path = os.path.join(
                self.setting_folder_path, DEFAULT_PRODUCT_NAME, app_name, 'openimu.json')

        if not self.is_app_matched:
            print_yellow(
                'Failed to extract app version information from unit.' +
                '\nThe supported application list is {0}.'.format(APP_STR) +
                '\nTo keep runing, use IMU configuration as default.' +
                '\nYou can choose to place your json file under exection path if it is an unknown application.')

        with open(app_file_path) as json_data:
            self.properties = json.load(json_data)

    def after_setup(self):
        pass

    def on_read_raw(self, data):
        pass

    def on_receive_output_packet(self, packet_type, data):
        '''
        Listener for getting output packet
        '''
        self.add_output_packet(packet_type, data)

    def get_log_info(self):
        '''
        Build information for log
        '''
        packet_rate = next(
            (item['value'] for item in self.parameters if item['name'] == 'Packet Rate'), '100')
        return {
            "type": self.type,
            "model": self.device_info['name'],
            "logInfo": {
                "pn": self.device_info['pn'],
                "sn": self.device_info['sn'],
                "sampleRate": packet_rate,
                "appVersion": self.app_info['version'],
                "imuProperties": json.dumps(self.properties)
            }
        }

    def get_upgrade_workers(self, firmware_content):
        firmware_worker = FirmwareUpgradeWorker(
            self.communicator, self.bootloader_baudrate, firmware_content)
        firmware_worker.on(
            FIRMWARE_EVENT_TYPE.FIRST_PACKET, lambda: time.sleep(8))
        return [firmware_worker]

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

        if self.is_backup:
            return 'BACKUP'

        if self.is_restore:
            return 'RESTORE'

        return 'IDLE'

    # command list

    def get_device_info(self, *args):  # pylint: disable=invalid-name
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
                {'name': 'SN', 'value': self.device_info['sn']},
                {'name': 'App Version', 'value': self.app_info['version']}
            ]
        }

    def get_conf(self, *args):  # pylint: disable=invalid-name
        '''
        Get json configuration
        '''
        return {
            'packetType': 'conf',
            'data': {
                'outputs': self.properties['userMessages']['outputPackets'],
                'inputParams': self.properties['userConfiguration']
            }
        }

    @with_device_message
    def get_params(self, *args):  # pylint: disable=invalid-name
        '''
        Get all parameters
        '''
        command_line = helper.build_input_packet('gA')

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
    def get_param(self, params, *args):  # pylint: disable=invalid-name
        '''
        Update paramter value
        '''
        command_line = helper.build_input_packet(
            'gP', properties=self.properties, param=params['paramId'])

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
                'data': data
            }

        yield {
            'packetType': 'error',
            'data': 'No Response'
        }

    @with_device_message
    def set_params(self, params, *args):  # pylint: disable=invalid-name
        '''
        Update paramters value
        '''
        for parameter in params:
            command_line = helper.build_input_packet(
                'uP', properties=self.properties,
                param=parameter['paramId'],
                value=parameter['value'])

            result = yield self._message_center.build(command=command_line)

            packet_type = result['packet_type']
            data = result['data']

            if packet_type == 'error':
                yield {
                    'packetType': 'error',
                    'data': {
                        'error': data
                    }
                }
            if data > 0:
                yield {
                    'packetType': 'error',
                    'data': {
                        'error': data
                    }
                }

        yield {
            'packetType': 'success',
            'data': {
                'error': 0
            }
        }

    @with_device_message
    def set_param(self, params, *args):  # pylint: disable=invalid-name
        '''
        Update paramter value
        '''
        try:
            command_line = helper.build_input_packet(
                'uP', properties=self.properties, param=params['paramId'], value=params['value'])
        except:
            yield {
                'packetType': 'error',
                'data': {
                    'error': params['paramId']
                }
            }

        result = yield self._message_center.build(command=command_line)

        error = result['error']
        data = result['data']
        if error:
            yield {
                'packetType': 'error',
                'data': {
                    'error': data
                }
            }

        yield {
            'packetType': 'success',
            'data': {
                'error': data
            }
        }

    @with_device_message
    def reset_params(self, *args):  # pylint: disable=unused-argument
        '''
        Reset params to default
        '''
        command_line = helper.build_input_packet('rD')
        result = yield self._message_center.build(command=command_line, timeout=2)

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
            'data': data
        }

    @with_device_message
    def save_config(self, *args):  # pylint: disable=unused-argument
        '''
        Save configuration
        '''
        command_line = helper.build_input_packet('sC')
        result = yield self._message_center.build(command=command_line)

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

    def mag_align_start(self, *args):  # pylint: disable=unused-argument
        '''
        Start mag align action
        '''
        if not self.is_mag_align:
            self.is_mag_align = True

            thread = threading.Thread(
                target=self.thread_do_mag_align, args=())
            thread.start()

        return {
            'packetType': 'success'
        }

    @with_device_message
    def thread_do_mag_align(self):
        '''
        Do mag align
        '''
        try:
            command_line = helper.build_input_packet(
                'ma', self.properties, 'start')
            # self.communicator.write(command_line)
            # result = self.get_input_result('ma', timeout=3)
            result = yield self._message_center.build(command=command_line, timeout=3)
            time.sleep(1)
            has_result = False
            while not has_result:
                command_line = helper.build_input_packet(
                    'ma', self.properties, 'status')
                result = yield self._message_center.build(command=command_line)

                if not self.is_mag_align:
                    break

                if result['data'] == [0]:
                    has_result = True
                else:
                    time.sleep(0.5)

            if not has_result:
                return

            command_line = helper.build_input_packet(
                'ma', self.properties, 'stored')

            result = yield self._message_center.build(command=command_line)

            mag_value = dict()

            if len(result['data']) > 0:
                decoded_status = binascii.hexlify(bytes(result['data']))
                mag_value = self.decode_mag_align_output(decoded_status)
            else:
                command_line = helper.build_input_packet(
                    'ma', self.properties, 'abort')

            self.is_mag_align = False

            # TODO: reset packet rate after operation successful
            self.add_output_packet('mag_status', {
                'status': 'complete',
                'value': mag_value
            })
        except Exception as ex:  # pylint: disable=broad-except
            APP_CONTEXT.get_logger().error(ex)
            self.is_mag_align = False
            self.add_output_packet('mag_status', {
                'status': 'error'
            })

    @with_device_message
    def mag_align_abort(self, *args):  # pylint: disable=invalid-name
        '''
        Abort mag align action
        '''
        self.is_mag_align = False

        time.sleep(0.5)
        command_line = helper.build_input_packet(
            'ma', self.properties, 'abort')
        result = yield self._message_center.build(command=command_line)
        # print('mag abort result', result['data'])

        if result['error']:
            yield {
                'packetType': 'error',
                'data': {
                    'error': 1
                }
            }
        else:
            yield {
                'packetType': 'success'
            }

    @with_device_message
    def mag_align_save(self, *args):  # pylint: disable=invalid-name
        '''
        Save mag align resut
        '''
        command_line = helper.build_input_packet(
            'ma', self.properties, 'save')
        # self.communicator.write(command_line)
        # result = self.get_input_result('ma', timeout=1)
        result = yield self._message_center.build(command=command_line)

        if result['error']:
            yield {
                'packetType': 'error',
                'data': {
                    'error': 1
                }
            }

        yield {
            'packetType': 'success'
        }

    def decode_mag_align_output(self, value):
        '''
        decode mag align output
        '''
        hard_iron_x = dict()
        hard_iron_y = dict()
        soft_iron_ratio = dict()
        soft_iron_angle = dict()

        hard_iron_x['paramId'] = next(
            (item['paramId'] for item in self.properties['userConfiguration']
             if item.__contains__('argument') and item['argument'] == 'hard_iron_x'), None)
        hard_iron_x['value'] = self.hard_iron_cal(value[16:20], 'axis')
        hard_iron_x['name'] = 'Hard Iron X'
        hard_iron_x['argument'] = 'hard_iron_x'

        hard_iron_y['paramId'] = next(
            (item['paramId'] for item in self.properties['userConfiguration']
             if item.__contains__('argument') and item['argument'] == 'hard_iron_y'), None)
        hard_iron_y['value'] = self.hard_iron_cal(value[20:24], 'axis')
        hard_iron_y['name'] = 'Hard Iron Y'
        hard_iron_y['argument'] = 'hard_iron_y'

        soft_iron_ratio['paramId'] = next(
            (item['paramId'] for item in self.properties['userConfiguration']
             if item.__contains__('argument') and item['argument'] == 'soft_iron_ratio'), None)
        soft_iron_ratio['value'] = self.hard_iron_cal(value[24:28], 'ratio')
        soft_iron_ratio['name'] = 'Soft Iron Ratio'
        soft_iron_ratio['argument'] = 'soft_iron_ratio'

        soft_iron_angle['paramId'] = next(
            (item['paramId'] for item in self.properties['userConfiguration']
             if item.__contains__('argument') and item['argument'] == 'soft_iron_angle'), None)
        soft_iron_angle['value'] = self.hard_iron_cal(value[28:32], 'angle')
        soft_iron_angle['name'] = 'Soft Iron Angle'
        soft_iron_angle['argument'] = 'soft_iron_angle'

        output = [hard_iron_x, hard_iron_y, soft_iron_ratio, soft_iron_angle]

        return output

    def hard_iron_cal(self, value, data_type):
        '''
        convert hard iron value
        '''
        decoded_value = int(value, 16)
        # print (decodedValue)
        if data_type == 'axis':
            if decoded_value > 2 ** 15:
                new_decoded_value = (decoded_value - 2 ** 16)
                return new_decoded_value / float(2 ** 15) * 8
            else:
                return decoded_value / float(2 ** 15) * 8

        if data_type == 'ratio':
            return decoded_value / float(2 ** 16 - 1)

        if data_type == 'angle':
            if decoded_value > 2 ** 15:
                decoded_value = decoded_value - 2 ** 16
                pi_value = 2 ** 15 / math.pi
                return decoded_value / pi_value

            pi_value = 2 ** 15 / math.pi
            return decoded_value / pi_value

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
            print("Upgrade OpenIMU firmware started at:[{0}].".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        return {
            'packetType': 'success'
        }

    def backup_calibration(self, params):
        '''
        start a thread to backup
        '''
        if not self.is_backup:
            self.is_backup = True
            self.ans_platform.set_access_token(params['token'])
            thread = threading.Thread(
                target=self.thread_do_backup, args=())
            thread.start()

        return {
            'packetType': 'success'
        }

    def restore_calibration(self, params):
        '''
        start a thread to restore
        '''
        # if not self.is_restore:
        #     self.is_restore = True
        #     self.ans_platform.set_access_token(params['token'])
        #     thread = threading.Thread(
        #         target=self.thread_do_restore, args=())
        #     thread.start()

        return {
            'packetType': 'success'
        }

    @with_device_message
    def thread_do_backup(self):
        '''
        Do Calibration Backup
        '''
        # get current odr
        packet_rate_param_index = 4
        command_line = helper.build_input_packet(
            'gP', properties=self.properties, param=packet_rate_param_index)
        packet_rate_result = yield self._message_center.build(command=command_line)

        if packet_rate_result['error']:
            self.is_backup = False
            self.add_output_packet('backup_status', {
                'status': 'fail'
            })

            return

        # set quiet
        command_line = helper.build_input_packet(
            'uP', properties=self.properties, param=packet_rate_param_index, value=0)
        result = yield self._message_center.build(command=command_line)

        if packet_rate_result['error']:
            self.is_backup = False
            self.add_output_packet('backup_status', {
                'status': 'fail'
            })

            return

        file_name = self.device_info['sn']+'.bin'  # todo: sn-yyyy-mm-dd-hhmmss
        start = 0x0
        read_size = 0x7E
        max_length = 4096
        file_write_size = 0
        file_result = bytearray()

        while file_write_size < max_length:
            actual_read_size = read_size
            plan_file_write_size = file_write_size + actual_read_size

            if plan_file_write_size >= max_length:
                actual_read_size = max_length - file_write_size

            command_line = helper.build_read_eeprom_input_packet(
                start, actual_read_size)
            result = yield self._message_center.build(command=command_line)

            if result['error']:
                self.is_backup = False
                self.add_output_packet('backup_status', {
                    'status': 'fail'
                })
                break

            data = result['data']
            if plan_file_write_size >= max_length:
                file_result.extend(data[0:actual_read_size])
            else:
                file_result.extend(data)

            file_write_size += len(data)
            start += actual_read_size

        reserved_data = self._reserve_by_word(file_result)

        self._write_to_file(file_name, reserved_data)

        # restore odr
        command_line = helper.build_input_packet(
            'uP', properties=self.properties,
            param=packet_rate_param_index,
            value=packet_rate_result['data']['value'])
        yield self._message_center.build(command=command_line)

    def _reserve_by_word(self, data):
        start_index = 0x284
        reserved_data = bytearray()
        reserved_data.extend([00, 00])  # append 16 bit count of erases
        reserved_data.extend(data[0:start_index])
        need_reserve = data[start_index:]
        total_len = int((4095 - start_index)/2)
        for i in range(total_len):
            reserved_data.extend([need_reserve[i*2+1], need_reserve[i*2]])

        return reserved_data

    def _write_to_file(self, file_name, result):
        # save to local path, backup/{device_type}/{file_name}
        executor_path = resource.get_executor_path()
        backup_folder_path = os.path.join(
            executor_path, 'backup', 'openimu')
        file_path = os.path.join(backup_folder_path, file_name)
        if not os.path.isdir(backup_folder_path):
            os.makedirs(backup_folder_path)

        with open(file_path, 'wb') as file_stream:
            file_stream.write(result)

        backup_status = 'backup_status'
        status_complete = 'complete'
        status_fail = 'fail'

        try:
            config = get_config()
            account_name = config.AZURE_STORAGE_ACCOUNT
            container_name = config.AZURE_STORAGE_BACKUP_CONTAINER
            sas_token = self.ans_platform.get_sas_token()
            if sas_token == '':
                raise Exception('cannot get sas token')
            self.block_blob_service = BlockBlobService(account_name=account_name,
                                                       sas_token=sas_token,
                                                       protocol='http')
            self.block_blob_service.create_blob_from_path(container_name=container_name,
                                                          blob_name=file_name,
                                                          file_path=file_path)
        except Exception as ex:
            print('azure exception', ex)
            self.is_backup = False
            self.add_output_packet(backup_status, {
                'status': status_fail
            })
            return

        # save to db
        serial_num = self.device_info['sn']
        save_result = self.ans_platform.save_backup_restult(
            serial_num, file_name, 'IMU')

        if save_result.__contains__('error'):
            self.is_backup = False
            self.add_output_packet(backup_status, {
                'status': status_fail
            })
            return

        self.is_backup = False
        self.add_output_packet(backup_status, {
            'status': status_complete,
            'date': save_result['data']['lastBackupTime']
        })

    @with_device_message
    def _unlock(self):
        command_line = helper.build_read_eeprom_input_packet(0x100, 2)
        result = yield self._message_center.build(command=command_line, timeout=2)
        if result['error']:
            self._restore_fail()
            return

        command_line = helper.build_unlock_eeprom_packet(result['data'])
        unlock_result = yield self._message_center.build(command=command_line, timeout=2)

        if unlock_result['error']:
            self._restore_fail()
            return
        print('unlock -- successfull', unlock_result['data'])

    @with_device_message
    def thread_do_restore(self):
        '''
        Do Calibration Restore
        '''
        # 1.download bin from azure
        file_name = self.device_info['sn']+'.bin'
        content_data = bytearray()
        executor_path = resource.get_executor_path()
        backup_folder_path = os.path.join(
            executor_path, 'backup', 'openimu')
        file_path = os.path.join(backup_folder_path, file_name)
        file = open(file_path, 'rb')
        content_data = file.read()
        file.close()
        # 2.save odr, then set quiet
        # get current odr
        packet_rate_param_index = 4
        command_line = helper.build_input_packet(
            'gP', properties=self.properties, param=packet_rate_param_index)
        packet_rate_result = yield self._message_center.build(command=command_line)

        if packet_rate_result['error']:
            self._restore_fail()
            return

        # set quiet
        command_line = helper.build_input_packet(
            'uP', properties=self.properties, param=packet_rate_param_index, value=0)
        result = yield self._message_center.build(command=command_line)

        if result['error']:
            self._restore_fail()
            return
        # 3.do restore
        # 3.1 unlock eeprom
        command_line = helper.build_read_eeprom_input_packet(0x100, 2)
        result = yield self._message_center.build(command=command_line, timeout=2)
        if result['error']:
            self._restore_fail()
            return

        command_line = helper.build_unlock_eeprom_packet(result['data'])
        unlock_result = yield self._message_center.build(command=command_line, timeout=2)

        if unlock_result['error']:
            self._restore_fail()
            return
        print('unlock -- successfull', unlock_result['data'])
        # 3.2 write eeprom
        skip_range = [0x200, 0x284]

        sn_string = self._build_sn_string(content_data[0x200, 0x204])
        model_string = self._build_model_string(content_data[0x204:0x284])

        can_write = self._clear_calibration_area()
        if not can_write:
            self._restore_fail()
            return

        can_write = self._write_calibration_from_data(content_data, skip_range)

        if not can_write:
            self._restore_fail()
            return

        can_write = self._write_sn_and_model_string(sn_string, model_string)

        if not can_write:
            self._restore_fail()
            return

        print('write eeporm -- successfull')

        self._lock()

        # 4.write operation result to db

        # 5.restore odr
        command_line = helper.build_input_packet(
            'uP', properties=self.properties,
            param=packet_rate_param_index,
            value=packet_rate_result['data']['value'])
        yield self._message_center.build(command=command_line)

        self.is_restore = False
        self.add_output_packet('restore_status', {
            'status': 'success'
        })

    def _build_sn_string(self, data_range):
        data = []
        start = 0
        for _ in range(2):
            if start == 4:
                break
            data.extend([
                struct.unpack('B', data_range[start+1: start+2])[0],
                struct.unpack('B', data_range[start: start+1])[0]
            ])
            start += 2
        return data

    def _build_model_string(self, data_range):
        end = [0]
        data = []
        for item in data_range:
            if item == 0:
                break
            data.append(item)

        data.extend(end)
        return data

    @with_device_message
    def _clear_calibration_area(self):
        start = 0
        end = 4096
        block_size = 20
        write_offset = 0
        while write_offset < end:
            write_data = []
            plan_write_offset = write_offset + block_size * 2

            if plan_write_offset >= end:
                plan_write_offset = end
                block_size = int((plan_write_offset - write_offset)/2)

            for _ in range(plan_write_offset - write_offset):
                write_data.append(0xFF)
            command_line = helper.build_write_eeprom_input_packet(
                start, block_size, write_data)
            result = yield self._message_center.build(command=command_line, timeout=2)
            if result['error']:
                yield False

            write_offset = plan_write_offset
            start += block_size

        yield True

    @with_device_message
    def _write_sn_and_model_string(self, sn_string, model_string):
        command_line = helper.build_write_eeprom_input_packet(
            0x100, 2, sn_string)
        result = yield self._message_center.build(command=command_line, timeout=2)
        if result['error']:
            yield False

        command_line = helper.build_write_eeprom_input_packet(
            0x104, len(model_string), self._build_16bit_data_range(model_string))
        result = yield self._message_center.build(command=command_line, timeout=2)
        if result['error']:
            yield False

        yield True

    @with_device_message
    def _write_calibration_from_data(self, data, skip_range):
        end = 4096
        block_size = 20
        write_offset = 0

        while write_offset < end:
            plan_write_offset = write_offset + block_size * 2

            if plan_write_offset >= end:
                plan_write_offset = end
                block_size = int((plan_write_offset - write_offset)/2)

            # plan write range
            plan_write_range = [write_offset, plan_write_offset]
            # build a new range with skip range
            new_range = self._build_calibration_write_range(
                data, plan_write_range, skip_range)

            for write_range in new_range:
                command_line = helper.build_write_eeprom_input_packet(
                    int(write_range['start']/2),
                    int(write_range['length']/2),
                    write_range['data'])
                result = yield self._message_center.build(command=command_line, timeout=2)

                if result['error']:
                    yield False
        yield True

    def _build_calibration_write_range(self, content_data, plan_write_range, skip_range):
        # range struct {'start': start, 'data': data, 'length': length}
        new_range = []
        write_data = []
        if plan_write_range[1] >= skip_range[0] and plan_write_range[1] <= skip_range[1]:
            if plan_write_range[0] < skip_range[0]:
                write_data.extend(
                    content_data[plan_write_range[0]: skip_range[0]])
                new_range.append({'start': int(plan_write_range[0]/2),
                                  'length': int((skip_range[0]-plan_write_range[0])/2),
                                  'data': write_data})

        if plan_write_range[0] >= skip_range[0] and plan_write_range[0] <= skip_range[1]:
            if plan_write_range[1] > skip_range[1]:
                write_data.extend(
                    content_data[skip_range[1]: plan_write_range[1]])
                new_range.append({'start': int(skip_range[1]/2),
                                  'length': int((plan_write_range[1] - skip_range[1])/2),
                                  'data': write_data})

        if plan_write_range[0] < skip_range[0] and skip_range[1] < plan_write_range[1]:
            new_range.append({'start': int(plan_write_range[0]/2),
                              'length': int((skip_range[0] - plan_write_range[0])/2),
                              'data': content_data[plan_write_range[0]: skip_range[0]]})

            new_range.append({'start': int(skip_range[1]/2),
                              'length': int((plan_write_range[1] - skip_range[1])/2),
                              'data': content_data[skip_range[1]: plan_write_range[1]]})

        if plan_write_range[1] < skip_range[0] or plan_write_range[0] > skip_range[1]:
            write_data.extend(
                content_data[plan_write_range[0]: plan_write_range[1]])
            new_range.append({'start': int(plan_write_range[0]/2),
                              'length': int((plan_write_range[1] - plan_write_range[0])/2),
                              'data': write_data})

        return new_range

    def _build_16bit_data_range(self, data_range):
        data = []
        for item in data_range:
            data.extend(struct.pack('>H', item))
        return data

    def _build_reserve_data(self, data_range):
        data = []
        start = 0
        for _ in range(int(len(data_range)/2)):
            if start == len(data_range):
                break
            data.extend([
                struct.unpack('B', data_range[start+1: start+2])[0],
                struct.unpack('B', data_range[start: start+1])[0]
            ])
            start += 2
        return data

    @with_device_message
    def _lock(self):
        # lock eeprom
        command_line = helper.build_input_packet('LE')
        result = yield self._message_center.build(command=command_line)

        if result['error']:
            self._restore_fail()
            return
        print('lock eeporm -- successfull', result['data'])

        # software reset
        command_line = helper.build_input_packet('SR')
        yield self._message_center.build(command=command_line)

    def _restore_fail(self):
        self.is_restore = False
        self.add_output_packet('restore_status', {
            'status': 'fail'
        })
