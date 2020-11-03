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

from setuptools import find_packages, setup
from src.aceinna import (PACKAGE_NAME, VERSION)

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
        'aceinna': ['setting/openrtk/*/*.json', 'setting/openimu/*/*.json', 'setting/dmu/*.json']
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
