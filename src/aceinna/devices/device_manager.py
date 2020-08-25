import sys
import os
import time
import struct
from .openimu.uart_provider import Provider as OpenIMUProvider
from .openrtk.uart_provider import Provider as OpenRTKProvider
from .dmu.uart_provider import Provider as DMUProvider
from .dmu import dmu_helper
from ..framework.utils import (helper, resource)
from ..framework.context import APP_CONTEXT

# for DMU 'GP'
ID = [0x49, 0x44]
VR = [0x56, 0x52]


class DeviceManager:
    '''
    Manage devices
    '''
    # device_list = []

    # @staticmethod
    # def ping(communicator, *args):
    #     '''
    #     Find the matched device
    #     '''
    #     filter_device_type = args[0]

    #     if communicator.type == 'uart':
    #         if len(DeviceManager.device_list) == 0:
    #             DeviceManager.device_list.append(OpenIMUProvider(communicator))
    #             DeviceManager.device_list.append(OpenRTKProvider(communicator))
    #             DeviceManager.device_list.append(DMUProvider(communicator))

    #     for device in DeviceManager.device_list:
    #         if filter_device_type and device.type != filter_device_type:
    #             continue

    #         can_ping = device.ping()
    #         if can_ping:
    #             return device
    #     return None

    can_ping = False
    device = None

    @staticmethod
    def reset_ping():
        DeviceManager.can_ping = False

    @staticmethod
    def imu_ping(serial, command, read_length=500, retry=20):
        if not DeviceManager.can_ping:
            command_line = helper.build_input_packet(command)
            serial.write(command_line)
            time.sleep(0.1)

            data_buffer = helper.read_untils_have_data_through_serial_port(
                serial, command, read_length, retry)
            parsed = bytearray(data_buffer) if data_buffer and len(
                data_buffer) > 0 else None

            format_string = None
            if parsed is not None:
                try:
                    if sys.version_info < (3, 0):
                        format_string = str(struct.pack(
                            '{0}B'.format(len(parsed)), *parsed))
                    else:
                        format_string = str(struct.pack(
                            '{0}B'.format(len(parsed)), *parsed), 'utf-8')
                except UnicodeDecodeError:
                    return ''

            if format_string is not None:
                return format_string
        return ''

    @staticmethod
    def dmu_ping(serial, command, message_bytes=[]):
        if not DeviceManager.can_ping:
            data_buffer = None
            if command == 'PK':
                command_line = dmu_helper.build_packet('PK')
                serial.write(command_line)
                time.sleep(0.1)
                data_buffer = helper.read_untils_have_data_through_serial_port(
                    serial, 'PK')
                if data_buffer == []:
                    return True

            elif command == 'GP' and message_bytes == ID:
                command_line = dmu_helper.build_packet('GP', ID)
                serial.write(command_line)
                time.sleep(0.1)
                data_buffer = helper.read_untils_have_data_through_serial_port(
                    serial, 'ID')

                if data_buffer is None:
                    return False

                serial_num = int.from_bytes(struct.pack(
                    '4B', *data_buffer[0:4]), byteorder='big')

                mode_string_len = len(data_buffer[4:])
                model_string = struct.pack('{0}B'.format(
                    mode_string_len), *data_buffer[4:]).decode()

                split_text = model_string.split(' ')
                if model_string.find('OpenIMU') > -1 or \
                        model_string.find('OpenRTK') > -1:
                    return False

                device_info = {
                    'name': split_text[0],
                    'pn': split_text[1],
                    # 'firmware_version': split_text[2],
                    'sn': serial_num
                }
                return device_info

            elif command == 'GP' and message_bytes == VR:
                command_line = dmu_helper.build_packet('GP', VR)
                serial.write(command_line)
                time.sleep(0.1)
                data_buffer = helper.read_untils_have_data_through_serial_port(
                    serial, 'VR')

                if data_buffer is None:
                    return False

                version_string = '{0}.{1}.{2}.{3}.{4}'.format(*data_buffer)

                app_info = {
                    'app_name': 'DMU',
                    'version': version_string
                }
                return app_info

            return data_buffer
        return False

    @staticmethod
    def ping_with_port(communicator, *args):

        if communicator.type == 'uart':
            port = args[0]
            serial = args[1]
            filter_device_type = args[2]

            if filter_device_type == None or filter_device_type == 'IMU' or filter_device_type == 'RTK':
                APP_CONTEXT.get_logger().logger.debug('Checking if is OpenRTK/OpenIMU device...')

                device_info_text = DeviceManager.imu_ping(serial, 'pG')
                app_info_text = DeviceManager.imu_ping(serial, 'gV')

                # TODO: Prevent action. Get app info again,
                # if cannot retrieve any info at the first time of ping. Should find the root cause.
                if app_info_text == '':
                    app_info_text = DeviceManager.imu_ping(serial, 'gV')

                APP_CONTEXT.get_logger().logger.debug(
                    'Device: {0}'.format(device_info_text))
                APP_CONTEXT.get_logger().logger.debug(
                    'Firmware: {0}'.format(app_info_text))

                if not DeviceManager.can_ping:
                    if device_info_text.find('OpenRTK') > -1:
                        DeviceManager.can_ping = True
                        split_device_info = device_info_text.split(' ')
                        print('# Connected OpenRTK [{0}] #'.format(port))
                        print('Device: {0} {1} {2} {3}'.format(
                            split_device_info[0], split_device_info[2], split_device_info[3], split_device_info[4]))
                        print('APP version:', app_info_text)
                        APP_CONTEXT.get_logger().logger.info(
                            'Connected {0}, {1}'.format(device_info_text, app_info_text))

                        if DeviceManager.device == None or DeviceManager.device.type != 'RTK':
                            DeviceManager.device = OpenRTKProvider(
                                communicator)

                        DeviceManager.device.build_device_info(
                            device_info_text, app_info_text)
                        return DeviceManager.device

                    elif device_info_text.find('OpenIMU') > -1 and \
                            device_info_text.find('OpenRTK') == -1:
                        DeviceManager.can_ping = True
                        print('# Connected OpenIMU #')
                        print('Device:', device_info_text)
                        print('Firmware:', app_info_text)
                        APP_CONTEXT.get_logger().logger.info(
                            'Connected {0}, {1}'.format(device_info_text, app_info_text))

                        if DeviceManager.device == None or DeviceManager.device.type != 'IMU':
                            DeviceManager.device = OpenIMUProvider(
                                communicator)

                        DeviceManager.device.build_device_info(
                            device_info_text, app_info_text)
                        return DeviceManager.device

            if filter_device_type == None or filter_device_type == 'DMU':
                APP_CONTEXT.get_logger().logger.debug('Checking if is DMU device...')
                ret = DeviceManager.dmu_ping(serial, 'PK')
                if ret:
                    # consider as dmu
                    device_info = DeviceManager.dmu_ping(serial, 'GP', ID)
                    if device_info:
                        app_info = DeviceManager.dmu_ping(serial, 'GP', VR)
                        if app_info:
                            DeviceManager.can_ping = True
                            #print('The device work as DMU')
                            print('# Connected DMU #')
                            print('Device SN: {0}'.format(device_info['sn']))
                            print('Device Model: {0} {1}'.format(
                                device_info['name'], device_info['pn']))
                            print('Firmware Version:', app_info['version'])

                            if DeviceManager.device == None or DeviceManager.device.type != 'DMU':
                                DeviceManager.device = DMUProvider(
                                    communicator)

                            DeviceManager.device.build_device_info(
                                device_info, app_info)
                            return DeviceManager.device
        return None
