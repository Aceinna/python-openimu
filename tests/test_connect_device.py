import unittest

class ConnectDeviceTest(unittest.TestCase):
    def test_connect_imu(self):
        self.assertTrue(True, 'Connect OpenIMU')

    def test_connect_openrtk(self):
        self.assertTrue(True, 'Connect OpenRTK')

    def test_connect_dum(self):
        self.assertTrue(True, 'Connect DMU')

    def test_connect_with_normal_parameters(self):
        self.assertTrue(True, 'Connect with normal parameters')

    def test_connect_with_wrong_parameters(self):
        self.assertTrue(True, 'Connect with wrong parameters')
