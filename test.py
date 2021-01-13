import requests
import os
import sys
import time
import re

path = r'C:\Program Files (x86)\Aceinna\Driver\versions'


def internet_on():
    try:
        url = 'https://navview.blob.core.windows.net/'
        requests.get(url, timeout=1, stream=True)
        return True
    except requests.exceptions.Timeout as err:
        return False


print(internet_on())

# chunk_size = 1024
# response = requests.get(
#     url=
#     'https://github.com/baweiji/python-openimu/releases/download/v2.2.5/ans-device-setup1.0.0.exe',
#     stream=True)
# start = time.time()
# size = 0
# content_size = int(response.headers['content-length'])  # 下载文件总大小
# try:
#     if response.status_code == 200:  #判断是否响应成功
#         print('Start download,[File size]:{size:.2f} MB'.format(
#             size=content_size / chunk_size / 1024))  #开始下载，显示下载文件大小
#         filepath = os.path.join(os.getcwd(), 'installer.exe')
#         with open(filepath, 'wb') as file:  #显示进度条
#             for data in response.iter_content(chunk_size=4096):
#                 file.write(data)
#                 size += len(data)
#                 print('\r' + '[下载进度]:%s%.2f%%' %
#                       ('>' * int(size * 50 / content_size),
#                        float(size / content_size * 100)),
#                       end=' ')
#     end = time.time()  #下载结束时间
#     print('Download completed!,times: %.2f秒' % (end - start))  #输出下载用时时间
# except Exception as ex:
#     print(ex)
#     print('Error!')
