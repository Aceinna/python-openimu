import os
import sys
import json
import traceback
import tornado.websocket
import tornado.ioloop
import tornado.httpserver
import tornado.web
from .tunnel_base import (TunnelBase, TunnelEvents)
from .. import VERSION
from ..framework.context import APP_CONTEXT
from ..framework.constants import DEFAULT_PORT_RANGE
from ..framework.utils import (helper, resource)
from ..framework.decorator import skip_error
from ..framework.file_storage import FileLoger
from ..framework.utils.print import print_red
if sys.version_info[0] > 2:
    from queue import Queue
else:
    from Queue import Queue

SERVER_UPDATE_RATE = 50

OPERATION_PACKET_TYPES = [
    'ping', 'upgrade_complete',
    'mag_status', 'backup_status', 'restore_status'
]  # 'upgrade_progress'


class WSHandler(tornado.websocket.WebSocketHandler):
    '''
    Websocket handler
    '''
    is_streaming = False
    is_logging = False
    file_logger = None
    period_output_callback = None
    _output_packet_collection = {}
    _tunnel = None

    # override methods
    def initialize(self, server):
        '''
        Websocket handler initialize
        '''
        self._tunnel = server
        server.ws_handler = self

    def open(self):
        device_context = APP_CONTEXT.device_context

        if device_context and device_context.connected:
            self.handle_device_found(device_context)
        else:
            self.response_device_isnot_connected()

        self.period_output_callback = tornado.ioloop.PeriodicCallback(
            self.response_output_packet_data, SERVER_UPDATE_RATE)
        self.period_output_callback.start()

    def on_message(self, message):
        client_msg = json.loads(message)
        method = client_msg['method'] if 'method' in client_msg else None
        parameters = client_msg['params'] if 'params' in client_msg else None

        if not method:
            self.response_unkonwn_method()
            return

        try:
            self._handle_message(method, parameters)
        except Exception as ex:  # pylint:disable=broad-except
            print_red('Error when execute command:{0}'.format(ex))
            if resource.is_dev_mode():
                traceback.print_exc()
            self.response_message(
                method, {'packetType': 'error', 'data': 'Server Error'})

    def on_close(self):
        self._reset()
        try:
            self.period_output_callback.stop()
        except:  # pylint:disable=bare-except
            # need log exception
            pass

    def check_origin(self, origin):
        return True

    def handle_continous_data(self, packet_type, data):
        '''
        Listenr for receive output packet
        '''
        if packet_type in OPERATION_PACKET_TYPES:
            return self.response_message('stream', {
                'packetType': packet_type,
                'data': data
            })

        if packet_type == 'upgrade_progress':
            self._output_packet_collection[packet_type] = data

        if not self.is_streaming:
            return

        if not packet_type in self._output_packet_collection:
            self._output_packet_collection[packet_type] = []

        self._output_packet_collection[packet_type].append(data)

        if self.file_logger and self.is_logging:
            self.file_logger.append(packet_type, data)

    # private
    def _reset(self):
        '''
        Reset some status after request from client
        '''
        self.is_streaming = False
        self.is_logging = False
        if self.file_logger:
            self.file_logger.stop_user_log()

    def _handle_message(self, method, parameters):
        '''
        Handle received message
        '''
        device_context = APP_CONTEXT.device_context

        converted_method = helper.name_convert_camel_to_snake(method)

        if hasattr(self, converted_method):
            getattr(self, converted_method, None)(parameters)
        else:
            # if device_context.check_allow_method(converted_method):
            try:
                self._tunnel.emit(TunnelEvents.Request,
                                  method,
                                  converted_method,
                                  parameters)
            except Exception as ex:
                if resource.is_dev_mode():
                    traceback.print_exc()
                self.response_unkonwn_method()

    def handle_device_found(self, device_context, force_response=True):
        '''
        If detect device, setup output and logger
        '''
        if self.ws_connection is None or self.ws_connection.is_closing():
            return

        self.file_logger = FileLoger(device_context.properties)
        if force_response:
            self.response_server_info(device_context)

    # response
    def response_device_lost(self):
        self.response_message(
            'stream', {
                'packetType': 'ping', 'data': {'status': 2}
            })
        self.response_message('stream', {
            'packetType': 'serverInfo',
            'data': {
                'version': VERSION,
                'serverUpdateRate': 50,
                'deviceConnected': False,
                'clientCount': 0,
            }})

    def response_invoke(self, method, result):
        self.response_message(method, result)

    @skip_error(tornado.websocket.WebSocketClosedError)
    def response_message(self, method, data):
        '''
        Format response
        '''
        loop = None
        if sys.version_info[0] > 2:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                pass

            if not loop:
                loop = self._tunnel.non_main_ioloop.asyncio_loop
                asyncio.set_event_loop(loop)

        self.write_message(
            json.dumps({
                'method': method,
                'result': data
            }))

    @skip_error(tornado.websocket.WebSocketClosedError)
    def response_unkonwn_method(self):
        '''
        Format unknonwn method message
        '''
        self.response_message('unknown', {
            'packetType': 'error',
            'data': {
                'message': 'unknown method'
            }})

    def response_server_info(self, device_context):
        '''
        Send webserver info
        '''
        self.response_message('stream', {
            'packetType': 'serverInfo',
            'data': {
                'version': VERSION,
                'serverUpdateRate': 50,
                'deviceConnected': True,
                'clientCount': 0,
                'deviceType': device_context.device_type
            }})

    @skip_error(tornado.websocket.WebSocketClosedError)
    def response_output_packet_data(self):
        '''
        Response continous data
        '''

        # fetch data from output_packet_queue
        collection_clone = self._output_packet_collection.copy()
        # TODO: may have object sync issue because of multi thread
        for packet_type in self._output_packet_collection:
            self._output_packet_collection[packet_type] = []

        for packet_type in collection_clone:
            if len(collection_clone[packet_type]) > 0:
                self.response_message('stream', {
                    'packetType': packet_type,
                    'data': collection_clone[packet_type]
                })

        if not self.is_streaming:
            return

        statistics_result = APP_CONTEXT.statistics.get_result()
        if statistics_result:
            self.response_message('stream', {
                'packetType': 'statistics',
                'data': statistics_result
            })

    def response_device_isnot_connected(self):
        '''
        Response device is not connected
        '''
        self.response_message('stream', {
            'packetType': 'serverInfo',
            'data': {
                'version': VERSION,
                'serverUpdateRate': SERVER_UPDATE_RATE,
                'deviceConnected': False,
                'clientCount': 0
            }})

    def response_only_allow_one_client(self):
        '''
        Response only allow one client connect
        '''
        self.response_message('stream', {
            'packetType': 'serverInfo',
            'data': {
                'version': VERSION,
                'serverUpdateRate': SERVER_UPDATE_RATE,
                'deviceConnected': True,
                'clientCount': 1
            }})

    # partial implements of message communication protocol

    def start_stream(self, *args):  # pylint: disable=invalid-name
        '''
        Start to send stream data
        '''
        self._output_packet_collection = {}
        self.response_message('startStream', {'packetType': 'success'})
        self.is_streaming = True

    def stop_stream(self, *args):  # pylint: disable=invalid-name
        '''
        Stop sending stream data
        '''
        self.response_message('stopStream', {'packetType': 'success'})
        self.is_streaming = False

    def start_log(self, *args):  # pylint: disable=invalid-name
        '''
        Start record log
        '''
        parameters = args[0]
        device_context = APP_CONTEXT.device_context
        self.file_logger.set_info(device_context.get_log_info)
        self.file_logger.set_user_id(parameters['id'])
        self.file_logger.set_user_access_token(parameters['access_token'])
        self.file_logger.start_user_log(parameters['fileName'], True)
        self.is_logging = True
        self.response_message(
            'startLog', {'packetType': 'success', 'data': parameters['fileName']+'.csv'})

    def stop_log(self, *args):  # pylint: disable=invalid-name
        '''
        Stop record log
        '''
        self.file_logger.stop_user_log()
        self.is_logging = False
        self.response_message('stopLog', {'packetType': 'success', 'data': ''})


class UploadHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers',
                        'x-requested-with, authorization')
        self.set_header('Access-Control-Allow-Methods',
                        'POST, GET, PUT, DELETE')

    def get(self):
        self.write('upload')

    def post(self, *args, **kwargs):
        files = self.request.files
        uploaded_files = []

        try:
            for inputname in files:
                http_file = files[inputname]
                for file_inst in http_file:
                    file_path = os.path.join(
                        resource.get_executor_path(), 'upgrade', file_inst.filename)

                    with open(file_path, 'wb') as file_writer:
                        file_writer.write(file_inst.body)

                    uploaded_files.append(
                        {'name': file_inst.filename, 'path': file_path})
            self.write({
                'success': True,
                'data': uploaded_files
            })
        except Exception as ex:
            print_red(ex)
            self.write({
                'success': False
            })

    def options(self):
        # no body
        self.set_status(204)
        self.finish()


class WebServer(TunnelBase):
    ws_handler = None
    options = None
    http_server = None
    non_main_ioloop = None

    def __init__(self, options, event_loop):
        super(WebServer, self).__init__()
        self.options = options
        if not event_loop:
            event_loop = tornado.ioloop.IOLoop.current()

        self.non_main_ioloop = event_loop

    def notify(self, notify_type, *other):
        if self.ws_handler is None:
            return

        if notify_type == 'continous':
            return self.ws_handler.handle_continous_data(*other)

        if notify_type == 'discovered':
            device_context = APP_CONTEXT.device_context
            return self.ws_handler.handle_device_found(device_context)

        if notify_type == 'lost':
            return self.ws_handler.response_device_lost(*other)

        if notify_type == 'invoke':
            return self.ws_handler.response_invoke(*other)

    def setup(self):
        try:
            application = tornado.web.Application(
                [
                    (r'/', WSHandler, dict(server=self)),
                    (r'/upload', UploadHandler)
                ])
            self.http_server = tornado.httpserver.HTTPServer(application)
            # self.http_server.listen(self.options.port)
            activated_port = 0
            if self.options.port == 'auto':
                for webserver_port in DEFAULT_PORT_RANGE:
                    try:
                        self.http_server.listen(webserver_port)
                        activated_port = webserver_port
                        break
                    except Exception as ex:
                        print(ex)
                        continue
                if activated_port == 0:
                    raise Exception('Port in used')
            else:
                self.http_server.listen(self.options.port)
                activated_port = self.options.port
            print('[Info] Websocket server is started on port', activated_port)
            self.non_main_ioloop.start()
            # tornado.ioloop.IOLoop.current().start()
        except Exception as ex:
            print(ex)
            # print('Cannot start a websocket server, please check if the port is in use')
            raise

    def stop_ws_server(self):
        if self.http_server is not None:
            self.http_server.stop()

    def stop(self):
        self.stop_ws_server()

        if self.non_main_ioloop is not None:
            self.non_main_ioloop.add_callback_from_signal(
                self.non_main_ioloop.stop)
            self.non_main_ioloop.stop()
