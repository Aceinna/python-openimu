# python-ans-devices
Python driver for OpenIMU and OpenRTK

## Working Environment 
- Windows10: python2.7 and python 3.7
- Mac OS: python2.7 and python 3.7

## Steps

### 1. Start the tool
There are 2 ways to run the tool
- A. From source code
#### Prepare
Install the dependency library. It is better to create a virtual environments before to do it.
```
pip install -r requirements.txt
```
#### Run
```
python ./src/main.py
```
- B. Build as a execution file
```
pyinstaller build.spec
```

#### Startup Arguments
You can specify some arguments while run the tool

parameters:

| Name | Type | Default | Description |
| - | :-: | :-: | - |
| --device-type | String | 'auto' | Value should be `IMU`, `RTK` |
| --com-port | String | 'auto' | Value should be a COM port |
| --baudrate | String | None | Value should be baudrate |
| --debug | Boolean | False | If log debug information |

### 2. Connect ans device
Link device to your pc or mac. And the tool will auto detect the linked device.

[More Usage](USAGE.md "More Usage")
