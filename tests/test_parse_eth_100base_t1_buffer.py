import sys
import time
try:
    from aceinna.framework.utils import helper
except:
    sys.path.append('./src')
    from aceinna.framework.utils import helper
    from aceinna.devices.parsers.ins401_message_parser import EthernetMessageParser


def parse_with_helper():
    bin_file = '/Users/songyiwei/projects/python-openimu/data/another/user_2021_07_26_10_30_41.bin'

    with open(bin_file, 'rb') as buf_r:
        tmp_data = buf_r.read(1000)

        if tmp_data:
            response = helper._parse_eth_100base_t1_buffer(tmp_data)
            print(response)


def parse_with_parser():

    def continuous_message_handler(packet_type, data, event_time, raw):
        print(packet_type, event_time)

    parser = EthernetMessageParser(None)
    #parser.on('continuous_message', continuous_message_handler)

    bin_file = '/Users/songyiwei/projects/python-openimu/data/20210729/user_2021_07_29_15_50_53.bin'
    #bin_file = '/Users/songyiwei/projects/python-openimu/data/another/user_2021_07_26_10_30_41.bin'

    print(time.time())
    read_size = 1024*1024
    count = 0
    with open(bin_file, 'rb') as buf_r:
        tmp_data = buf_r.read(read_size)

        if len(tmp_data) > 0:
            parser.analyse(tmp_data)
            # tmp_data = buf_r.read(read_size)
        # if tmp_data:
    print(time.time())


if __name__ == '__main__':
    parse_with_parser()
