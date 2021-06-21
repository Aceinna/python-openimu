import sys
import unittest

try:
    from aceinna.devices.openimu.uart_provider import Provider as OpenIMUUartProvider
    # from aceinna.devices.openrtk.uart_provider import Provider as OpenRTKUartProvider
    # from aceinna.devices.openrtk.lan_provider import Provider as OpenRTKLANProvider
    # from aceinna.devices.rtkl.uart_provider import Provider as OpenRTKLUartProvider
except:
    sys.path.append('./src')
    from aceinna.devices.openimu.uart_provider import Provider as OpenIMUUartProvider
    # from aceinna.devices.openrtk.uart_provider import Provider as OpenRTKUartProvider
    # from aceinna.devices.openrtk.lan_provider import Provider as OpenRTKLANProvider
    # from aceinna.devices.rtkl.uart_provider import Provider as OpenRTKLUartProvider


PRODUCT_NORMAL = 'OpenIMU330BI'
PRODUCT_OPTIONAL = '{0} EVB'.format(PRODUCT_NORMAL)
PART_NUM = '5020-1800-01'
SERIAL_NUM = 'SN:2074001166'
APP_NAME = 'IMU'
APP_VERSION = '02.01.51'

DEVICE_NORMAL = '{0} {1} {2} {3}'.format(
    PRODUCT_NORMAL, PART_NUM, APP_VERSION, SERIAL_NUM)
DEVICE_OPTIONAL = '{0} {1} {2} {3}'.format(
    PRODUCT_OPTIONAL, PART_NUM, APP_VERSION, SERIAL_NUM)

VERSION_NORMAL = '{0} {1} {2}'.format(PRODUCT_NORMAL, APP_NAME, APP_VERSION)
VERSION_SHORT = '{0} {1}'.format(APP_NAME, APP_VERSION)

DEVICE_BOOTLOADER = 'Bootloader Unit SN:xxxxxx'
VERSION_BOOTLOADER = ''

INVALID_DEVICE = 'xx xx'


class TestDevicePing(unittest.TestCase):
    def test_ping_openimu_normal(self):
        provider = OpenIMUUartProvider(None)
        provider.bind_device_info(None, DEVICE_NORMAL, VERSION_NORMAL)

        self.assertEqual(
            [provider.device_info['name'], provider.device_info['product_name'],
                provider.app_info['app_name'], provider.app_info['product_name']],
            [PRODUCT_NORMAL, PRODUCT_NORMAL, APP_NAME, PRODUCT_NORMAL]
        )

    def test_ping_openimu_device_name_optional(self):
        provider = OpenIMUUartProvider(None)
        provider.bind_device_info(None, DEVICE_OPTIONAL, VERSION_NORMAL)

        self.assertEqual(
            [provider.device_info['name'], provider.device_info['product_name'],
                provider.app_info['app_name'], provider.app_info['product_name']],
            [PRODUCT_OPTIONAL, PRODUCT_NORMAL, APP_NAME, PRODUCT_NORMAL]
        )

    def test_ping_openimu_normal_short_app_version(self):
        provider = OpenIMUUartProvider(None)
        provider.bind_device_info(None, PRODUCT_NORMAL, VERSION_SHORT)

        self.assertEqual(
            [provider.device_info['name'], provider.device_info['product_name'],
                provider.app_info['app_name'], provider.app_info['product_name']],
            [PRODUCT_NORMAL, PRODUCT_NORMAL, APP_NAME, '']
        )

    def test_ping_openimu_device_name_optional_short_app_version(self):
        provider = OpenIMUUartProvider(None)
        provider.bind_device_info(None, DEVICE_OPTIONAL, VERSION_SHORT)

        self.assertEqual(
            [provider.device_info['name'], provider.device_info['product_name'],
                provider.app_info['app_name'], provider.app_info['product_name']],
            [PRODUCT_OPTIONAL, PRODUCT_NORMAL, APP_NAME, '']
        )

    def test_ping_openimu_bootloader(self):
        provider = OpenIMUUartProvider(None)
        provider.bind_device_info(None, DEVICE_BOOTLOADER, VERSION_BOOTLOADER)

        self.assertEqual(
            [provider.device_info['name'], provider.device_info['product_name'],
                provider.app_info['app_name'], provider.app_info['product_name']],
            ['Bootloader', 'Bootloader', 'IMU', '']
        )

    def test_ping_openimu_invalid_device(self):
        provider = OpenIMUUartProvider(None)
        provider.bind_device_info(None, INVALID_DEVICE, '')

        self.assertEqual(
            [provider.device_info['name'], provider.device_info['product_name'],
                provider.app_info['app_name'], provider.app_info['product_name']],
            ['xx', 'xx', 'IMU', '']
        )


if __name__ == '__main__':
    unittest.main()
