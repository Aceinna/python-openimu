"""
predefined params for openrtk
"""
JSON_FILE_NAME = 'openrtk.json'


def get_openrtk_products():
    return {
        'OpenRTK330L': ['RTK_INS', 'RAWDATA', 'RTK'],
        'RTK330L': ['RTK_INS'],
    }


def get_app_names():
    '''
    define openimu app type
    '''
    app_names = ['RTK_INS',
                 'RAWDATA',
                 'RTK',
                 ]
    return app_names


APP_STR = ['RAWDATA', 'RTK', 'RTK_INS']
