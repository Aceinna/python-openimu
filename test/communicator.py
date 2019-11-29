from . import app

serial =  app.framework.communicator.SerialPort()
ports = serial.find_ports()
print(ports)