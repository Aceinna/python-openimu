import sys
import json
import tornado.websocket
import tornado.ioloop
import tornado.httpserver
import tornado.web
import traceback
from .base import BootstrapBase
from ..framework.communicator import CommunicatorFactory
from ..framework.context import app_context
from ..framework.file_storage import FileLoger
from ..framework.utils import helper


class WSHandler(tornado.websocket.WebSocketHandler):
    is_streaming = False
    is_logging = False
    latest_packet_collection = []
    file_logger = None
    packet_white_list = ['ping', 'upgrade_progress',
                         'upgrade_complete', 'mag_status']

    def initialize(self, server):
        server.ws_handler = self

    def open(self):
        self.get_device().append_client(self)
        print('open client count:', len(self.get_device().clients))
        self.period_output_callback = tornado.ioloop.PeriodicCallback(
            self.response_output_packet, self.get_device().server_update_rate)
        self.period_output_callback.start()

        self.file_logger = FileLoger(self.get_device().properties)

        self.response_server_info()  # response server info at first time connected
        pass

    def on_message(self, message):
        client_msg = json.loads(message)
        method = client_msg['method'] if 'method' in client_msg else None
        parameters = client_msg['params'] if 'params' in client_msg else None
        if method:
            try:
                self.handle_message(method, parameters)
            except Exception as e:
                print('websocket on message error', e)
                traceback.print_exc()
                self.response_message(
                    method, {'packetType': 'error', 'data': 'sever error'})
        else:
            self.response_unkonwn_method()

    def on_close(self):
        self.reset()
        try:
            self.period_output_callback.stop()
        except Exception as e:
            pass
        self.get_device().remove_client(self)
        print('close client count:', len(self.get_device().clients))

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

        if self.file_logger and self.is_logging:
            self.file_logger.append(packet_type, data)

    def reset(self):
        self.is_streaming = False
        self.is_logging = False
        if self.file_logger:
            self.file_logger.stop_user_log()

    def handle_message(self, method, parameters):
        device = self.get_device()

        if device and device.connected and hasattr(device, method):
            result = getattr(device, method, None)(parameters)
            self.response_message(method, result)
        elif hasattr(self, method):
            getattr(self, method, None)(parameters)

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
            if latest_packet['packet_type'] in self.packet_white_list or self.is_streaming:
                self.write_message(
                    json.dumps({
                        'method': 'stream',
                        'result': {
                            'packetType': latest_packet['packet_type'],
                            'data': latest_packet['data']
                        }
                    })
                )

        helper.clear_elements(self.latest_packet_collection)

    # protocol

    def startStream(self, *args):
        self.response_message('startStream', {'packetType': 'success'})
        self.is_streaming = True

    def stopStream(self, *args):
        self.response_message('stopStream', {'packetType': 'success'})
        self.is_streaming = False

    def startLog(self, *args):
        parameters = args[0]
        self.file_logger.set_info(self.get_device().get_log_info())
        self.file_logger.set_user_id(parameters['id'])
        self.file_logger.set_user_access_token(parameters['access_token'])
        self.file_logger.start_user_log(parameters['fileName'], True)
        self.is_logging = True
        self.response_message(
            'startLog', {'packetType': 'success', 'data': parameters['fileName']+'.csv'})

    def stopLog(self, *args):
        self.file_logger.stop_user_log()
        self.is_logging = False
        self.response_message('stopLog', {'packetType': 'success', 'data': ''})


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
        return None

    def device_discover_handler(self, device_provider):
        # load device provider
        self.load_device_provider(device_provider)
        # start websocket server
        self.start_websocket_server()

    def device_rediscover_handler(self, device_provider):
        if self.device_provider.device_info['sn'] == device_provider.device_info['sn']:
            if self.ws_handler:
                self.ws_handler.on_receive_output_packet(
                    'stream', 'ping', {'status': 3})
        else:
            if self.ws_handler:
                self.ws_handler.on_receive_output_packet(
                    'stream', 'ping', {'status': 1})
            self.device_provider.close()

        self.load_device_provider(device_provider)

    def device_complete_upgrade_handler(self, device_provider):
        if self.device_provider.device_info['sn'] == device_provider.device_info['sn']:
            if self.ws_handler:
                self.ws_handler.on_receive_output_packet(
                    'stream', 'upgrade_complete', {'success': True})
        else:
            if self.ws_handler:
                self.ws_handler.on_receive_output_packet(
                    'stream', 'upgrade_complete', {'success': False})
            self.device_provider.close()

        self.device_provider = device_provider
        self.device_provider.upgrade_completed(self.options)

    def load_device_provider(self, device_provider):
        self.device_provider = device_provider
        self.device_provider.setup(self.options)
        self.device_provider.on('exception', self.handle_device_exception)
        self.device_provider.on(
            'complete_upgrade', self.handle_device_complete_upgrade)
        # self.device_provider.on('data', self.handle_receive_device_data)
        pass

    def start_websocket_server(self):
        # add ws handler as a member
        try:
            application = tornado.web.Application(
                [(r'/', WSHandler, dict(server=self))])
            self.http_server = tornado.httpserver.HTTPServer(application)
            self.http_server.listen(self.options.p)
            tornado.ioloop.IOLoop.instance().start()
        except Exception as e:
            print('Cannot start a websocket, please check if the port is in use')
            raise

    def handle_device_exception(self, error, message):
        if self.ws_handler:
            self.ws_handler.reset()
            self.ws_handler.on_receive_output_packet(
                'stream', 'ping', {'status': 2})

        self.device_provider.reset()
        self.detect_device(self.device_rediscover_handler)

    def handle_device_complete_upgrade(self):
        self.communicator.reset_buffer()
        self.communicator.close()
        # self.device_provider.reset()
        self.detect_device(self.device_complete_upgrade_handler)

    # def handle_receive_device_data(self, method, packet_type, data):
    #     self.ws_handler.on_receive_output_packet()
    #     pass

    def detect_device(self, callback):
        print('start to find device')
        if self.communicator is None:
            self.communicator = CommunicatorFactory.create(
                self.communication, self.options)

        self.communicator.find_device(callback)

    def stop(self):
        if self.http_server is not None:
            self.http_server.stop()
