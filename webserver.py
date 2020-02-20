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

tcpip_port_scan = 8000

if __name__ == "__main__":
    print("server_version:", server_version)
    # Create IMU
    try:
        imu.ws = True
        imu.find_device()
        application = tornado.web.Application([(r'/', WSHandler)])
        http_server = tornado.httpserver.HTTPServer(application)
        # no port input,websocket server auto scan Port setup,from 8000 to 8003. 8123 just the default input value to be checked.
        if imu.input_tcpip_port == 8123:
            while True:
                try:
                    http_server.listen(tcpip_port_scan)
                    break
                except Exception as e:
                    # print(e)
                    if tcpip_port_scan > 8002:
                        print(
                            'port conflict,please input port with command: -p port_number, type -h will get the help information!')
                        os._exit(0)
                    tcpip_port_scan = tcpip_port_scan + 1
        # setup websocket port with input port number
        else:
            http_server.listen(imu.input_tcpip_port)
        tornado.ioloop.IOLoop.instance().start()

    except KeyboardInterrupt:  # response for KeyboardInterrupt such as Ctrl+C
        print('User stop this program by KeyboardInterrupt! File:[{0}], Line:[{1}]'.format(
            __file__, sys._getframe().f_lineno))
        os._exit(1)
    except Exception as e:
        print(e)
