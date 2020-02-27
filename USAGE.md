# Work as command
start cli: `ans-devices`

parameters:

| Name | Type | Default | Description |
| - | :-: | :-: | - |
| --device-type | String | 'auto' | Value should be `IMU`, `RTK` |
| --com-port | String | 'auto' | Value should be a COM port |
| --baudrate | String | None | Value should be baudrate |
| --debug | Boolean | False | If log debug information |


# Work as sdk
Detect device
```python
import time
from aceinna.tools import Detector

def on_find_device(device):
    # prepare to use
    device.setup(None)
    # get device info
    device.get_device_info()
    # start to log
    device.start_data_log()
    time.sleep(10)
    # stop to log
    device.stop_data_log()

detector = Detector(
    device_type='IMU',
    com_port='COM1',
    baudrate=115200)
detector.find(on_find_device)
```

Host in webserver 
```python
from aceinna.bootstrap import Webserver

app = Webserver(
    device_type='openimu',
    com_port='COM1',
    port=8001,
    baudrate=115200,
    debug=True)
app.listen()
```


# Use source code
Invoke sdk and start a webserver `python ./src/main.py`