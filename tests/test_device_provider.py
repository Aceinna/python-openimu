import sys
import time
import unittest

try:
    from aceinna.devices import DeviceManager
    from mocker.communicator import MockCommunicator
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.devices import DeviceManager
    from mocker.communicator import MockCommunicator


def build_provider(device_access_type='IMU', filter_device_type=None):
    mocker_communicator_options = {'device': device_access_type}
    communicator = MockCommunicator(mocker_communicator_options)
    provider = DeviceManager.ping(
        communicator, communicator.device_access, filter_device_type)
    provider.setup(None)  # no options
    time.sleep(0.5)
    return provider


def close_provider(provider):
    provider.communicator.close()
    time.sleep(.5)
    provider.close()


@unittest.skip
class TestOpenIMUProvider(unittest.TestCase):
    def test_get_params(self):
        provider = build_provider()
        all_params = provider.get_params()
        close_provider(provider)

        method_result = all_params['packetType']
        expect_result = 'inputParams'
        self.assertEqual(method_result, expect_result)

    def test_get_param(self):
        provider = build_provider()
        get_param_id = 1
        single_param = provider.get_param({'paramId': get_param_id})
        close_provider(provider)

        data_in_result = single_param['data']
        param_id_in_data = data_in_result['paramId']

        method_result = [single_param['packetType'], param_id_in_data]
        expect_result = ['inputParam', get_param_id]
        self.assertEqual(method_result, expect_result)

    def test_get_invalid_param(self):
        provider = build_provider()
        get_param_id = 100
        single_param = provider.get_param({'paramId': get_param_id})
        close_provider(provider)

        method_result = single_param['packetType']
        expect_result = 'error'
        self.assertEqual(method_result, expect_result)

    def test_set_params(self):
        provider = build_provider()
        update_params = [
            {'paramId': 1, 'value': 1},
            {'paramId': 2, 'value': 2},
        ]
        set_params_result = provider.set_params(update_params)
        close_provider(provider)

        method_result = set_params_result['packetType']
        expect_result = 'success'
        self.assertEqual(method_result, expect_result)

    def test_set_param(self):
        provider = build_provider()
        set_param_result = provider.set_param({'paramId': 1, 'value': 1})
        close_provider(provider)

        data_in_result = set_param_result['data']['error']

        method_result = [set_param_result['packetType'], data_in_result]
        expect_result = ['success', 0]
        self.assertEqual(method_result, expect_result)

    def test_set_invalid_param(self):
        provider = build_provider()
        set_param_result = provider.set_param({'paramId': 100, 'value': -1})
        close_provider(provider)

        method_result = set_param_result['packetType']
        expect_result = 'error'
        self.assertEqual(method_result, expect_result)

    def test_reset_params(self):
        provider = build_provider()
        reset_params_result = provider.reset_params()
        close_provider(provider)

        method_result = reset_params_result['packetType']
        expect_result = 'success'
        self.assertEqual(method_result, expect_result)

    def test_save_config(self):
        provider = build_provider()
        save_config_result = provider.save_config()

        close_provider(provider)

        method_result = save_config_result['packetType']
        expect_result = 'success'
        self.assertEqual(method_result, expect_result)


