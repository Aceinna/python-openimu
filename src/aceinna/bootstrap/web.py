"""
Websocket server entry
"""
import os
import sys
#import asyncio
import json
import time
import traceback
import threading
import tornado.websocket
import tornado.ioloop
import tornado.httpserver
import tornado.web
from tornado import gen
from .. import VERSION
from ..devices.base.event_base import EventBase
from ..framework.communicator import CommunicatorFactory
from ..framework.context import APP_CONTEXT
from ..framework.file_storage import FileLoger
from ..framework.utils import (helper, resource)
from ..models import WebserverArgs
from ..framework.constants import DEFAULT_PORT_RANGE
from ..framework import AppLogger
if sys.version_info[0] > 2:
    from queue import Queue
else:
    from Queue import Queue

SERVER_UPDATE_RATE = 50


class WSHandler(tornado.websocket.WebSocketHandler):
    '''
    Websocket handler
    '''
    is_streaming = False
    is_logging = False
    latest_packet_collection = []
    file_logger = None
    packet_white_list = ['ping', 'upgrade_progress',
                         'upgrade_complete', 'mag_status', 'backup_status', 'restore_status']
    period_output_callback = None

    def initialize(self, server):
        '''
        Websocket handler initialize
        '''
        server.ws_handler = self

    def open(self):
        connected_device = self.get_device()
        if connected_device and connected_device.connected:
            self.handle_device_found(connected_device)
        else:
            self.response_device_isnot_connected()

        self.period_output_callback = tornado.ioloop.PeriodicCallback(
            self.response_output_packet, SERVER_UPDATE_RATE)
        self.period_output_callback.start()

    def on_message(self, message):
        client_msg = json.loads(message)
        method = client_msg['method'] if 'method' in client_msg else None
        parameters = client_msg['params'] if 'params' in client_msg else None
        if method:
            try:
                self.handle_message(method, parameters)
            except Exception as ex:  # pylint:disable=broad-except
                print('websocket on message error', ex)
                traceback.print_exc()
                self.response_message(
                    method, {'packetType': 'error', 'data': 'sever error'})
        else:
            self.response_unkonwn_method()

    def on_close(self):
        self.reset()
        try:
            self.period_output_callback.stop()
        except:  # pylint:disable=bare-except
            # need log exception
            pass
        connected_device = self.get_device()
        if connected_device:
            connected_device.remove_client(self)
            # print('close client count:', len(connected_device.clients))

    def check_origin(self, origin):
        return True

    def get_device(self):
        '''
        Get device
        '''
        return APP_CONTEXT.get_app().get_device()

    def on_receive_output_packet(self, method, packet_type, data):
        '''
        Listenr for receive output packet
        '''
        data_updated = False
        for item in self.latest_packet_collection:
            if item['packet_type'] == packet_type:
                item['data'] = data
                data_updated = True
                break

        if not data_updated:
            self.latest_packet_collection.append({
                'packet_type': packet_type,
                'data': data
            })

        if self.file_logger and self.is_logging:
            self.file_logger.append(packet_type, data)

    def reset(self):
        '''
        Reset status
        '''
        self.is_streaming = False
        self.is_logging = False
        if self.file_logger:
            self.file_logger.stop_user_log()

    def handle_message(self, method, parameters):
        '''
        Handle received message
        '''
        device = self.get_device()

        converted_method = helper.name_convert_camel_to_snake(method)

        if device and device.connected and hasattr(device, converted_method):
            device_command = getattr(
                device, converted_method, None)(parameters)
            self.response_message(method, device_command)

        elif hasattr(self, converted_method):
            getattr(self, converted_method, None)(parameters)
        else:
            self.response_unkonwn_method()

    def handle_device_found(self, device, force_response=True):
        '''
        If detect device, setup output and logger
        '''
        if len(device.clients) == 1:
            self.response_only_allow_one_client()
            return

        device.append_client(self)
        # print('open client count:', len(device.clients))

        self.file_logger = FileLoger(device.properties)
        if force_response:
            self.response_server_info(device)

    def response_message(self, method, data):
        '''
        Format response
        '''
        self.write_message(
            json.dumps(
                {
                    'method': method,
                    'result': data
                }
            ))

    def response_unkonwn_method(self):
        '''
        Format unknonwn method message
        '''
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

    def response_server_info(self, device):
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
                'deviceType': device.type
            }})

    def response_output_packet(self):
        '''
        Response streaming data
        '''
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
    # protocol

    def start_stream(self, *args):  # pylint: disable=invalid-name
        '''
        Start to send stream data
        '''
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
        self.file_logger.set_info(self.get_device().get_log_info())
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


