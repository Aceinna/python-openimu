import os
import sys
import pkgutil
from ... import PACKAGE_NAME


def is_in_bundle():
    return hasattr(sys, 'frozen') and getattr(sys, 'frozen') and hasattr(sys, '_MEIPASS')


def is_dev_mode():
    return hasattr(sys, '__dev__') and getattr(sys, '__dev__')


def get_executor_path():
    if is_in_bundle():
        path = os.path.abspath(os.path.dirname(sys.executable))
    else:
        if is_dev_mode():  # if start from main.py
            path = os.getcwd()
        else:
            path = os.path.join(os.path.expanduser('~'), PACKAGE_NAME)
            if not os.path.isdir(path):
                os.makedirs(path)
    return path


def get_content_from_bundle(package, path):
    module_name = 'aceinna'
    if is_in_bundle():
        content = pkgutil.get_data(package, path)
    else:
        content = pkgutil.get_data(module_name, os.path.join(package, path))

    return content
