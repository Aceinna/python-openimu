# Work as executable
```bash
$ `./ans-device [parameters]`
```

parameters:

| Name | Type | Default | Description |
| - | :-: | :-: | - |
| --cli | Boolean | False | Work as command line mode |
| -p, --port | Number | '8000' | Value should be an available port |
| --device-type | String | 'auto' | Value should be `IMU`, `RTK`, `DMU` |
| -b, --baudrate | String | None | Value should be a valid baudrate. The valid value should be one of `38400`, `57600`, `115200`, `230400`, `460800` |
| -c, --com-port | String | 'auto' | Value should be a COM port |
| --console-log | Boolean | False | Output log on console |
| --debug | Boolean | False | Log debug information |
| --with-data-log | Boolean | False | Contains internal data log (OpenIMU only) |
| -s, --set-user-para | Boolean | False | Set uesr parameters (OpenRTK only) |
| -n, --ntrip-client | Boolean | False | Enable ntrip client (OpenRTK only) |
| -l, --protocol | String | 'uart' | Value should be `uart`, `lan`. Depends on device type |

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
from aceinna.bootstrap import Default

app = Default(
    device_type='openimu',
    com_port='COM1',
    port=8001,
    baudrate=115200,
    debug=True)
app.listen()
```


# Use source code
Invoke sdk and start a webserver `python main.py`