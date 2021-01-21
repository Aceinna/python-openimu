"""
predefined params for openrtk
"""
JSON_FILE_NAME = 'openrtk.json'


def get_openrtk_products():
    return {
        'OpenIMU330LI': ['INS', 'RAWDATA', 'RTK'],
        'RTK330LA': ['INS', 'RAWDATA', 'RTK'],
    }


def get_app_names():
    '''
    define openimu app type
    '''
    app_names = ['INS',
                 'RAWDATA',
                 'RTK',
                 ]
    return app_names


APP_STR = ['INS', 'RAWDATA', 'RTK']
