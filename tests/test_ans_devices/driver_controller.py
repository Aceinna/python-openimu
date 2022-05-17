"""This module defines the `ProcessController` class
which runs app as a subprocess and can write to it and read from it to get
structured output.
"""

import logging
import subprocess
from distutils.spawn import find_executable
from typing import Union, List, Optional
from io_manager import IoManager
from constants import (
    DEFAULT_PROCESS_TIMEOUT_SEC,
    DEFAULT_TIME_TO_CHECK_FOR_ADDITIONAL_OUTPUT_SEC,
)
import time
import process_parser
import sys

DEFAULT_PROCESS_LAUNCH_COMMAND = ["./ans-devices.exe", "--cli"]
logger = logging.getLogger(__name__)


class ProcessController:
    def __init__(
        self,
        command,
        time_to_check_for_additional_output_sec=DEFAULT_TIME_TO_CHECK_FOR_ADDITIONAL_OUTPUT_SEC,
    ):
        """
        Run a subprocess. Send commands and receive structured output.
        Create new object, along with subprocess

        Args:
            command: Command to run in shell to spawn new subprocess
            time_to_check_for_additional_output_sec: When parsing responses, wait this amout of time before exiting (exits before timeout is reached to save time). If <= 0, full timeout time is used.
        Returns:
            New ProcessController object
        """

        if command is None:
            command = DEFAULT_PROCESS_LAUNCH_COMMAND

        # if not any([("--interpreter=mi" in c) for c in command]):
        #     logger.warning(
        #         "warning. "
        #     )
        self.abs_app_path = None  # abs path to executable
        self.command = command  # type: List[str]
        self.time_to_check_for_additional_output_sec = (
            time_to_check_for_additional_output_sec
        )
        self.app_process = None
        self._allow_overwrite_timeout_times = (
            self.time_to_check_for_additional_output_sec > 0
        )
        app_path = command.split(' ')[0]

        if not app_path:
            raise ValueError("a valid path to app must be specified")

        else:
            abs_app_path = find_executable(app_path)
            if abs_app_path is None:
                raise ValueError(
                    'executable could not be resolved from "%s"' % app_path
                )

            else:
                self.abs_app_path = abs_app_path
        self.spawn_new_subprocess()

    def spawn_new_subprocess(self):
        """Spawn a new subprocess with the arguments supplied to the object
        during initialization. If subprocess already exists, terminate it before
        spanwing a new one.
        Return int: process id
        """
        if self.app_process:
            logger.debug(
                "Killing current subprocess (pid %d)" % self.app_process.pid
            )
            self.exit()

        logger.debug(f'Launching app: {" ".join(self.command)}')
        # print('xxxxxxxxxxxxxxxxxxxxx', self.command)
        # Use pipes to the standard streams
        self.app_process = subprocess.Popen(
            self.command,
            shell=False,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        self.io_manager = IoManager(
            self.app_process.stdin,
            self.app_process.stdout,
            self.app_process.stderr,
            self.time_to_check_for_additional_output_sec,
        )
        return self.app_process.pid

    def get_process_response(
        self, timeout_sec: float = DEFAULT_PROCESS_TIMEOUT_SEC, raise_error_on_timeout=True
    ):
        """Get process response. See IoManager.get_process_response() for details"""
        return self.io_manager.get_process_response(timeout_sec, raise_error_on_timeout)

    def write(
        self,
        mi_cmd_to_write: Union[str, List[str]],
        timeout_sec=DEFAULT_PROCESS_TIMEOUT_SEC,
        raise_error_on_timeout: bool = True,
        read_response: bool = True,
    ):
        # print('cmd: ', mi_cmd_to_write)
        """Write command to process. See IoManager.write() for details"""
        return self.io_manager.write(
            mi_cmd_to_write, timeout_sec, raise_error_on_timeout, read_response
        )

    def exit(self) -> None:
        """Terminate process"""
        if self.app_process:
            self.app_process.terminate()
            self.app_process.communicate()
        self.app_process = None
        return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('input upgrade file')
        exit(-1)
    upgrade_file = sys.argv[1]
    fs_log = open('./log.txt', 'w')
    driver_cmd = './ans-devices.exe --cli'
    app_handle = ProcessController(driver_cmd)
    suc_count = 0
    fail_count = 0
    data = ''
    process_ret = ''
    while True:
        while True:
            try:
                response = app_handle.get_process_response()
                try:
                    process_ret += process_parser.get_gdb_response_str(response)
                except Exception as e:
                    print(e)
                if 'Connected' in process_ret:
                    print('python drivder connected...')
                    fs_log.write(process_ret)
                    process_ret = ''
                    break
            except Exception as e:
                time.sleep(1)
                print('wait to connect')
        time.sleep(3)
        while True:
            response = app_handle.write('upgrade {0}'.format(upgrade_file), 1, read_response = False)
            time_used = 0
            while True:
                
                try:
                    app_handle.write('', 1, read_response = False)
                    response = app_handle.get_process_response()
                    try:
                        process_ret += process_parser.get_gdb_response_str(response)
                    except Exception as e:
                        print(e)
                    if 'RTK_INS App' in process_ret:
                        print('upgrade suc...')
                        suc_count+= 1
                        break
                    elif 'failed' in process_ret:
                        print('upgrade fail...')
                        fail_count+= 1
                        break
                except Exception as e:
                    time.sleep(1)
                    time_used+= 2
                    print("\rtime used: %ds" %(time_used), end="")
                    if time_used % 10 == 10:
                        app_handle.write('ls', 1, read_response = False)
                    if time_used > 200:
                        print('time out')
                        time_used = 0
                        fail_count+= 1
                        break

            print('suc_count = {0}, fail_count = {1}'.format(suc_count, fail_count))
            fs_log.write(process_ret)
            time.sleep(5)
            process_ret = ''