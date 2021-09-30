"""
predefined params for openrtk
"""


def get_openrtk_products():
    return {
        'OpenRTK330L': ['RTK_INS'],
        'RTK330L': ['RTK_INS'],
        'INS401':['RTK_INS']
    }


def get_app_names():
    '''
    define openimu app type
    '''
    app_names = ['RTK_INS']
    return app_names


def get_configuratin_file_mapping():
    return {
        'OpenRTK330L': 'openrtk.json',
        'RTK330L': 'RTK330L.json',
        'INS401':'ins401.json'
    }


APP_STR = ['RTK_INS']
