import json
import requests
from .configuration import get_config


class AnsPlatformAPI:
    def __init__(self):
        self.access_token = ''
        self.host_url = get_config().ANS_PLATFORM_URL

    def set_access_token(self, token):
        self.access_token = token

    def get_sas_token(self):
        try:
            url = self.host_url + "token/storagesas"
            headers = {'Content-type': 'application/json',
                       'Authorization': self.access_token}
            response = requests.post(url, headers=headers)
            rev = response.json()
            if 'token' in rev:
                return rev['token']
            else:
                return ''
        except Exception as ex:
            print('Exception when get_sas_token:', ex)
            return ''

    def save_backup_restult(self, serial_num, file_name, device_type):
        ''' save backup result
        '''
        body = {
            'data': {
                'sn': serial_num,
                'file': file_name,
                'type': device_type
            }
        }
        try:
            url = self.host_url + "api/userDevices/backup"
            data_json = json.dumps(body)
            headers = {'Content-type': 'application/json',
                       'Authorization': self.access_token}
            response = requests.post(url, data=data_json, headers=headers)
            return response.json()
        except Exception as ex:
            print('Exception when update db:', ex)
