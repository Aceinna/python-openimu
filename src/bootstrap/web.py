import json
import tornado.websocket
import tornado.ioloop
import tornado.httpserver
import tornado.web
from .base import BootstrapBase
from ..framework.communicator import CommunicatorFactory
from ..framework.context import app_context


class WSHandler(tornado.websocket.WebSocketHandler):
    is_streaming = False
    latest_packet_collection = []

    def initialize(self, server):
        server.ws_handler = self

    def open(self):
        self.get_device().append_client(self)
        print('open client count:', len(self.get_device().clients))
        self.callback = tornado.ioloop.PeriodicCallback(
            self.response_output_packet, self.get_device().server_update_rate)
        self.callback.start()

        self.response_server_info()  # response server info at first time connected
        pass

    def on_message(self, message):
        device = self.get_device()
        client_msg = json.loads(message)
        method = client_msg['method'] if 'method' in client_msg else None
        parameters = client_msg['params'] if 'params' in client_msg else None

        if method:
            try:
                result = getattr(device, method, None)(parameters)
                self.response_message(method, result)
            except Exception as e:
                print('websocket on message error', e)
        else:
            self.response_unkonwn_method()

    def on_close(self):
        try:
            self.callback.stop()
        except Exception as e:
            pass

        self.get_device().remove_client(self)
        print('close client count:', len(self.get_device().clients))
        pass

    def check_origin(self, origin):
        return True

    def get_device(self):
        return app_context.get_app().get_device()

    def on_receive_output_packet(self, method, packet_type, data):
        data_updated = False
        for item in self.latest_packet_collection:
            if item['packet_type'] == packet_type:
                item['data'] = data
                data_updated = True
                break

        if data_updated == False:
            self.latest_packet_collection.append({
                'packet_type': packet_type,
                'data': data
            })

    def on_receive_notify(self, method):
        if method == 'startStream':
            self.is_streaming = True
            pass

        if method == 'stopStream':
            self.is_streaming = False
            pass

    def response_message(self, method, data):
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

    def response_output_packet(self):
        for latest_packet in self.latest_packet_collection:
            if latest_packet['packet_type'] == 'ping' or self.is_streaming:
                self.write_message(
                    json.dumps({
                        'method': 'stream',
                        'result': {
                            'packetType': latest_packet['packet_type'],
                            'data': latest_packet['data']
                        }
                    })
                )
        self.latest_packet_collection.clear()


class Webserver:
    def __init__(self, options):
        self.communication = 'uart'
        self.options = options
        self.device_provider = None
        self.communicator = None
        self.ws_handler = None
        pass

    def listen(self):
        print('start web listen')
        self.detect_device(self.device_discover_handler)

    def get_device(self):
        if self.device_provider is not None:
            return self.device_provider
        raise Exception('device is not connected')

    def device_discover_handler(self, device_provider):
        print('device found')
        # load device provider
        self.load_device_provider(device_provider)
        # start websocket server
        self.start_websocket_server()

    def device_rediscover_handler(self, device_provider):
        self.load_device_provider(device_provider)
        # TODO: compare if it is this last connected device
        if self.ws_handler:
            self.ws_handler.on_receive_output_packet(
                'stream', 'ping', {'status': 3})

    def load_device_provider(self, device_provider):
        print('foudn device', device_provider)
        self.device_provider = device_provider
        self.device_provider.setup()
        self.device_provider.on('exception', self.handle_device_exception)
        self.device_provider.on('data', self.handle_receive_device_data)
        pass

    def start_websocket_server(self):
        # add ws handler as a member
        application = tornado.web.Application(
            [(r'/', WSHandler, dict(server=self))])
        self.http_server = tornado.httpserver.HTTPServer(application)
        self.http_server.listen(self.options.p)
        tornado.ioloop.IOLoop.instance().start()

    def handle_device_exception(self, error, message):
        print('recevied exception', error, message, self.ws_handler)
        if self.ws_handler:
            self.ws_handler.on_receive_output_packet(
                'stream', 'ping', {'status': 2})

        self.device_provider.close()
        self.detect_device(self.device_rediscover_handler)

    def handle_receive_device_data(self, method, packet_type, data):
        self.ws_handler.on_receive_output_packet()
        pass

    def detect_device(self, callback):
        print('start to find device')
        if self.communicator is None:
            self.communicator = CommunicatorFactory.create(
                self.communication, self.options)

        self.communicator.find_device(callback)

    def stop(self):
        if self.http_server is not None:
            self.http_server.stop()
