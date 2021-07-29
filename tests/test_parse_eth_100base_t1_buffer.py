import sys

try:
    from aceinna.framework.utils import helper
except:
    sys.path.append('./src')
    from aceinna.framework.utils import helper

bin_file = '/Users/songyiwei/projects/python-openimu/data/another/user_2021_07_26_10_30_41.bin'

with open(bin_file, 'rb') as buf_r:
    tmp_data = buf_r.read(1000)

    if tmp_data:
        response = helper._parse_eth_100base_t1_buffer(tmp_data)
        print(response)