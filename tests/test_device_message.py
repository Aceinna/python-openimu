import sys
import unittest
try:
    from aceinna.framework.utils import helper
    from aceinna.devices.dmu import dmu_helper
except:  # pylint: disable=bare-except
    sys.path.append('./src')
    from aceinna.framework.utils import helper
    from aceinna.devices.dmu import dmu_helper


class TestOpenPacketMessage(unittest.TestCase):
    '''
    Test Open Packet Message
    1. build_packet
    2. build_input_packet
    '''

    def test_build_packet(self):
        # gA
        msg = helper.build_packet('gA')
        expect_msg = [85, 85, 103, 65, 0, 49, 10]
        self.assertEqual(msg, expect_msg, 'gA Message is matched')

        # pG
        msg = helper.build_packet('pG')
        expect_msg = [85, 85, 112, 71, 0, 93, 95]
        self.assertEqual(msg, expect_msg, 'pG Message is matched')

    def test_build_packet_with_params(self):
        # uP
        param_index = [2, 0, 0, 0]
        int64_value = [10, 0, 0, 0, 0, 0, 0, 0]
        msg = helper.build_packet('uP', param_index + int64_value)
        expect_msg = [85, 85, 117, 80, 12] + param_index+int64_value + [127, 28]
        self.assertEqual(msg, expect_msg, 'uP Message is matched')

        # gP
        param_index = [2, 0, 0, 0]
        msg = helper.build_packet('gP', param_index)
        expect_msg = [85, 85, 103, 80, 4] + param_index + [166, 214]
        self.assertEqual(msg, expect_msg, 'gP Message is matched')


class TestDMUPacketMessage(unittest.TestCase):
    '''
    Test DMU Packet Message
    1. build_packet
    '''

    def test_build_packet(self):
        # RF
        read_fields = [0, 1] + [0, 2]
        msg = dmu_helper.build_packet('RF', read_fields)
        len_of_payload = len(read_fields)
        number_of_fields = int(len_of_payload/2)
        expect_msg = [85, 85, 82, 70] \
            + [len_of_payload+1] + [number_of_fields] \
            + read_fields+[201, 194]
        self.assertEqual(msg, expect_msg, 'RF Message is matched')

        # WF
        write_fields = [0, 1, 0, 1] + [0, 2, 0, 2]
        msg = dmu_helper.build_packet('WF', write_fields)
        len_of_payload = len(write_fields)
        number_of_fields = int(len(write_fields)/4)
        expect_msg = [85, 85, 87, 70] \
            + [len_of_payload+1] + [number_of_fields]\
            + write_fields + [65, 107]
        self.assertEqual(msg, expect_msg, 'WF Message is matched')

        # Other
        payload = [0, 1, 0, 2]
        msg = dmu_helper.build_packet('TS', payload)
        expect_msg = [85, 85, 84, 83] + [len(payload)]+payload + [19, 35]
        self.assertEqual(msg, expect_msg, 'TS Message is matched')


if __name__ == '__main__':
    unittest.main()
