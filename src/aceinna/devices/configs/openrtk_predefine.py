"""
predefined params for openrtk
"""


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


def get_configuratin_file_mapping():
    return {
        'OpenRTK330L': 'openrtk.json',
        'RTK330L': 'RTK330L.json',
    }


APP_STR = ['RAWDATA', 'RTK', 'RTK_INS']