class MessageStore(object):
    def __init__(self):
        self.messages = Queue()
        self.ready = False
        self.max_length = 100

    def append(self, msg):
        format_msg = '{} - {}: {}'.format(
            msg['asctime'],
            msg['levelname'],
            msg['message']
        )

        current_msg_len = self.messages.qsize()
        overflow_len = current_msg_len - self.max_length + 1
        for _ in range(overflow_len):
            self.messages.get()

        self.messages.put(format_msg)

    def get_messages(self):
        output_msg = []
        current_msg_len = self.messages.qsize()
        for _ in range(current_msg_len):
            output_msg.append(self.messages.get())
        return output_msg

    def empty(self):
        self.messages.empty()

    def size(self):
        return self.messages.qsize()


class LoggerServerSentEvent(tornado.web.RequestHandler):
    '''
    Send device data to client
    '''

    def __init__(self, *args, **kwargs):
        super(LoggerServerSentEvent, self).__init__(*args, **kwargs)
        #self.set_header('Content-Type', 'text/event-stream')
        #self.set_header('Access-Control-Allow-Origin', '*')

    def initialize(self, store):
        '''
        Websocket handler initialize
        '''
        self.store = store
        self._auto_finish = False

        self.set_header('Content-Type', 'text/event-stream')
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers', '*')
        self.set_header('Access-Control-Allow-Methods',
                        'GET, POST, PUT, DELETE, PATCH, OPTIONS')

    def get(self):
        self._loop = tornado.ioloop.PeriodicCallback(
            lambda: {self.emit()}, 1000)
        self._loop.start()

    @gen.coroutine
    def emit(self):
        '''
        Fetch log information from logger
        '''
        try:
            if self.store.size() == 0:
                yield self.flush()

            self.write('data:{}\n\n'.format(
                json.dumps({
                    'msg': self.store.get_messages()
                })
            ))
            yield self.flush()
        except tornado.iostream.StreamClosedError as e:
            self._loop.stop()
            self.finish()
        except RuntimeError as e:
            self._loop.stop()
            self.finish()


