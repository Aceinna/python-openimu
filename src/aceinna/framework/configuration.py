from .utils.resource import is_dev_mode
from .utils.helper import dict_to_object

DEV_CONFIG = dict_to_object({
    'ANS_PLATFORM_URL': 'http://localhost:3000/',
    'AZURE_STORAGE_ACCOUNT': 'navview',
    'AZURE_STORAGE_BACKUP_CONTAINER': 'testing',
    'AZURE_STORAGE_DATA_CONTAINER': 'data-1000',
    'AZURE_STORAGE_APPS_CONTAINER': 'apps'
})

PROD_CONFIG = dict_to_object({
    'ANS_PLATFORM_URL': 'https://api.aceinna.com/',
    'AZURE_STORAGE_ACCOUNT': 'navview',
    'AZURE_STORAGE_BACKUP_CONTAINER': 'backup',
    'AZURE_STORAGE_DATA_CONTAINER': 'data',
    'AZURE_STORAGE_APPS_CONTAINER': 'apps'
})


def get_config():
    '''
    Get configuration by dev mode
    '''
    if is_dev_mode():
        return DEV_CONFIG

    return PROD_CONFIG
