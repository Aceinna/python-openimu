# build a setup execution
import subprocess
import os
import json
import datetime
import sys

sys.path.append('./')
from src.aceinna import VERSION

ELEVATE_NAME = 'elevate.exe'
EXECUTABLE_NAME = 'ans-devices.exe'
RELESE_PATH = os.path.join(os.getcwd(), 'dist')
NSIS_PATH = os.path.join(os.getcwd(), 'tools', 'nsis')
TEMPLATES_PATH = os.path.join(os.getcwd(), 'tools', 'templates')
SETUP_FILE_NAME = 'Setup.' + VERSION + '.exe'


# TODO: add version
def run_command(command, arguments, script):
    subprocess.run([command, *arguments, script], env={"NSISDIR": NSIS_PATH})


def build():
    build_setup()
    build_package_info()


def build_setup():
    command = os.path.join(NSIS_PATH, 'makensis.exe')
    arguments = [
        '-DEXECUTABLE=' + os.path.join(RELESE_PATH, EXECUTABLE_NAME),
        '-DELEVATE=' + os.path.join(NSIS_PATH, ELEVATE_NAME),
        '-DVERSION=' + VERSION,
        '-XOutFile ' + os.path.join(RELESE_PATH, SETUP_FILE_NAME)
    ]
    script = os.path.join(TEMPLATES_PATH, 'install.nsi')
    run_command(command, arguments, script)


def build_package_info():
    package_info_path = os.path.join(RELESE_PATH, 'latest.json')
    try:
        package_info = {}
        package_info['name'] = 'Aceinna Devices Driver'
        package_info['version'] = VERSION
        package_info['url'] = SETUP_FILE_NAME
        package_info['releaseDate'] = datetime.datetime.utcnow().strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ")
        with open(package_info_path, 'w') as outfile:
            json.dump(package_info, outfile)
    except Exception as ex:
        print(ex)


if __name__ == '__main__':
    build()
