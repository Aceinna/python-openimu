import requests
import json
from urllib import parse
import sys

def can_cfg_set(config_file):
    can_fs = open(config_file, 'r')
    data = json.load(can_fs)    

    HEADERS = {'Content-Type': 'application/x-www-form-urlencoded', "enctype": "pplication/x-www-form-urlencoded"}
    url = "http://openrtk/cancfg.cgi"
    data["gear"] = json.dumps(data["gear"])
    data["canMesg"] = json.dumps(data["canMesg"])
    data = parse.urlencode(data).replace('+', '')
    content = requests.post(url=url, headers=HEADERS, data=data)
    if content.status_code == 200:
        return True
    return False