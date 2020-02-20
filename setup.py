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

install_requires = [
    "pyserial",
    "pathlib",
    "psutil",
    "azure-storage-blob==2.1.0",
    "tornado"
]

setup(
    name="openimu",
    version="1.0.5",
    author="Aceinna OpenIMU",
    author_email="info@aceinna.com",
    description="Aceinna Open Source Python",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Aceinna/python-openimu",
    license="Apache 2.0",
    python_requires=">=2.7, !=3.0.*, !=3.1.*",
    install_requires=install_requires,
    packages=find_packages(),
    package_data={
        'openimu': ['app_config/*/*.json']
    },
    classifiers=[
        "Environment :: Console",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
    entry_points={
        "console_scripts": [
            "openimu = openimu.__main__:main",
        ]
    }
)
