import os
import sys
import tornado.websocket
import tornado.ioloop
import tornado.httpserver
import tornado.web
from openimu.server import (
    server_version,
    WSHandler
)
from openimu.global_vars import imu
from openimu.predefine import (
    app_str,
    string_folder_path
)


tcpip_port = 8000

if __name__ == "__main__":
    print("server_version:", server_version)
    # Create IMU
    try:
        imu.ws = True
        imu.find_device()
        # Set up Websocket server on Port 8000
        # Port scan: from 8000 to 8003
        while True:
            try:
                application = tornado.web.Application([(r'/', WSHandler)])
                http_server = tornado.httpserver.HTTPServer(application)
                http_server.listen(tcpip_port)
                break
            except Exception as e:
                print(e)
                if tcpip_port > 8002:
                    print('port conflict, please input port number:')
                    os._exit(0)
                tcpip_port = tcpip_port + 1

        tornado.ioloop.IOLoop.instance().start()

    except KeyboardInterrupt:  # response for KeyboardInterrupt such as Ctrl+C
        print('User stop this program by KeyboardInterrupt! File:[{0}], Line:[{1}]'.format(
            __file__, sys._getframe().f_lineno))
        os._exit(1)
    except Exception as e:
        print(e)
