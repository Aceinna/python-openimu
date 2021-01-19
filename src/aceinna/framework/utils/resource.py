import os
import sys
import pkgutil
import platform
from ... import PACKAGE_NAME


def is_in_bundle():
    return hasattr(sys, 'frozen') and getattr(sys, 'frozen') and hasattr(
        sys, '_MEIPASS')


def is_dev_mode():
    return hasattr(sys, '__dev__') and getattr(sys, '__dev__')


def get_executor_path():
    if is_in_bundle():
        path = os.path.abspath(os.path.dirname(sys.executable))

        # check if local is installed the package, only for windows
        _, is_installed = get_installed_info()
        if is_installed:
            path = os.path.join(os.getenv("LOCALAPPDATA"),
                                'AceinnaDevicesDriver')
    else:
        if is_dev_mode():  # if start from main.py
            path = os.getcwd()
        else:
            path = os.path.join(os.path.expanduser('~'), PACKAGE_NAME)

    if not os.path.exists(path):
        os.makedirs(path)
    return path


def get_content_from_bundle(package, path):
    module_name = 'aceinna'
    if is_in_bundle():
        content = pkgutil.get_data(package, path)
    else:
        content = pkgutil.get_data(module_name, os.path.join(package, path))

    return content


def get_installed_info():
    if not 'Windows' in platform.system():
        return None, False

    import winreg

    location = None
    has_value = False
    string = r'Software\Aceinna_Devices_Driver'
    try:
        handle = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, string, 0,
                                winreg.KEY_WOW64_32KEY + winreg.KEY_READ)
        location, _ = winreg.QueryValueEx(handle, "Install_Dir")
        has_value = True
    except:
        location = None
        has_value = False

    return location, has_value