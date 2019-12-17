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
python main.py
```
- B. Build as a execution file
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

### 2. Connect ans device
Link device to your pc or mac. And the tool will auto detect the linked device.
