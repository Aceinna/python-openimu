import os
from ctypes import *
from ..framework.utils import resource


def prepare_lib_folder():
    executor_path = resource.get_executor_path()
    lib_folder_name = 'libs'

    # copy contents of setting file under executor path
    lib_folder_path = os.path.join(
        executor_path, lib_folder_name)

    if not os.path.isdir(lib_folder_path):
        os.makedirs(lib_folder_path)

    lib_file = 'UserDecoderLib.so'
    if os.name == 'nt':  # windows
        lib_file = "UserDecoderLib.dll"

    lib_path = os.path.join(lib_folder_path, lib_file)

    if not os.path.isfile(lib_path):
        lib_content = resource.get_content_from_bundle(
            lib_folder_name, lib_file)
        if lib_content is None:
            raise ValueError('Lib file content is empty')

        with open(lib_path, "wb") as code:
            code.write(lib_content)

    return lib_path


def do_parse(folder_path, kml_rate, setting_file):
    lib_path = prepare_lib_folder()

    lib = CDLL(lib_path)
    for root, _, file_name in os.walk(folder_path):
        for fname in file_name:
            if fname.startswith('user') and fname.endswith('.bin'):
                file_path = os.path.join(folder_path, fname)
                lib.decode_openrtk_user(bytes(file_path, encoding='utf8'))
