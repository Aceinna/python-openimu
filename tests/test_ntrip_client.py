import sys
import os
import json
#import unittest

try:
    from aceinna.devices.widgets import NTRIPClient
    # from aceinna.devices.openrtk.uart_provider import Provider as OpenRTKUartProvider
    # from aceinna.devices.openrtk.lan_provider import Provider as OpenRTKLANProvider
    # from aceinna.devices.rtkl.uart_provider import Provider as OpenRTKLUartProvider
except:
    sys.path.append('./src')
    from aceinna.devices.widgets import NTRIPClient

local_config_file_path = os.path.join(os.getcwd(),'setting','RTK330L','RTK_INS','RTK330L.json')
properties=None

if os.path.isfile(local_config_file_path):
    with open(local_config_file_path) as json_data:
        properties = json.load(json_data)

def handle_data_parsed(data):
    pass

ntrip_client = NTRIPClient(properties)
ntrip_client.on('parsed', handle_data_parsed)
ntrip_client.run()