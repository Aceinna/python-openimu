import os
import subprocess
import requests
import threading
from .. import VERSION
from ..models import (VersionInfo, LocalInstallerInfo)


def get_installed_info():
    import winreg

    location = None
    has_value = False
    string = r'Software\Aceinna_Devices_Driver'
    try:
        handle = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, string, 0,
                                winreg.KEY_READ)
        location, _ = winreg.QueryValueEx(handle, "Install_Dir")
        has_value = True
    except:
        location = None
        has_value = False

    return location, has_value


class AutoUpdater(object):
    def __init__(self):
        installed_path, is_installed = get_installed_info()
        self._installed_path = installed_path
        self._is_installed = is_installed

    def check(self):
        # check if there new version on remote server
        print('check if there new version on remote server')
        new_version_info = self._get_new_version_info()
        if new_version_info:
            #inform there is a new version
            self._print_new_version()

            if self._is_installed:
                thread = threading.Thread(target=self._download_installer,
                                          args=(new_version_info, ))
                thread.start()

        # check if local has a new install file
        print('check if local has a new install file')
        exist_install_file_info = self._get_exist_install_file_info()
        if  new_version_info and \
            exist_install_file_info and \
            new_version_info.version == exist_install_file_info.version:
            is_process_install = self._inform_user(new_version_info.version)

            if is_process_install:
                self._run_installer(exist_install_file_info.path)

    #TODO
    def _get_new_version_info(self):
        version_info = None
        # check if has network, do a ping

        # access remote interface

        # request github release

        version_info = VersionInfo()
        version_info.name = ''
        version_info.url = ''
        version_info.version_no = ''

        return version_info

    def _get_exist_install_file_info(self):
        if self._installed_path and self._is_installed:
            # check if exists installed folder/versions
            installers_path = os.path.join(self._is_installed, 'versions')
            if not os.path.isdir(installers_path):
                return None

            # list the files, and find the last modified file with name format=installer.{version}.exe
            install_file = self._get_latest_install_file(installers_path)

            return install_file
        return None

    def _get_latest_install_file(self, installers_path):
        latest_version = ''
        install_files = []
        reg_expression = 'installer.(\S+).exe'

        with os.scandir(installers_path) as it:
            for entry in it:
                if entry.is_file() and re.match(reg_expression, entry.name,
                                                re.M | re.I):
                    install_files.append(entry.path)

        if len(install_files) == 0:
            return None

        return install_files.sort(reverse=True)[0]

    def _run_installer(self, installer_path):
        # Start to install new version
        subprocess.Popen([installer_path])
        # kill current process
        os.kill(os.getpid(), signal.SIGTERM)

    #TODO
    def _download_installer(self, version_info: VersionInfo):
        can_download = False
        # create a temp file
        temp_name = 'TMP-xxx'
        # save to installed folder/versions
        saved_folder = os.path.join(self._installed_path, 'versions')
        if not os.path.isdir(saved_folder):
            os.makedirs(saved_folder)

        try:
            # download from parsed link
            can_download = self._do_download(version_info.url, temp_name,
                                             saved_folder)
        except:
            # rename the temp file as a format name
            # log the exception while downloading
            pass

        if can_download:
            # rename the temp file as a format name
            os.replace(
                os.path.join(self._installed_path, temp_name),
                os.path.join(self._installed_path,
                             'installer.' + version_info.version_no + '.exe'))
        else:
            # remove temp files if there is any exception
            pass

    def _do_download(self, url, temp_name, saved_folder):
        chunk_size = 4096
        response = requests.get(url=url, stream=True)
        start = time.time()
        size = 0
        content_size = int(response.headers['content-length'])

        if response.status_code == 200:
            filepath = os.path.join(saved_folder, temp_name)
            with open(filepath, 'wb') as file:
                for data in response.iter_content(chunk_size=chunk_size):
                    file.write(data)
                    size += len(data)
            end = time.time()
        else:
            return False

        return True

    def _remove_temp_files(self):

        pass

    def _print_new_version(self):
        if self._is_installed:
            print('New version is found, downloading...')
        else:
            print(
                'New version is found, please download the lastest version on https://github.com/Aceinna/python-openimu/releases'
            )

    def _inform_user(self, version_no):
        answer = input(
            'New version {0} is prepared, continue to update? y/n (yes)'.
            format(version_no))
        is_yes_option = ['y', 'yes', ''].__contains__(answer.lower())
        return is_yes_option
