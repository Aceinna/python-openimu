import sys
import unittest
import threading
import time
import asyncio
from websocket import create_connection

try:
    from aceinna.bootstrap.web import (
        WebserverArgs,
        Webserver
    )
except:  # pylint: disable=bare-except
    sys.path.append('./src')
    from aceinna.bootstrap.web import (
        WebserverArgs,
        Webserver
    )


WS_ADDRESS = "ws://127.0.0.1:8000"


# pylint: disable=missing-class-docstring
@unittest.skip
class TestWebserver(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_websocket_server_establish(self):
        # start web server
        webserver = Webserver()

        def do_listen():
            asyncio.set_event_loop(asyncio.new_event_loop())
            webserver.listen()

        thread = threading.Thread(target=do_listen)
        thread.start()
        time.sleep(1)
        # send a ping request
        websocket_client = create_connection(WS_ADDRESS)
        # wait the response
        response = websocket_client.recv()
        websocket_client.close()

        webserver.stop()
        # validate the result
        self.assertTrue(response is not None, 'WebSocket server established')


if __name__ == '__main__':
    unittest.main()
