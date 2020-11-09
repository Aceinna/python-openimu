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
            # TODO: use logger
            print('Exception when update db:', ex)

    def log_device_connection(self, sessionId, device_info):
        ''' log device connection to db
        '''
        body = {
            'data':{
                'sessionId': sessionId,
                'device': device_info
            }
        }
        try:
            url = self.host_url + "api/deviceConnections/log"
            data_json = json.dumps(body)
            headers = {'Content-type': 'application/json',
                       'Authorization': self.access_token}
            response = requests.post(url, data=data_json, headers=headers)
        except Exception as ex:
            # TODO: use logger
            print('Exception when log device connection to db:', ex)

    def save_record_log(self, data):
        ''' save record log
        '''
        try:
            url = self.host_url + "api/recordLogs/post"
            data_json = json.dumps(data)
            headers = {'Content-type': 'application/json',
                       'Authorization': self.access_token}
            response = requests.post(url, data=data_json, headers=headers)
            return True if 'success' in response.json() else False
        except Exception as ex:
            # TODO: use logger
            print('Exception when save record log:', ex)
