import os
import subprocess
import requests
import signal
import threading
import json
import time
import re
from .. import VERSION
from ..models import (VersionInfo, LocalInstallerInfo)
from ..framework.utils.print import print_green
from ..framework.terminal import Choice
from ..framework.utils.resource import (get_executor_path, get_installed_info)

github_owner = 'baweiji'

github_repo = 'python-openimu'

current_milli_time = lambda: int(round(time.time() * 1000))


class AutoUpdater(object):
    def __init__(self):
        installed_path, is_installed = get_installed_info()
        self._installed_path = installed_path
        self._is_installed = is_installed
        self._skip_versions = []

    def check(self):
        # check if local has a new install file
        is_process_install = False
        exist_install_file_info, self._skip_versions = self._get_exist_install_file_info(
        )

        if  exist_install_file_info and \
            VERSION < exist_install_file_info.version_no and \
            not self._skip_versions.__contains__(exist_install_file_info.version_no):

            process_option_index = self._inform_user(
                exist_install_file_info.version_no)

            is_process_install = process_option_index == 0

            if process_option_index == 0:
                self._run_installer(exist_install_file_info.path)
                return

            if process_option_index == 2:
                #store skip version no
                self._add_to_skip_versions(exist_install_file_info.version_no)
                return

        # check if there new version on remote server
        threading.Thread(target=self._version_check,
                         args=(
                             is_process_install,
                             exist_install_file_info,
                         )).start()

    def _load_skip_verions(self, skip_versions_file_path):
        # open and load
        temp = []
        if not os.path.isfile(skip_versions_file_path):
            return temp

        with open(skip_versions_file_path) as json_data:
            temp = json.load(json_data)
        return temp

    def _add_to_skip_versions(self, version_no):
        self._skip_versions.append(version_no)
        skip_versions_file_path = os.path.join(get_executor_path(), 'versions',
                                               'skip_versions.json')
        try:
            with open(skip_versions_file_path, 'w') as outfile:
                json.dump(self._skip_versions, outfile)
        except:
            os.unlink(skip_versions_file_path)
        #save to file

    def _version_check(self, is_process_install, exist_install_file_info):
        new_version_info = self._get_new_version_info()
        if new_version_info:
            if is_process_install:
                return

            if exist_install_file_info and \
                new_version_info.version_no <= exist_install_file_info.version_no:
                return

            if self._skip_versions.__contains__(new_version_info.version_no):
                return

            #inform there is a new version
            self._print_new_version(new_version_info.url)

            if self._is_installed:
                self._download_installer(new_version_info)

    def _get_new_version_info(self):
        # check if has network, do a ping
        has_internet = self._check_internet()
        if not has_internet:
            return None

        tag_name = None
        version_info = None
        # request github get latest version info
        response = requests.get(
            'https://api.github.com/repos/{0}/{1}/releases/latest'.format(
                github_owner, github_repo))
        #convert to json, get the tag_name
        if response.status_code == 200:
            tag_name = json.loads(response.text).get('tag_name')

        if not tag_name:
            return None

        # download the latest.json, contains file info, version, download url
        response = requests.get(
            'https://github.com/{0}/{1}/releases/download/{2}/latest.json'.
            format(github_owner, github_repo, tag_name))
        if response.status_code == 200:
            latest_text = json.loads(response.text)

            latest_version = latest_text.get('version')

            if latest_version <= VERSION:
                return None

            version_info = VersionInfo()
            version_info.name = latest_text.get('name')
            version_info.url = 'https://github.com/{0}/{1}/releases/download/{2}/{3}'.format(
                github_owner, github_repo, tag_name, latest_text.get('url'))
            version_info.version_no = latest_text.get('version')

        return version_info

    def _check_internet(self):
        try:
            url = 'https://navview.blob.core.windows.net/'
            requests.get(url, timeout=1, stream=True)
            return True
        except requests.exceptions.Timeout as err:
            return False

    def _get_exist_install_file_info(self) -> LocalInstallerInfo:
        if self._installed_path and self._is_installed:
            # check if exists installed folder/versions
            installers_path = os.path.join(get_executor_path(), 'versions')
            skip_versions_file_path = os.path.join(installers_path,
                                                   'skip_versions.json')
            if not os.path.isdir(installers_path):
                return None, []

            # list the files, and find the last modified file with name format=installer.{version}.exe
            install_file = self._get_latest_install_file(installers_path)

            skip_versions = self._load_skip_verions(skip_versions_file_path)

            return install_file, skip_versions

        return None, []

    def _get_latest_install_file(self, installers_path) -> LocalInstallerInfo:
        latest_version = ''
        install_files = []
        reg_expression = 'installer.(\S+).exe'

        with os.scandir(installers_path) as it:
            for entry in it:
                if not entry.is_file():
                    continue

                match_group = re.match(reg_expression, entry.name, re.M | re.I)

                if not match_group:
                    continue

                install_files.append((entry.path, match_group[1]))

        if len(install_files) == 0:
            return None

        def extract_version(element):
            return element[1]

        install_files.sort(key=extract_version, reverse=True)
        path, version = install_files[0]

        installer_info = LocalInstallerInfo()
        installer_info.path = path
        installer_info.version_no = version
        return installer_info

    def _run_installer(self, installer_path):
        # Start to install new version
        elevate_path = os.path.join(self._installed_path, 'elevate.exe')
        try:
            subprocess.Popen([installer_path], shell=True)
        except Exception as ex:
            subprocess.Popen([elevate_path, installer_path])
        # kill current process
        os.kill(os.getpid(), signal.SIGTERM)

    def _download_installer(self, version_info: VersionInfo):
        can_download = False
        # save to installed folder/versions
        saved_folder = os.path.join(get_executor_path(), 'versions')
        if not os.path.isdir(saved_folder):
            os.makedirs(saved_folder)

        self._remove_temp_files(saved_folder)

        # create a temp file
        temp_name = 'tmp-{0}'.format(current_milli_time())  # tmp-{timestamp}

        try:
            # download from parsed link
            can_download = self._do_download(version_info.url, temp_name,
                                             saved_folder)
        except Exception as ex:
            print('Download exception:', ex)
            # rename the temp file as a format name
            self._remove_temp_files(saved_folder)
            # TODO: log the exception while downloading

        if can_download:
            # rename the temp file as a format name
            os.replace(
                os.path.join(saved_folder, temp_name),
                os.path.join(saved_folder,
                             'installer.' + version_info.version_no + '.exe'))
        else:
            # remove temp files if there is any exception
            self._remove_temp_files(saved_folder)

    def _do_download(self, url, temp_name, saved_folder):
        chunk_size = 32 * 1024  # save file per 32k buffer data
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
                    #print('\r' + 'File current', size, end=' ')
            end = time.time()
            print_green('[Version] The new version is downloaded')
        else:
            return False

        return True

    def _remove_temp_files(self, from_folder):
        try:
            with os.scandir(from_folder) as it:
                for entry in it:
                    if entry.is_file() and entry.name.startswith('tmp-'):
                        os.unlink(entry.path)
        except Exception as ex:
            # TODO: log the remove exception
            pass

    def _print_new_version(self, url):
        if self._is_installed:
            print_green('[Version] New version is found, downloading from ' +
                        url)
        else:
            print_green(
                '[Version] New version is found, please download the lastest version on https://github.com/Aceinna/python-openimu/releases'
            )

    def _inform_user(self, version_no):
        c = Choice(
            title='New version {0} is prepared, continue to update?'.format(
                version_no),
            options=['Yes', 'No', 'Skip this version'])

        choice = c.get_choice()
        if choice:
            index, _ = choice

        return index
