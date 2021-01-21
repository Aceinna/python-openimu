"""
predefined params for openrtk
"""
JSON_FILE_NAME = 'openrtk.json'


def get_openrtk_products():
    return {
        'OpenRTK330L': ['INS', 'RAWDATA', 'RTK'],
        'RTK330L': ['RTK_INS'],
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


APP_STR = ['INS', 'RAWDATA', 'RTK', 'RTK_INS']
