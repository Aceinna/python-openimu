"""
predefined params for openimu
"""
JSON_FILE_NAME = 'openimu.json'

DEFAULT_PRODUCT_NAME = 'OpenIMU300ZI'

def get_openimu_products():
    return {
        'OpenIMU300RI': ['Compass', 'IMU', 'INS', 'Leveler', 'VG_AHRS'],
        'OpenIMU300ZI': ['Compass', 'IMU', 'INS', 'Leveler', 'VG_AHRS'],
        'OpenIMU330BI': ['IMU', 'VG_AHRS'],
        'OpenIMU335RI': ['IMU', 'VG']
    }


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


APP_STR = ['INS', 'VG', 'VG_AHRS', 'Compass', 'Leveler', 'IMU']
