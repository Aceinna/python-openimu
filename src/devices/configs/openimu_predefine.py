"""
predefined params for openimu
"""


def get_app_names():
    '''
    define openimu app type
    '''
    app_names = ['Compass',
                 'IMU',
                 'INS',
                 'Leveler',
                 'OpenIMU',
                 'VG_AHRS'
                 ]
    return app_names


APP_URL_BASE = 'https://raw.githubusercontent.com/Aceinna/python-openimu/bugfix/app_config'
APP_STR = ['INS', 'VG_AHRS', 'IMU', 'Compass', 'Leveler']
