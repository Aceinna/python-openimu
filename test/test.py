import serial
import serial.tools.list_ports

portList = list(serial.tools.list_ports.comports())
for p in portList:
    print(p.device,p.hwid, p.interface)
