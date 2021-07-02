import sys
import os
import json
import unittest
import threading
import time

try:
    from aceinna.devices.widgets import NTRIPClient
except:
    sys.path.append('./src')
    from aceinna.devices.widgets import NTRIPClient

local_config_file_path = os.path.join(
    os.getcwd(), 'setting', 'RTK330L', 'RTK_INS', 'RTK330L.json')
properties = None

if os.path.isfile(local_config_file_path):
    with open(local_config_file_path) as json_data:
        properties = json.load(json_data)


def handle_data_parsed(data):
    pass


class TestNtripClient(unittest.TestCase):
    _ntrip_client = None

    def _start_ntrip_client(self):
        self._ntrip_client = NTRIPClient(properties)
        self._ntrip_client.on('parsed', handle_data_parsed)
        self._ntrip_client.run()

    def test_connect_with_ntrip_server(self):
        threading.Thread(target=self._start_ntrip_client).start()
        time.sleep(3)
        is_connected = self._ntrip_client.is_connected
        self._ntrip_client.close()

        self.assertEqual(self._ntrip_client.is_connected,
                          0, 'Ntrip Server connected')


if __name__ == '__main__':
    unittest.main()
