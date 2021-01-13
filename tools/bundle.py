# build a setup execution
import subprocess
import os

EXECUTABLE_NAME = 'ans-devices.exe'
RELESE_PATH = 'C:\\Users\\bawei\\Documents\\Projects\\forks\\python-openimu\\dist'
NSIS_PATH = 'C:\\Users\\bawei\\Documents\\Projects\\forks\\python-openimu\\tools\\nsis'
TEMPLATES_PATH = 'C:\\Users\\bawei\\Documents\\Projects\\forks\\python-openimu\\tools\\templates'
VERSION = '1.0.0'


# TODO: add version
def run_command(command, arguments, script):
    subprocess.run([command, *arguments, script])


def build():
    command = os.path.join(NSIS_PATH, 'makensis.exe')
    arguments = [
        '-DEXECUTABLE=' + os.path.join(RELESE_PATH, EXECUTABLE_NAME),
        '-XOutFile ' +
        os.path.join(RELESE_PATH, 'ans-device-setup' + VERSION + '.exe')
    ]
    script = os.path.join(TEMPLATES_PATH, 'install.nsi')
    run_command(command, arguments, script)


if __name__ == '__main__':
    build()
