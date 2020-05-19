"""
predefined params for openimu
"""
JSON_FILE_NAME = 'openimu.json'


def get_app_names():
    '''
    define openimu app type
    '''
    app_names = ['Compass',
                 'IMU',
                 'INS',
                 'Leveler',
                 'OpenIMU',
                 'VG',
                 'VG_AHRS',
                 ]
    return app_names


APP_STR = ['INS', 'VG', 'VG_AHRS', 'Compass', 'Leveler', 'IMU', 'OpenIMU']
