# Test Cases Definition

## Bootstrap
Client communication
- Websocket
- MQTT (TODO)

### Default Run
A executable with WebSocket(Client) and UART(Device)

### CLI
A command line tool with WebSocket(Client) and UART(Device)

## Test Tools
TODO

## Test Framework
- Platform API
- Application Logger
- File Logger
- UART Communicator
- LAN Communicator
- Decorator
- Resource
- Helper

## Test Devices

### Test Detector
Device connection test
- Device connect with UART
- Device connect with LAN
- Device disconnect 

### Test Parser
- UART Message Parser
- LAN Message Parser

## Mocker
- OpenIMU
- OpenRTK
- DMU 