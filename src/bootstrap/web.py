import json
import tornado.websocket
import tornado.ioloop
import tornado.httpserver
import tornado.web
from .base import BootstrapBase
from ..framework.communicator import CommunicatorFactory
from ..framework.context import app_context


class WSHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        self.get_device().append_client(self)
        print('open client count:', len(self.get_device().clients))
        #self.callback = tornado.ioloop.PeriodicCallback(self.send_data, callback_rate)
        self.response_server_info()
        pass

    def on_message(self, message):
        device = self.get_device()
        client_msg = json.loads(message)
        print('request message:', client_msg)
        method = client_msg['method'] if 'method' in client_msg else None
        parameters = client_msg['params'] if 'params' in client_msg else None
        if method:
            try:
                getattr(device, method, None)(parameters)
            except Exception as e:
                print('websocket on message error', e)
        else:
            self.response_unkonwn_method()

    def on_close(self):
        self.get_device().remove_client(self)
        print('close client count:', len(self.get_device().clients))
        pass

    def check_origin(self, origin):
        return True

    def get_device(self):
        return app_context.get_app().get_device()

    def response_message(self, method, data):
        print('response message:', method)
        self.write_message(
            json.dumps(
                {
                    'method': method,
                    'result': data
                }
            ))

    def response_unkonwn_method(self):
        self.write_message(
            json.dumps({
                'method': 'unknown',
                'result': {
                    'packetType': 'error',
                    'data': {
                        'message': 'unknown method'
                    }
                }
            })
        )

    def response_server_info(self):
        self.write_message(
            json.dumps({
                'method': 'stream',
                'result': {
                    'packetType': 'serverInfo',
                    'data': {
                        'version': '2.0.0',
                        'serverUpdateRate': self.get_device().server_update_rate
                    }
                }
            })
        )
        pass


class Webserver:
    def __init__(self, options):
        self.communication = 'uart'
        self.options = options
        self.device_provider = None
        pass

    def listen(self):
        print('start web listen')
        # start to detect device
        self.detect_device(self.device_found_handler)

    def get_device(self):
        if self.device_provider is not None:
            return self.device_provider
        raise Exception('device is not connected')

    def device_found_handler(self, device_provider):
        print('device found')
        # load device provider
        self.device_provider = device_provider
        self.device_provider.setup()
        #self.deviceProvider.on('stream', onReceiveStreamData)
        #self.deviceProvider.on('', onReceiveStreamData)

        # start websocket server
        application = tornado.web.Application([(r'/', WSHandler)])
        self.http_server = tornado.httpserver.HTTPServer(application)
        self.http_server.listen(self.options.p)

        tornado.ioloop.IOLoop.instance().start()

    def detect_device(self, callback):
        print('start find device')
        communicator = CommunicatorFactory.create(
            self.communication, self.options)
        communicator.find_device(callback)

    def stop(self):
        if self.http_server is not None:
            self.http_server.stop()
