# build a setup execution
import subprocess
import os
import json
import datetime
import sys

sys.path.append('./')
from src.aceinna import VERSION

EXECUTABLE_NAME = 'ans-devices.exe'
RELESE_PATH = 'C:\\Users\\bawei\\Documents\\Projects\\forks\\python-openimu\\dist'
NSIS_PATH = 'C:\\Users\\bawei\\Documents\\Projects\\forks\\python-openimu\\tools\\nsis'
TEMPLATES_PATH = 'C:\\Users\\bawei\\Documents\\Projects\\forks\\python-openimu\\tools\\templates'
SETUP_FILE_NAME = 'Setup.' + VERSION + '.exe'


# TODO: add version
def run_command(command, arguments, script):
    subprocess.run([command, *arguments, script])


def build():
    build_setup()
    build_package_info()


def build_setup():
    command = os.path.join(NSIS_PATH, 'makensis.exe')
    arguments = [
        '-DEXECUTABLE=' + os.path.join(RELESE_PATH, EXECUTABLE_NAME),
        '-XOutFile ' + os.path.join(RELESE_PATH, SETUP_FILE_NAME)
    ]
    script = os.path.join(TEMPLATES_PATH, 'install.nsi')
    run_command(command, arguments, script)


def build_package_info():
    package_info_path = os.path.join(RELESE_PATH, 'latest.json')
    try:
        with open(package_info_path, 'w') as outfile:
            json.dump(
                {
                    'name':
                    'Aceinna Devices Driver',
                    'version':
                    VERSION,
                    'url':
                    SETUP_FILE_NAME,
                    'releaseDate':
                    datetime.datetime.utcnow().strftime(
                        "%Y-%m-%dT%H:%M:%S.%fZ")
                }, outfile)
    except Exception as ex:
        print(ex)
        pass


if __name__ == '__main__':
    build()
