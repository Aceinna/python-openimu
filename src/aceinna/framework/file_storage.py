# -*- coding: utf-8 -*
import sys
import os
import time
import datetime
import json
import threading
import requests
from azure.storage.blob import AppendBlobService
from azure.storage.blob import ContentSettings
from .utils import resource
from .configuration import get_config
from .ans_platform_api import AnsPlatformAPI
from .context import APP_CONTEXT


class FileLoger():
    def __init__(self, device_properties):
        '''Initialize and create a CSV file
        '''
        start_time = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        self.device_properties = device_properties
        if not self.device_properties:
            print('No properties found')
            os._exit(1)

        self.root_folder = os.path.join(resource.get_executor_path(), r'data')
        if not os.path.exists(self.root_folder):
            os.mkdir(self.root_folder)
        self.output_packets = self.device_properties['userMessages']['outputPackets']
        self.log_file_rows = {}
        self.log_file_names = {}
        self.log_files_obj = {}
        self.log_files = {}
        self.user_file_name = ''  # the prefix of log file name.
        self.msgs_need_to_log = []
        self.ws = False
        # azure app.
        self.user_id = ''
        self.file_name = ''
        self.sas_token = ''
        self.db_user_access_token = ''
        # 'http://40.118.233.18:3000/'  # TODO: set a host url
        self.host_url = get_config().ANS_PLATFORM_URL

        #
        self.threads = []  # thread of receiver and paser
        self.exit_thread = False  # flag of exit threads
        self.exit_lock = threading.Lock()  # lock of exit_thread
        self.data_dict = {}  # data container
        self.data_lock = threading.Lock()  # lock of data_queue

        self.device_log_info = None
        self.ans_platform = AnsPlatformAPI()

    def start_user_log(self, file_name='', ws=False):
        '''
        start log.
        return:
                0: OK
                1: exception that has started logging already.
                2: other exception.
        '''
        try:
            if len(self.log_file_rows) > 0:
                return 1  # has started logging already.

            self.ws = ws
            self.exit_thread = False
            self.user_file_name = file_name
            start_time = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            current_path = os.path.join(self.root_folder, start_time)
            if not os.path.exists(current_path):
                os.mkdir(current_path)

            for packet in self.output_packets:
                # if 1 == packet['save2file']:
                has_save2file = packet.__contains__('save2file')
                save2file = 1
                if has_save2file:
                    save2file = packet['save2file']

                if save2file == 1:
                    self.msgs_need_to_log.append(packet['name'])

                self.log_file_rows[packet['name']] = 0
                if self.user_file_name == '':
                    self.log_file_names[packet['name']
                                        ] = packet['name'] + '.csv'
                else:
                    self.log_file_names[packet['name']] = self.user_file_name + \
                        '_' + packet['name'] + '.csv'
                self.log_files[packet['name']
                               ] = self.log_file_names[packet['name']]

                self.log_files_obj[packet['name']] = open(
                    current_path + '/' + self.log_file_names[packet['name']], 'w')

            if self.ws:
                self.get_sas_token()
                self.data_dict.clear()
                for i, (k, v) in enumerate(self.log_files.items()):  # k:pack type  v:log file name
                    self.data_dict[v] = ''
                    threading.Thread(target=self.upload_azure,
                                     args=(k, v)).start()
            return 0
        except Exception as e:
            print('Exception! File:[{0}], Line:[{1}]. Exception:{2}'.format(
                __file__, sys._getframe().f_lineno, e))
            return 2

    def stop_user_log(self):
        '''
        stop log.
        return:
                0: OK
                1: exception that driver hasn't started logging files yet.
                2: other exception.
        '''
        rev = 0
        try:
            if len(self.log_file_rows) == 0:
                return 1  # driver hasn't started logging files yet.
            for i, (k, v) in enumerate(self.log_files_obj.items()):
                v.close()
            self.log_file_rows.clear()
            self.log_file_names.clear()
            self.log_files_obj.clear()
            rev = 0
        except Exception as e:
            print(e)
            rev = 2

        if self.ws:
            time.sleep(1)
            self.exit_lock.acquire()
            self.exit_thread = True
            self.exit_lock.release()
            self.ws = False

        return rev

    def upload_azure(self, packet_type, log_file_name):
        if self.db_user_access_token == '' or self.sas_token == '':
            print(
                "Error: Can not upload log to azure since token is empty! Please check the network.")

        print(datetime.datetime.now().strftime(
            '%Y_%m_%d_%H_%M_%S:'), log_file_name, ' start.')

        config = get_config()
        account_name = config.AZURE_STORAGE_ACCOUNT
        container_name = config.AZURE_STORAGE_DATA_CONTAINER
        url_name = datetime.datetime.now().strftime(
            '%Y_%m_%d_%H_%M_%S') + '-' + self.user_id + '-' + log_file_name
        bcreate_blob_ok = False

        error_connection = 'ConnectionError'
        error_authorization = 'AuthenticationFailed'

        while True:
            # get data from data_dict.
            self.data_lock.acquire()
            text = self.data_dict[log_file_name]
            self.data_dict[log_file_name] = ''
            self.data_lock.release()

            # check if user stop logging data.
            self.exit_lock.acquire()
            if self.exit_thread:
                # check for internet and text
                if text == '':
                    self.exit_lock.release()
                    break
                else:
                    pass
            self.exit_lock.release()

            # let CPU have a break.
            if text == '':
                time.sleep(1)
                continue

            # create blob on azure
            if not bcreate_blob_ok:
                try:
                    self.append_blob_service = AppendBlobService(account_name=account_name,
                                                                 sas_token=self.sas_token,
                                                                 protocol='http')
                    self.append_blob_service.create_blob(container_name=container_name, blob_name=url_name,
                                                         content_settings=ContentSettings(content_type='text/plain'))
                    bcreate_blob_ok = True
                    threading.Thread(target=self.save_to_db_task, args=(
                        packet_type, log_file_name, url_name)).start()
                except Exception as e:
                    # print('Exception when create_blob:', type(e), e)
                    if error_connection in str(e):
                        pass
                    elif error_authorization in str(e):
                        self.get_sas_token()
                        self.append_blob_service = AppendBlobService(account_name=account_name,
                                                                     sas_token=self.sas_token,
                                                                     protocol='http')
                    print('Retry to create_blob again...')
                    continue

            # append blob on azure
            try:
                # self.append_blob_service.append_blob_from_text(countainerName, fileName, text, progress_callback=self.upload_callback)
                self.append_blob_service.append_blob_from_text(
                    container_name, url_name, text)
            except Exception as e:
                # print('Exception when append_blob:', type(e), e)
                if error_connection in str(e):
                    pass
                elif error_authorization in str(e):
                    self.get_sas_token()
                    self.append_blob_service = AppendBlobService(account_name=account_name,
                                                                 sas_token=self.sas_token,
                                                                 protocol='http')
                    # if append blob failed, do not drop 'text', but push 'text' to data_dict and re-append next time.
                    self.data_lock.acquire()
                    self.data_dict[log_file_name] = text + \
                        self.data_dict[log_file_name]
                    self.data_lock.release()

            time.sleep(5)

        if bcreate_blob_ok:
            # if not self.save_to_ans_platform(packet_type, log_file_name):
            #     print('save_to_ans_platform failed.')
            print(datetime.datetime.now().strftime(
                '%Y_%m_%d_%H_%M_%S:'), log_file_name, ' done.')

    def save_to_db_task(self, packet_type, file_name, url_name):
        if not self.save_to_ans_platform(packet_type, file_name, url_name):
            print('save_to_ans_platform failed.')

    def append(self, packet_type, packet):
        if len(self.log_file_rows) == 0:  # if hasn't started logging.
            return

        if packet_type in self.msgs_need_to_log:
            self.log(packet_type, packet)

    def get_log_file_names(self):
        return self.log_file_names.copy()

    def log(self, packet_type, data):
        ''' Parse the data, read in from the unit, and generate a data file using
            the json properties file to create a header and specify the precision
            of the data in the resulting data file.
        '''
        output_packet = next(
            (x for x in self.output_packets if x['name'] == packet_type), None)

        fields = [field['name'] for field in output_packet['payload']]
        '''Write row of CSV file based on data received.  Uses dictionary keys for column titles
        '''
        if self.log_file_rows[packet_type] == 0:
            # Loop through each item in the data dictionary and create a header from the json
            #   properties that correspond to the items in the dictionary
            labels = ''
            # for key in data:
            for i, (k, v) in enumerate(data.items()):
                '''dataStr = output_packet['payload'][i]['name'] + \
                          ' [' + \
                          output_packet['payload'][i]['unit'] + \
                          ']'''
                if not fields.__contains__(k):
                    continue
                data_str = output_packet['payload'][i]['name']
                unit_str = output_packet['payload'][i]['unit']
                if unit_str == '':
                    labels = labels + '{0:s},'.format(data_str)
                else:
                    labels = labels + \
                        '{0:s} ({1:s}),'.format(data_str, unit_str)

            # Remove the comma at the end of the string and append a new-line character
            labels = labels[:-1]
            header = labels + '\n'
        else:
            header = ''

        self.log_file_rows[packet_type] += 1

        # Loop through the items in the data dictionary and append to an output string
        #   (with precision based on the data type defined in the json properties file)
        str = ''
        for i, (k, v) in enumerate(data.items()):
            if not fields.__contains__(k):
                continue
            output_packet_type = output_packet['payload'][i]['type']

            if output_packet['payload'][i].__contains__('scaling'):
                str += '{0},'.format(v)
            else:
                if output_packet_type == 'uint32' or output_packet_type == 'int32' or \
                        output_packet_type == 'uint16' or output_packet_type == 'int16' or \
                        output_packet_type == 'uint64' or output_packet_type == 'int64':
                    # integers and unsigned integers
                    str += '{0:d},'.format(v)
                elif output_packet_type == 'double':
                    # double
                    str += '{0:0.8f},'.format(v)  # 15.12
                elif output_packet_type == 'float':
                    str += '{0:0.4f},'.format(v)  # 12.8
                elif output_packet_type == 'uint8':
                    # byte
                    str += '{0:d},'.format(v)
                elif output_packet_type == 'uchar' or output_packet_type == 'char' or output_packet_type == 'string':
                    # character
                    str += '{:},'.format(v)
                else:
                    # unknown
                    str += '{0:3.5f},'.format(v)
        #
        str = header + str[:-1] + '\n'

        try:
            self.log_files_obj[packet_type].write(str)
            self.log_files_obj[packet_type].flush()
        except ValueError:
            APP_CONTEXT.get_logger().logger.error(
                'I/O Exception, file may be closed before using')
        except Exception as ex:
            APP_CONTEXT.get_logger().logger.error(ex)

        if self.ws:
            self.data_lock.acquire()
            self.data_dict[self.log_files[packet_type]
                           ] = self.data_dict[self.log_files[packet_type]] + str
            self.data_lock.release()

    def set_info(self, info):
        self.device_log_info = info
        pass

    def set_user_id(self, user_id):
        self.user_id = user_id
        if not isinstance(self.user_id, str):
            self.user_id = str(self.user_id)

    def set_user_access_token(self, access_token):
        self.db_user_access_token = access_token

    def get_sas_token(self):
        try:
            self.ans_platform.set_access_token(self.db_user_access_token)
            self.sas_token = self.ans_platform.get_sas_token()
        except Exception as e:
            self.sas_token = ''
            print('Exception when get_sas_token:', e)

    def save_to_ans_platform(self, packet_type, file_name, url_name):
        ''' Upload CSV related information to the database.
        '''
        if not self.device_log_info:
            return False

        try:
            self.device_log_info['fileName'] = file_name
            self.device_log_info['url'] = url_name
            self.device_log_info['userId'] = self.user_id
            self.device_log_info['logInfo']['packetType'] = packet_type
            data = self.device_log_info

            # data = {
            #     "type": self.device_log_info['type'],
            #     "model": self.device_log_info['name'],
            #     "fileName": file_name,
            #     "url": file_name,
            #     "userId": self.user_id,
            #     "logInfo": {
            #             "pn": self.device_log_info['pn'],
            #             "sn": self.device_log_info['sn'],
            #             "packetType": packet_type,
            #             "insProperties": json.dumps(self.device_properties)
            #     }
            # }

            self.ans_platform.set_access_token(self.db_user_access_token)
            return self.ans_platform.save_record_log(data)
        except Exception as e:
            print('Exception when update db:', e)

    def internet_on(self):
        try:
            url = 'https://navview.blob.core.windows.net/'
            if sys.version_info[0] > 2:
                import urllib.request
                response = urllib.request.urlopen(url, timeout=1)
            # print(response.read())
            return True
        except Exception as err:
            return False
