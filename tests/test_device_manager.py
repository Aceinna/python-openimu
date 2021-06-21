import sys
import unittest

try:
    from aceinna.devices import DeviceManager
    from aceinna.devices.base.provider_base import OpenDeviceBase
    from aceinna.devices.openimu.uart_provider import Provider as OpenIMUUartProvider
    from aceinna.devices.openrtk.uart_provider import Provider as OpenRTKUartProvider
    from aceinna.devices.rtkl.uart_provider import Provider as RTKLUartProvider
    from aceinna.devices.dmu.uart_provider import Provider as OpenDMUUartProvider
    from mocker.communicator import MockCommunicator
except:  # pylint: disable=bare-except
    sys.path.append('./src')
    sys.path.append('./tests')
    from aceinna.devices import DeviceManager
    from aceinna.devices.base.provider_base import OpenDeviceBase
    from aceinna.devices.openimu.uart_provider import Provider as OpenIMUUartProvider
    from aceinna.devices.openrtk.uart_provider import Provider as OpenRTKUartProvider
    from aceinna.devices.rtkl.uart_provider import Provider as RTKLUartProvider
    from aceinna.devices.dmu.uart_provider import Provider as OpenDMUUartProvider
    from mocker.communicator import MockCommunicator


def build_provider(device_access_type='IMU', filter_device_type=None):
    mocker_communicator_options = {'device': device_access_type}
    communicator = MockCommunicator(mocker_communicator_options)
    provider = DeviceManager.ping(
        communicator, communicator.device_access, filter_device_type)
    communicator.close()
    return provider

# pylint: disable=missing-class-docstring


class TestDeviceManager(unittest.TestCase):
    def test_ping_openimu_with_default(self):
        provider = build_provider('IMU')
        self.assertTrue(isinstance(provider, OpenIMUUartProvider),
                        'OpenIMU UART Provider')

    def test_ping_openimu_with_specified_device_type(self):
        provider = build_provider('IMU', 'IMU')
        self.assertTrue(isinstance(provider, OpenIMUUartProvider),
                        'OpenIMU UART Provider')

    def test_ping_openrtk_with_default(self):
        provider = build_provider('RTK')
        self.assertTrue(isinstance(provider, OpenRTKUartProvider),
                        'OpenRTK UART Provider')

    def test_ping_openrtk_with_specified_device_type(self):
        provider = build_provider('RTK', 'RTK')
        self.assertTrue(isinstance(provider, OpenRTKUartProvider),
                        'OpenRTK UART Provider')

    def test_ping_dmu_with_default(self):
        provider = build_provider('DMU')
        self.assertTrue(isinstance(provider, OpenDMUUartProvider),
                        'DMU UART Provider')

    def test_ping_dmu_with_specified_device_type(self):
        provider = build_provider('DMU', 'DMU')
        self.assertTrue(isinstance(provider, OpenDMUUartProvider),
                        'DMU UART Provider')

    def test_ping_rtkl_with_specified_device_type(self):
        provider = build_provider('RTK', 'RTKL')
        self.assertTrue(isinstance(provider, RTKLUartProvider),
                        'RTKL UART Provider')

    def test_ping_device_with_unmatched_device_type(self):
        provider = build_provider('IMU', 'RTK')
        self.assertTrue(provider is None, 'OpenIMU UART Provider')

    def test_ping_same_device_with_samed_provider_instance(self):
        communicator = MockCommunicator({'device': 'IMU'})
        provider1 = DeviceManager.ping(
            communicator, communicator.device_access, None)
        provider2 = DeviceManager.ping(
            communicator, communicator.device_access, None)
        communicator.close()
        self.assertEqual(provider1, provider2)

    # TODO: missing commuinicator with LAN


if __name__ == '__main__':
    unittest.main()
