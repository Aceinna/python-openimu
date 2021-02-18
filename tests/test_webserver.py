import sys
import unittest
import threading
import time
import asyncio
import tornado.ioloop
from websocket import create_connection

try:
    from aceinna.core.tunnel_web import WebServer
    from aceinna.models import WebserverArgs
except:  # pylint: disable=bare-except
    sys.path.append('./src')
    from aceinna.core.tunnel_web import WebServer
    from aceinna.models import WebserverArgs


WS_ADDRESS = "ws://127.0.0.1:8000"


# pylint: disable=missing-class-docstring
# @unittest.skip
class TestWebserver(unittest.TestCase):
    _tunnel=None

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_websocket_server_establish(self):
        # start web server
        threading.Thread(target=self._prepare_tunnel).start()
        time.sleep(1)
        # send a ping request
        websocket_client = create_connection(WS_ADDRESS)
        # wait the response
        response = websocket_client.recv()
        websocket_client.close()

        self._tunnel.stop()
        # validate the result
        self.assertTrue(response is not None, 'WebSocket server established')

    def _prepare_tunnel(self):
        asyncio.set_event_loop(asyncio.new_event_loop())

        event_loop = tornado.ioloop.IOLoop.current()

        self._tunnel = WebServer(WebserverArgs(), event_loop)
        self._tunnel.setup()

if __name__ == '__main__':
    unittest.main()
