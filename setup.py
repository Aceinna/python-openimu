# Copyright (C) 2018 Aceinna Navigation System Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS IS"
# BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing
# permissions and limitations under the License.
import json
import os
from setuptools import find_packages, setup
from src.aceinna import (PACKAGE_NAME, VERSION)


def load_json_file_path_under_setting_folder():
    json_file_paths = []
    setting_root_path = os.path.join(os.getcwd(), 'src', 'aceinna', 'setting')
    for root, dirs, files in os.walk(setting_root_path):
        json_file = next(
            (item for item in files if item.__contains__('.json')), None)
        if not json_file:
            continue

        json_file_path = os.path.join(root.replace(
            setting_root_path, 'setting'), json_file)
        json_file_paths.append(json_file_path)

    return json_file_paths


def load_libraries():
    file_paths = []
    setting_root_path = os.path.join(os.getcwd(), 'src', 'aceinna', 'libs')
    for root, dirs, files in os.walk(setting_root_path):
        for item in files:
            lib_file = item if item.__contains__(
                '.dll') or item.__contains__('.so') else None
            if not lib_file:
                continue

            file_path = os.path.join(root.replace(
                setting_root_path, 'libs'), lib_file)
            file_paths.append(file_path)

    return file_paths


def load_resources():
    resources = []
    json_files = load_json_file_path_under_setting_folder()
    lib_files = load_libraries()
    resources.extend(json_files)
    resources.extend(lib_files)
    return resources


PACKAGE_DESCRIPTION = "Aceinna Navigation System Open Devices Library"

INSTALL_REQUIRES = [
    "pyserial",
    "pathlib",
    "psutil",
    "azure-storage-blob==2.1.0",
    "tornado"
]

setup(
    name=PACKAGE_NAME,
    version=VERSION,
    author="Aceinna, Inc",
    author_email="info@aceinna.com",
    description=PACKAGE_DESCRIPTION,
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Aceinna/python-openimu",
    license="Apache 2.0",
    python_requires=">=2.7, !=3.0.*, !=3.1.*",
    install_requires=INSTALL_REQUIRES,
    packages=find_packages("src", exclude=['test', 'tests']),
    package_dir={"": "src"},
    package_data={
        'aceinna': load_resources()
    },
    classifiers=[
        "Environment :: Console",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
    entry_points={
        "console_scripts": [
            "openimu = aceinna.executor:from_command_line",
        ]
    }
)
