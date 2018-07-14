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
        if user:
            self.user = user
            if self.user['fileName'] == '':
                self.user['fileName'] = self.name
            else:
                self.user['fileName'] += '.csv'
            self.file = open('data/' + self.user['fileName'], 'w')
        else:
            self.file = open('data/' + self.name, 'w')
        self.first_row = 0
        # decode converts out of byte array
        self.ws = imu.ws
        self.sn = imu.device_id.split(" ")[0]
        self.pn = imu.device_id.split(" ")[1]
        self.device_id = imu.device_id
        self.odr_setting = imu.odr_setting
        self.packet_type = imu.packet_type
        self.imu_properties = imu.imu_properties

    # Parse the data, read in from the unit, and generate a data file using
    #   the json properties file to create a header and specify the precision
    #   of the data in the resulting data file.
    def log(self, imu, data):
        #
        output_packet = next((x for x in imu.imu_properties['userMessages']['outputPackets'] if x['name'] == imu.packet_type), None)

        '''Write row of CSV file based on data received.  Uses dictionary keys for column titles
        '''
        if not self.first_row:
            self.first_row = 1

            # Loop through each item in the data dictionary and create a header from the json
            #   properties that correspond to the items in the dictionary
            labels = ''
            keyIdx = -1
            for key in data:
                keyIdx= keyIdx + 1
                '''dataStr = output_packet['payload'][keyIdx]['name'] + \
                          ' [' + \
                          output_packet['payload'][keyIdx]['unit'] + \
                          ']'''
                dataStr = output_packet['payload'][keyIdx]['name']
                labels = labels + '{0:s},'.format(dataStr)
            
            # Remove the comma at the end of the string and append a new-line character
            labels = labels[:-1]
            header = labels + '\n'
        else:
            self.first_row += 1
            header = ''


        # Loop through the items in the data dictionary and append to an output string
        #   (with precision based on the data type defined in the json properties file)
        str = ''
        keyIdx = -1
        for key in data:
            keyIdx= keyIdx + 1
            outputPcktType = output_packet['payload'][keyIdx]['type']

            if outputPcktType == 'uint32' or outputPcktType == 'int32' or \
               outputPcktType == 'uint16' or outputPcktType == 'int16' or \
               outputPcktType == 'uint64' or outputPcktType == 'int64':
                # integers and unsigned integers
                str += '{0:d},'.format(data[key])
            elif outputPcktType == 'double':
                # double
                str += '{0:15.12f},'.format(data[key])
            elif outputPcktType == 'float':
                # print(3) #key + str(2))
                str += '{0:12.8f},'.format(data[key])
            elif outputPcktType == 'uint8':
                # byte
                str += '{0:d},'.format(data[key])
            elif outputPcktType == 'uchar' or outputPcktType == 'char':
                # character
                str += '{:},'.format(data[key])
            else:
                # unknown
                print(0)
                str += '{0:3.5f},'.format(data[key])

        # 
        str = str[:-1]
        str = str + '\n'
        self.file.write(header+str)

    def write_to_azure(self):
        # check for internet 
        # if not self.internet_on(): 
        #    return False

        # record file to cloud
        # f = open("data/" + self.name,"r")
        f = open("data/" + self.user['fileName'], "r")
        text = f.read()
        try: 
            self.append_blob_service = AppendBlobService(account_name='navview', account_key='+roYuNmQbtLvq2Tn227ELmb6s1hzavh0qVQwhLORkUpM0DN7gxFc4j+DF/rEla1EsTN2goHEA1J92moOM/lfxg==', protocol='http')
            self.append_blob_service.create_blob(container_name='data', blob_name=self.name,  content_settings=ContentSettings(content_type='text/plain'))
            self.append_blob_service.append_blob_from_text('data',self.name, text)
        except:
            # Try again!
            print('trying to write again due to exception')
            self.append_blob_service = AppendBlobService(account_name='navview', account_key='+roYuNmQbtLvq2Tn227ELmb6s1hzavh0qVQwhLORkUpM0DN7gxFc4j+DF/rEla1EsTN2goHEA1J92moOM/lfxg==', protocol='http')
            self.append_blob_service.create_blob(container_name='data', blob_name=self.name,  content_settings=ContentSettings(content_type='text/plain'))
            self.append_blob_service.append_blob_from_text('data',self.name, text)


        # record record to ansplatform
        self.record_to_ansplatform()
        
        
    def record_to_ansplatform(self):
        data = { "pn" : self.pn, "sn": self.sn, "fileName" : self.user['fileName'],  "url" : self.name, "imuProperties" : json.dumps(self.imu_properties),
                 "sampleRate" : self.odr_setting, "packetType" : self.packet_type, "userId" : self.user['id'] }
        url = "https://api.aceinna.com/api/datafiles/replaceOrCreate"
        data_json = json.dumps(data)
        headers = {'Content-type': 'application/json', 'Authorization' : self.user['access_token'] }
        response = requests.post(url, data=data_json, headers=headers)
        response = response.json()
       
        # clean up
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
        if self.ws:
            self.file.close()
            threading.Thread(target=self.write_to_azure).start()
        else:
            self.file.close()
