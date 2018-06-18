import time
import datetime
import json
import requests
import threading

# need to find something python3 compatible  
# import urllib2

from azure.storage.blob import AppendBlobService
from azure.storage.blob import ContentSettings

class OpenIMULog:
    
    def __init__(self, imu, user = False):
        '''Initialize and create a CSV file
        '''
        self.name = 'data-' + datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S') + '.csv'
        self.file = open('data/' + self.name, 'w')
        self.first_row = 0
        if user:
            self.user = user
            if self.user['fileName'] == '':
                self.user['fileName'] = self.name
        # decode converts out of byte array
        self.sn = imu.device_id.split(" ")[0]
        self.pn = imu.device_id.split(" ")[1]
        self.device_id = imu.device_id
        self.odr_setting = imu.odr_setting
        self.packet_type = imu.packet_type
        self.imu_properties = imu.imu_properties
        self.sample_rate = self.odr_setting

    def log(self, data, odr_setting): 
        '''Write row of CSV file based on data received.  Uses dictionary keys for column titles
        '''
        if not self.first_row:
            self.first_row = 1
            labels = ''.join('{0:s},'.format(key) for key in data)
            labels = labels[:-1]
            header = labels + '\n'
        else:
            self.first_row += 1
            header = ''
        
        str = ''
        for key in data:
            # TODO update this to use json file to determine formatting
            if key == 'BITstatus' or key == 'GPSITOW' or key == 'counter' or key == 'timeITOW':
                str += '{0:d},'.format(data[key])
            else:
                str += '{0:3.5f},'.format(data[key])
        str = str[:-1]
        str = str + '\n'
        self.file.write(header+str)

    def write_to_azure(self):
        # check for internet 
        # if not self.internet_on(): 
        #    return False

        # record file to cloud
        self.append_blob_service = AppendBlobService(account_name='navview', account_key='+roYuNmQbtLvq2Tn227ELmb6s1hzavh0qVQwhLORkUpM0DN7gxFc4j+DF/rEla1EsTN2goHEA1J92moOM/lfxg==', protocol='http')
        self.append_blob_service.create_blob(container_name='data', blob_name=self.name,  content_settings=ContentSettings(content_type='text/plain'))
        f = open("data/" + self.name,"r")
        self.append_blob_service.append_blob_from_text('data',self.name, f.read())

        # TODO: check if success

        # record record to ansplatform
        self.record_to_ansplatform()


    def record_to_ansplatform(self):
        data = { "pn" : self.pn, "sn": self.sn, "fileName" : self.user['fileName'],  "url" : self.name, "imuProperties" : json.dumps(self.imu_properties),
                 "sampleRate" : self.sample_rate, "packetType" : self.packet_type, "userId" : self.user['id'] }
        url = "https://ans-platform.azurewebsites.net/api/datafiles/replaceOrCreate"
        data_json = json.dumps(data)
        headers = {'Content-type': 'application/json', 'Authorization' : self.user['access_token'] }
        response = requests.post(url, data=data_json, headers=headers)
        response = response.json()
        print(response)
       
        # clean up
        self.file.close()
        self.name = ''

        return  #ends thread

    def internet_on(self):
        try:
            urllib2.urlopen('https://ans-platform.azurewebsites.net', timeout=1)
            return True
        except urllib2.URLError as err: 
            return False

    def close(self):
        time.sleep(0.1)
        if self.imu.ws:
            threading.Thread(target=self.write_to_azure).start()
        else:
            self.file.close()
