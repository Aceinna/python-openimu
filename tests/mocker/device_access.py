import os
import fcntl
import threading
import struct
import termios
import time

MOTION_DATA = []

if hasattr(termios, 'TIOCINQ'):
    TIOCINQ = termios.TIOCINQ
else:
    TIOCINQ = getattr(termios, 'FIONREAD', 0x541B)
TIOCM_zero_str = struct.pack('I', 0)


class DeviceAccess(object):
    def __init__(self, app_name):
        self._read_buffer = None
        self._output_buffer = None
        self._command_queue = []
        self._pipe_sensor_data_read = None
        self._pipe_sensor_data_write = None
        self._pipe_command_read = None
        self._pipe_command_write = None
        self._generator = None
        self._app = None
        self._app_name = app_name

        self._load(app_name)

    def start(self):
        self._pipe_sensor_data_read, self._pipe_sensor_data_write = os.pipe()
        self._pipe_command_read, self._pipe_command_write = os.pipe()

        fcntl.fcntl(self._pipe_sensor_data_read, fcntl.F_SETFL, os.O_NONBLOCK)
        fcntl.fcntl(self._pipe_command_read, fcntl.F_SETFL, os.O_NONBLOCK)

        thread = threading.Thread(target=self._run)
        thread.start()

    def _run(self):
        print('device is running')
        try:
            while True:
                # prepare output data
                self._prepare_data()
                # receive command, send to handler
                self._handle_command()
        except:
            os.close(self._pipe_sensor_data_read)
            os.close(self._pipe_sensor_data_write)
            os.close(self._pipe_command_read)
            os.close(self._pipe_command_write)

    def _load(self, app_name):
        # set application
        if app_name == 'IMU':
            from mocker.devices.openimu import OpenIMUMocker
            cls = OpenIMUMocker
        else:
            raise NotImplementedError("No matched device")
        self._app = cls()
        self._generator = self._app.gen_sensor_data()

    @property
    def in_waiting(self):
        """Return the number of bytes currently in the input buffer."""
        # ~ s = fcntl.ioctl(self.fd, termios.FIONREAD, TIOCM_zero_str)
        s = fcntl.ioctl(self._pipe_command_read, TIOCINQ, TIOCM_zero_str)
        return struct.unpack('I', s)[0]

    def _prepare_data(self):
        # read motion data, then send to _output_buffer
        sensor_data = next(self._generator)
        os.write(self._pipe_sensor_data_write, sensor_data)

    def _handle_command(self):
        command = None
        try:
            command = os.read(self._pipe_command_read, self.in_waiting)
        except:
            command = None

        if command:
            # do handle command
            response = self._app.handle_command(command)
            # write to response
            os.write(self._pipe_sensor_data_write, response)

    def write(self, data):
        if isinstance(data, str):
            os.write(self._pipe_command_write, data.encode('utf-8'))
        else:
            os.write(self._pipe_command_write, bytes(data))

    def read(self, size):
        read_result = bytearray()
        try:
            buf = os.read(self._pipe_sensor_data_read, size)
            read_result.extend(buf)
        except:
            pass
        return bytes(read_result)
