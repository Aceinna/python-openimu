"""
Global variables, imu, cli etc. are declared in the file
Created on 07-19-2018
"""
import sys

if sys.version_info[0] > 2:
    from openimu.openimu import OpenIMU
else:
    from openimu import OpenIMU

imu = OpenIMU(ws=False)