@unittest.skip
class TestOpenRTKProvider(unittest.TestCase):
    def test_get_params(self):
        provider = build_provider('RTK')
        all_params = provider.get_params()
        close_provider(provider)

        method_result = all_params['packetType']
        expect_result = 'inputParams'
        self.assertEqual(method_result, expect_result)

    def test_get_param(self):
        provider = build_provider('RTK')
        get_param_id = 1
        single_param = provider.get_param({'paramId': get_param_id})
        close_provider(provider)

        data_in_result = single_param['data']
        param_id_in_data = data_in_result['paramId']

        method_result = [single_param['packetType'], param_id_in_data]
        expect_result = ['inputParam', get_param_id]
        self.assertEqual(method_result, expect_result)

    def test_get_invalid_param(self):
        provider = build_provider('RTK')
        get_param_id = 100
        single_param = provider.get_param({'paramId': get_param_id})
        close_provider(provider)

        method_result = single_param['packetType']
        expect_result = 'error'
        self.assertEqual(method_result, expect_result)

    def test_set_params(self):
        provider = build_provider('RTK')
        update_params = [
            {'paramId': 1, 'value': 1},
            {'paramId': 2, 'value': 2},
        ]
        set_params_result = provider.set_params(update_params)
        close_provider(provider)

        method_result = set_params_result['packetType']
        expect_result = 'success'
        self.assertEqual(method_result, expect_result)

    def test_set_param(self):
        provider = build_provider('RTK')
        set_param_result = provider.set_param({'paramId': 1, 'value': 1})
        close_provider(provider)

        data_in_result = set_param_result['data']['error']

        method_result = [set_param_result['packetType'], data_in_result]
        expect_result = ['success', 0]
        self.assertEqual(method_result, expect_result)

    def test_set_invalid_param(self):
        provider = build_provider('RTK')
        set_param_result = provider.set_param({'paramId': 100, 'value': -1})
        close_provider(provider)

        method_result = set_param_result['packetType']
        expect_result = 'error'
        self.assertEqual(method_result, expect_result)

    def test_reset_params(self):
        provider = build_provider('RTK')
        reset_params_result = provider.reset_params()
        close_provider(provider)

        method_result = reset_params_result['packetType']
        expect_result = 'success'
        self.assertEqual(method_result, expect_result)

    def test_save_config(self):
        provider = build_provider('RTK')
        save_config_result = provider.save_config()
        close_provider(provider)

        method_result = save_config_result['packetType']
        expect_result = 'success'
        self.assertEqual(method_result, expect_result)


@unittest.skip
class TestOpenDMUProvider(unittest.TestCase):
    def test_get_conf(self):
        provider = build_provider('DMU')
        conf = provider.get_conf()
        close_provider(provider)

        method_result = conf['packetType']
        expect_result = 'conf'
        self.assertEqual(method_result, expect_result)

    def test_get_params(self):
        provider = build_provider('DMU')
        all_params = provider.get_params()
        close_provider(provider)

        method_result = all_params['packetType']
        expect_result = 'inputParams'
        self.assertEqual(method_result, expect_result)

    def test_get_param(self):
        provider = build_provider('DMU')
        get_param_id = 1
        single_param = provider.get_param({'paramId': get_param_id})
        close_provider(provider)

        data_in_result = single_param['data']
        param_id_in_data = data_in_result['paramId']

        method_result = [single_param['packetType'], param_id_in_data]
        expect_result = ['inputParam', get_param_id]
        self.assertEqual(method_result, expect_result)

    def test_get_invalid_param(self):
        provider = build_provider('DMU')
        get_param_id = 0
        single_param = provider.get_param({'paramId': get_param_id})
        close_provider(provider)

        method_result = single_param['packetType']
        expect_result = 'error'
        self.assertEqual(method_result, expect_result)

    def test_set_param(self):
        provider = build_provider('DMU')
        set_param_result = provider.set_param({'paramId': 1, 'value': 2})
        close_provider(provider)

        data_in_result = set_param_result['data']['error']

        method_result = [set_param_result['packetType'], data_in_result]
        expect_result = ['success', 0]
        self.assertEqual(method_result, expect_result)

    def test_set_invalid_param(self):
        provider = build_provider('DMU')
        set_param_result = provider.set_param({'paramId': 0, 'value': 2})
        close_provider(provider)

        method_result = set_param_result['packetType']
        expect_result = 'error'
        self.assertEqual(method_result, expect_result)

    def test_save_config(self):
        provider = build_provider('DMU')

        #get_param_result = provider.get_param({'paramId':1})
        #set_param_result = provider.set_param({'paramId':1, 'value':1})
        save_config_result = provider.save_config()
        # provider.restart()
        #get_param_result = provider.get_param({'paramId':1})

        close_provider(provider)

        method_result = save_config_result['packetType']
        expect_result = 'success'
        self.assertEqual(method_result, expect_result)


class TestProviderSwitch(unittest.TestCase):
    def test_reconnect_with_same_device(self):
        pass

    def test_reconnect_with_different_device(self):
        pass


if __name__ == '__main__':
    unittest.main()
