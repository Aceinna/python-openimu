# python-ans-devices
Python driver for OpenIMU and OpenRTK

## Working Environment 
- Windows10: python2.7 and python 3.7
- Mac OS: python2.7 and python 3.7

## Steps

### Dependency - pip install
```
pip install -r requirements.txt
```

### Execution
There are 2 ways to run the tool
1. From source code, run main.py
```
python server.py
```
2. Build as a execution file
```
pyinstaller build.spec
```
#### Startup Arguments
You can specify some arguments while run the tool

Parameter | Default Value | Description
-|-|-
`-p` | 8000 | This a port for websocket server |
`-b`|[38400, 57600, 115200,230400, 460800]|A baudrate range for auto detect device|
`-nolog`|True|Internal log switch, suggest to disable|

### Connect your device
Link device to your pc or mac. And the tool will auto detect the linked device.