class Webserver(EventBase):
    '''
    Websocket server
    '''

    def __init__(self, **options):
        super(Webserver, self).__init__()
        self.communication = 'uart'
        self.device_provider = None
        self.communicator = None
        self.ws_handler = None
        self.sse_handler = None
        self.http_server = None
        self.non_main_ioloop = None
        self._build_options(**options)
        APP_CONTEXT.set_app(self)

        self.prepare_logger()

    def listen(self):
        '''
        Start to find device
        '''
        print("Python driver version: {0}".format(VERSION))
        loop = None  # asyncio.get_event_loop()

        thread = threading.Thread(target=self.start_webserver, args=(loop,))
        thread.start()

        thread = threading.Thread(
            target=self.detect_device_wrapper, args=(loop,))
        thread.start()

        #self.non_main_ioloop = tornado.ioloop.IOLoop.current()
        # loop.run_forever()

    def prepare_logger(self):
        '''
        Set default log handler: console logger, file logger
        '''
        executor_path = resource.get_executor_path()
        log_level = 'info'
        if self.options.debug:
            log_level = 'debug'

        console_log = self.options.console_log

        APP_CONTEXT.set_logger(
            AppLogger(
                filename=os.path.join(executor_path, 'loggers', 'trace.log'),
                gen_file=True,
                level=log_level,
                console_log=console_log
            ))

    def get_device(self):
        '''
        Get device provider
        '''
        if self.device_provider is not None:
            return self.device_provider
        return None

    def device_discover_handler(self, device_provider):
        '''
        Handler after device discovered
        '''
        # load device provider
        self.load_device_provider(device_provider)
        # notify ws handler
        if self.ws_handler:
            self.ws_handler.handle_device_found(
                device_provider)

    def device_rediscover_handler(self, device_provider):
        '''
        Handler after device rediscovered
        '''
        if self.device_provider.device_info['sn'] == device_provider.device_info['sn']:
            # if self.ws_handler:
            #     self.ws_handler.on_receive_output_packet(
            #         'stream', 'ping', {'status': 3})
            self.device_provider.close()
            self.load_device_provider(device_provider)
        else:
            self.device_provider.close()
            self.load_device_provider(device_provider)
            # if self.ws_handler:
            #     self.ws_handler.on_receive_output_packet(
            #         'stream', 'ping', {'status': 1})
            # self.ws_handler.handle_device_found(device_provider)

        if self.ws_handler:
            self.ws_handler.handle_device_found(device_provider)

    def device_complete_upgrade_handler(self, device_provider):
        '''
        Handler after device upgrade complete
        '''
        self.device_provider = device_provider
        self.device_provider.upgrade_completed(self.options)
        if self.device_provider.device_info['sn'] == device_provider.device_info['sn']:
            if self.ws_handler:
                self.ws_handler.on_receive_output_packet(
                    'stream', 'upgrade_complete', {'success': True})
        else:
            if self.ws_handler:
                self.ws_handler.on_receive_output_packet(
                    'stream', 'upgrade_complete', {'success': False})
         #   self.device_provider.close()

    def load_device_provider(self, device_provider):
        '''
        Load device provider
        '''
        self.device_provider = device_provider
        self.device_provider.setup(self.options)
        self.device_provider.on('exception', self.handle_device_exception)
        self.device_provider.on(
            'complete_upgrade', self.handle_device_complete_upgrade)

    def start_webserver(self, current_loop):
        # self.webserver_io_loop = asyncio.new_event_loop()
        if sys.version_info[0] > 2:
            import asyncio
            asyncio.set_event_loop(asyncio.new_event_loop())
            # asyncio.set_event_loop(current_loop)

        self.non_main_ioloop = tornado.ioloop.IOLoop.current()
        self.start_websocket_server()

    def start_websocket_server(self):
        '''
        Initial websocket server
        '''
        # add ws handler as a member
        store = MessageStore()
        try:
            application = tornado.web.Application(
                [
                    (r'/', WSHandler, dict(server=self)),
                    (r'/sse', LoggerServerSentEvent, dict(store=store))
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
            print('Websocket server is started on port', activated_port)

            APP_CONTEXT.get_logger().enable_msg_store_handler(store)
            self.non_main_ioloop.start()
            # tornado.ioloop.IOLoop.current().start()
        except Exception as ex:
            print(ex)
            # print('Cannot start a websocket server, please check if the port is in use')
            raise

    def handle_device_exception(self, error, message):
        '''
        Handle device exception
        '''
        APP_CONTEXT.get_logger().logger.error(message)

        if self.ws_handler:
            self.ws_handler.reset()
            self.ws_handler.on_receive_output_packet(
                'stream', 'ping', {'status': 2})

        self.device_provider.reset()
        self.detect_device(self.device_rediscover_handler)

    def handle_device_complete_upgrade(self):
        '''
        Handle device complete upgrade
        '''
        self.communicator.reset_buffer()
        self.communicator.close()
        # self.device_provider.reset()
        self.detect_device(self.device_complete_upgrade_handler)

    def detect_device_wrapper(self, current_loop):
        # self.webserver_io_loop = asyncio.new_event_loop()
        if sys.version_info[0] > 2:
            import asyncio
            asyncio.set_event_loop(asyncio.new_event_loop())
            # asyncio.set_event_loop(current_loop)

        #self.non_main_ioloop = tornado.ioloop.IOLoop.current()
        self.detect_device(self.device_discover_handler)

    def detect_device(self, callback):
        '''find if there is a connected device'''
        print('Prepare to find device...')
        if self.communicator is None:
            self.communicator = CommunicatorFactory.create(
                self.communication, self.options)

        self.communicator.find_device(callback)

    def set_communicator(self, communicator):
        self.communicator = communicator

    def stop_ws_server(self):
        '''close websocket server'''
        if self.http_server is not None:
            self.http_server.stop()

    def stop(self):
        self.stop_ws_server()

        if self.device_provider is not None:
            self.device_provider.close()

        time.sleep(1)

        if self.communicator is not None:
            self.communicator.close()

        if self.non_main_ioloop is not None:
            self.non_main_ioloop.add_callback_from_signal(
                self.non_main_ioloop.stop)
            self.non_main_ioloop.stop()

    def _build_options(self, **options):
        self.options = WebserverArgs(**options)
        self.communication = self.options.protocol.lower() \
            if self.options.protocol is not None else 'uart'
