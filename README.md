# python-ans-devices
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
| --port | Number | 8000 | Value should be an available port |
| --device-type | String | 'auto' | Value should be `IMU`, `RTK` |
| --baudrate | String | None | Value should be baudrate |
| --com-port | String | 'auto' | Value should be a COM port |
| --console-log | Boolean | False | Output log on console |
| --debug | Boolean | False | Log debug information |
| --with-data-log | Boolean | False | Contains internal data log (OpenIMU only) |
| --with-raw-log | Boolean | False | Contains raw data log (OpenRTK only) |

### 2. Connect ans device
Link device to your pc or mac. And the tool will auto detect the linked device.

[More Usage](USAGE.md "More Usage")
