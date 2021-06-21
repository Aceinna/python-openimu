import time
import serial


def process_force_bootloader(port_name, device_type):
    # OpenRTK has a bootloader switch, no need force enter bootloader
    baudrate_mapping = {
        'IMU': 57600
    }
    # communicator open
    left_time = 10
    serial_port = None

    while left_time > 0:
        if not serial_port:
            try:
                serial_port = serial.Serial(
                    port=port_name, baudrate=baudrate_mapping[device_type])
            except serial.serialutil.SerialException:
                serial_port = None

                time.sleep(0.01)
                left_time -= 0.01
                continue

        # JB commands
        serial_port.write([0x55, 0x55, 0x4A, 0x42, 0x00, 0xA0, 0xCE])
        time.sleep(0.02)
        left_time -= 0.02

    if serial_port:
        serial_port.close()

    return {
        'packetType': 'success',
        'data': {
            'status': 1
        }
    }


if __name__ == '__main__':
    process_force_bootloader('/dev/cu.usbserial-AK005M29', 'IMU')
