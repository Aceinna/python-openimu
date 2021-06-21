import struct
from . import filter_nan

IIR_50HZ_LPF = 50
IIR_40HZ_LPF = 40
IIR_25HZ_LPF = 25
IIR_20HZ_LPF = 20
IIR_10HZ_LPF = 10
IIR_05HZ_LPF = 5
IIR_02HZ_LPF = 2
UNFILTERED = 0


def bytes_to_byte_instr(b, n=None):
    s = ''.join(f'{x:08b}' for x in b)
    return s if n is None else s[:n + n // 8 + (0 if n % 8 else -1)]


def decode_lpf(payload):
    # print('decode lpf', payload)
    pack_item = struct.pack('2B', *payload)
    counts = struct.unpack('>H', pack_item)[0]
    if counts > 18749:
        return IIR_02HZ_LPF
    elif (counts <= 18749) and (counts > 8034):
        return IIR_05HZ_LPF
    elif (counts <= 8034) and (counts > 4017):
        return IIR_10HZ_LPF
    elif (counts <= 4017) and (counts > 2410):
        return IIR_20HZ_LPF
    elif (counts <= 2410) and (counts > 1740):
        return IIR_25HZ_LPF
    elif (counts <= 1740) and (counts > 1204):
        return IIR_40HZ_LPF
    elif (counts <= 1204) and (counts > 0):
        return IIR_50HZ_LPF
    else:
        return UNFILTERED


def encode_lpf(value):
    # print('encode lpf', value)
    counts = 0
    if value == IIR_02HZ_LPF:
        counts = 26785
    elif value == IIR_05HZ_LPF:
        counts = 10713
    elif value == IIR_10HZ_LPF:
        counts = 5356
    elif value == IIR_20HZ_LPF:
        counts = 2678
    elif value == IIR_25HZ_LPF:
        counts = 2142
    elif value == IIR_40HZ_LPF:
        counts = 1338
    elif value == UNFILTERED:
        counts = 0
    else:
        counts = 1070

    return struct.pack('>h', counts)


def do_decode_value(data_type, data):
    if data_type == 'uint64':
        try:
            pack_item = struct.pack('8B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('>Q', pack_item)[0]
    elif data_type == 'int64':
        try:
            pack_item = struct.pack('8B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('>q', pack_item)[0]
    elif data_type == 'double':
        try:
            pack_item = struct.pack('8B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('d', pack_item)[0]
    elif data_type == 'uint32':
        try:
            pack_item = struct.pack('4B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('>I', pack_item)[0]
    elif data_type == 'int32':
        try:
            pack_item = struct.pack('4B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('>i', pack_item)[0]
    elif data_type == 'float':
        try:
            pack_item = struct.pack('4B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('>f', pack_item)[0]
    elif data_type == 'uint16':
        try:
            pack_item = struct.pack('2B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('>H', pack_item)[0]
    elif data_type == 'int16':
        try:
            pack_item = struct.pack('2B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('>h', pack_item)[0]
    elif data_type == 'uint8':
        try:
            pack_item = struct.pack('1B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('>B', pack_item)[0]
    elif data_type == 'int8':
        try:
            pack_item = struct.pack('1B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('>b', pack_item)[0]
    elif 'char' in data_type:
        try:
            trim_data = [elem for elem in data if elem != 0]
            max_len = int(data_type.replace('char', ''))
            trim_len = len(trim_data)
            data_len = trim_len if trim_len < max_len else max_len
            pack_item = struct.pack('{0}B'.format(data_len), *trim_data)
            return pack_item.decode()
        except:  # pylint: disable=bare-except
            return False
    elif data_type == 'string':
        try:
            fmt_str = '{0}B'.format(len(data))
            pack_item = struct.pack(fmt_str, *data)
            return pack_item
        except:  # pylint: disable=bare-except
            return False
    elif data_type == 'ip4':
        try:
            ip_1 = str(data[0])
            ip_2 = str(data[1])
            ip_3 = str(data[2])
            ip_4 = str(data[3])
            return ip_1+'.'+ip_2+'.'+ip_3+'.'+ip_4
        except:  # pylint: disable=bare-except
            return False
    elif data_type == 'ip6':
        try:
            ip_1 = str(data[0])
            ip_2 = str(data[1])
            ip_3 = str(data[2])
            ip_4 = str(data[3])
            ip_5 = str(data[4])
            ip_6 = str(data[5])
            return ip_1+'.'+ip_2+'.'+ip_3+'.'+ip_4+'.'+ip_5+'.'+ip_6
        except:  # pylint: disable=bare-except
            return False
    elif data_type == 'orientation':
        byte_str = bytes_to_byte_instr(data)
        ret_data = ''
        x_sign = byte_str[-1]
        ret_data += '+' if x_sign == '0' else '-'
        x_asix = int(byte_str[-3:-1], 2)
        ret_data += ['X', 'Y', 'Z'][x_asix]

        y_sign = byte_str[-4]
        ret_data += '+' if y_sign == '0' else '-'
        y_asix = int(byte_str[-6:-4], 2)
        ret_data += ['Y', 'Z', 'X'][y_asix]

        z_sign = byte_str[-7]
        ret_data += '+' if z_sign == '0' else '-'
        z_asix = int(byte_str[-9:-7], 2)
        ret_data += ['Z', 'X', 'Y'][z_asix]

        return ret_data  # '+X+Y+Z'
    elif data_type == 'lpf':
        return decode_lpf(data)
    else:
        return False


def decode_value(data_type, data):
    ret_value = do_decode_value(data_type, data)

    return filter_nan(ret_value)


def encode_value(data_type, data):
    if 'char' in data_type:
        actual_len = len(data)
        max_len = int(data_type.replace('char', ''))
        data_len = actual_len if actual_len < max_len else max_len
        bytes_data = bytearray(data, 'utf-8')
        return struct.pack('{0}B'.format(data_len), *bytes_data)

    elif data_type == 'uint16':
        return struct.pack('>h', data)

    elif data_type == 'orientation':
        if len(data) == 6:
            bit_str = ''
            x_sign = data[0]
            bit_str += '0' if x_sign == '+' else '1'
            x_asix = data[1]
            bit_str = {'X': '00', 'Y': '01', 'Z': '10'}.get(x_asix) + bit_str

            y_sign = data[2]
            bit_str = ('0' if y_sign == '+' else '1') + bit_str
            y_asix = data[3]
            bit_str = {'Y': '00', 'Z': '01', 'X': '10'}.get(y_asix) + bit_str

            z_sign = data[4]
            bit_str = ('0' if z_sign == '+' else '1') + bit_str
            z_asix = data[5]
            bit_str = {'Z': '00', 'X': '01', 'Y': '10'}.get(z_asix) + bit_str

            value = int(bit_str, 2)
            return struct.pack('>h', value)
        return False
    elif data_type == 'lpf':
        return encode_lpf(data)
    else:
        return False
