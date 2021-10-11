# python-openimu

A message communication tool for OpenIMU, OpenRTK and other devices of Aceinna

## Working Environment 
- Windows10: python 3.7
- Mac OS: python 3.7

## Steps

### 1. Start the tool
There are 3 ways to run the tool

#### Prepare
1. Install the dependency library. It is better to create a virtual environment before to do it.

```bash
$ pip install -r requirements.txt
```

2. Install pcap api library(`optional`). Because we try to support INS401 a new device from Aceinna. It would use 100BASE-T1 ethernet, and the data transfer is in low-level of network, so we need help of pcap api. Actually, we integrated `scapy` in our project. The pcap api library is the dependency of `scapy`. If you are using a INS401 device, please also install the library based on your platform.

| Platform | Libraray | Reference |
| - | - | - |
| Windows | `npcap` | https://scapy.readthedocs.io/en/latest/installation.html#windows |
| Ubuntu | `tcpdump` | https://scapy.readthedocs.io/en/latest/installation.html#debian-ubuntu-fedora |
| Mac | `libpcap` | https://scapy.readthedocs.io/en/latest/installation.html#mac-os-x |


#### A. From source code

##### Run
Please use this way if you want to contribute the project.
```bash
$ python main.py
```
#### B. Work as execution file

##### Build
The executable will be generated in `dist` folder.
```bash
$ pyinstaller build.spec
```

##### Run
```bash
$ cd dist
$ ./ans-devices
```

#### C. From pip

##### Install
```bash
$ pip install openimu
```

##### Run
```
$ openimu
```

#### Startup Arguments
You can specify some arguments while run the tool

Arguments:

| Name | Type | Default | Description |
| - | :-: | :-: | - |
| -i, --interface | String | 'default' | Value should be `uart`, `eth`, `100base-t1` |
| -p, --port | Number | '8000' | Value should be an available port |
| --device-type | String | 'auto' | Value should be one of `IMU`, `RTK`, `DMU` |
| -b, --baudrate | String | None | Value should be a valid baudrate. The valid value should be one of `38400`, `57600`, `115200`, `230400`, `460800` |
| -c, --com-port | String | 'auto' | Value should be a COM port |
| --console-log | Boolean | False | Output log on console |
| --debug | Boolean | False | Log debug information |
| --with-data-log | Boolean | False | Contains internal data log (OpenIMU only) |
| -s, --set-user-para | Boolean | False | Set uesr parameters (OpenRTK only) |


### 2. Connect Aceinna device
Link device to your pc or mac. The tool will auto detect the linked device by default.

[More Usage](USAGE.md "More Usage")

## Work Mode
### Default Mode
Normally, python-openimu works as default mode. It will establish a websocket server, then exchange messages through the websocket protocol. And it should work with [aceinna developers site](https://developers.aceinna.com "Aceinna Developers Site"), it allows user to do data monitor, configuration and firmware management.

### Command Line Mode
You can specify the startup argument `--cli` to switch to Command Line Mode. Command Line Mode helps you interact with device directly. And it also supply command to start a websocket server, so that you can use the full features of Default Mode. 

Command Line Mode supports some commands for using, below is a list of commands description,

#### Help
Show help menu. It would show a list of description for all supported commands.
```bash
$ help
```

#### Get Device Info
Show information of connected device.
```bash
$ connect
```

#### Get Parameter (OpenIMU Only)
Retrieve current value of specified parameter.
```bash
$ get param_name
```

#### Set Parameter (OpenIMU Only)
Update the value of specified parameter. The value would be recoverd after device power off.
```bash
$ set param_name param_value
```

#### Save Configuration
Save the configuration into EEPROM. The value would be permanently saved.
```bash
$ save
```

#### Record Data (OpenIMU Only)
Log the device output data in path /data. It is not supported for OpenRTK, because OpenRTK device will automatically log data when it is connected. 
```bash
$ record
```

#### Upgrade Firmware
Upgrade firmware from a specified path. The binary file should match with the device. This is a high risk command.
```bash
$ upgrade path/to/bin
```

#### Start Server
Establish a websocket server.
```bash
$ server_start
```

#### Stop Server
Stop the websocket server. If there is websocket server runing, it has to stop it when you want to use other command.
```bash
$ stop
```

#### Exit
Quit from Command Line Mode
```bash
$ exit
```


## Interface
Aceinna Device could be connected with your PC via UART or LAN. The supported interface is depended on the device type.
| Device Type | Supported Protocols | Description |
| - | - | - |
| DMU | `uart` | |
| OpenIMU | `uart` | |
| OpenRTK | `uart`, `eth` | The startup argument `-i eth` is supported |
| RTK330L | `uart` |  |
| INS401 | `100base-t1` | The startup argument `-i 100base-t1` is supported |


## Parse Tool
There is a log parse tool integrated in. It could parse `OpenRTK`, `RTK330LA`, `IN S401` raw data log from data folder. Assgin `parse` to start it.

### Arguments:

| Name | Type | Default | Description |
| - | :-: | :-: | - |
| -t | String | 'openrtk' | Switch work mode. Value should be one of `openrtk`,`rtkl`,`ins401` |
| -p | String | '.' | Value should be a valid path. It could be the container folder of log files |
| -i | Number | 5 | INS kml rate(hz) |

### Example

Run from source code
```bash
$ python main.py parse
```

Work as execution file
```bash
$ ans-devices parse
```

Run from pip
```bash
$ openimu parse
```

## Changelogs and Release Notes

Please refer to [HISTORY.md](HISTORY.md "Change History")
