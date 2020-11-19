# python-openimu

Python driver for OpenIMU and OpenRTK

## Working Environment 
- Windows10: python2.7 and python 3.7
- Mac OS: python2.7 and python 3.7

## Steps

### 1. Start the tool
There are 2 ways to run the tool

#### Prepare
Install the dependency library. It is better to create a virtual environments before to do it.

python 3.x
```
pip install -r requirements.txt
```

python 2.x
```
pip install -r requirements-2.x.txt
```

#### A. From source code

##### Run
Please use this way if you want to develop the project.
```
python main.py
```
#### B. Work as execution file

##### Build
It will be generated in `dist` folder.
```
pyinstaller build.spec
```

##### Run it
```
./ans-devices
```

##### Startup Arguments
You can specify some arguments while run the tool

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

### 2. Connect Aceinna device
Link device to your pc or mac. And the tool will auto detect the linked device.

[More Usage](USAGE.md "More Usage")

## Work Mode
Normally, python-openimu works as Web mode. It will auto start a websocket server after device is detected. And it can works with [acinna developers site](https://developers.aceinna.com "Aceinna Developers Site") to do monitor and set configuration of connected device.

You can specify the startup parameter `--cli` to switch to Command Line Mode. Command Line Mode helps you to interact with device without open the brower. 

Commnad List:
| Name  | Description |
| - | - |
| help | CLI help menu |
| exit | Exit Command Line Mode |
| run | Operations defined by users |
| save | Save thee configuration into EEPROM |
| connect | Show information of connected device |
| upgrade | Upgrade firmware |
| record | Record output data of device |
| stop | Stop recording outputs |
| server_start | Start server thread and must use `exit` command to quit |
| get | Read the current configuration and output data |
| set | Write parameters to device |


## Changelogs and Release Notes

[HISTORY.md](HISTORY.md "Change History")
