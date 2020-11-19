# Work as command
start cli: `./ans-device`

parameters:

| Name | Type | Default | Description |
| - | :-: | :-: | - |
| -p, --port | Number | '8000' | Value should be an available port |
| --device-type | String | 'auto' | Value should be `IMU`, `RTK` |
| -b, --baudrate | String | None | Value should be baudrate |
| -c, --com-port | String | 'auto' | Value should be a COM port |
| --console-log | Boolean | False | Output log on console |
| --debug | Boolean | False | Log debug information |
| --with-data-log | Boolean | False | Contains internal data log (OpenIMU only) |
| -r, --with-raw-log | Boolean | False | Contains raw data log (OpenRTK only) |
| -s, --set-user-para | Boolean | False | Set uesr parameters (OpenRTK only) |
| -n, --ntrip-client | Boolean | False | Enable ntrip client (OpenRTK only) |
| --cli | Boolean | False | Work as command line mode |

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
Invoke sdk and start a webserver `python main.py`