import tornado.websocket
import tornado.ioloop
import tornado.httpserver
import tornado.web
from .base import BootstrapBase
from ..framework.communicator import CommunicatorFactory
from ..framework.context import active_app


class WSHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        self.get_device().append_client(self)

        #self.callback = tornado.ioloop.PeriodicCallback(self.send_data, callback_rate)
        pass

    def on_message(self, message):
        device = self.get_device()
        client_msg = json.loads(message)
        params = client_msg['params']
        getattr(device, client_msg['method'], None)(params)
        pass

    def on_close(self):
        self.get_device().remove_client(self)
        pass

    def check_origin(self, origin):
        return True

    def get_device(self):
        return active_app.get_device()

    def response_message(self, method, data):
        self.write_message(
            json.dumps(
                {
                    'method': method,
                    'result': data
                }
            ))


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
