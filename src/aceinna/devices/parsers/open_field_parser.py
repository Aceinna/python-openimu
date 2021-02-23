import math
import struct
import decimal
from . import filter_nan


def do_decode_value(data_type, data, conf):
    if data_type == 'uint64':
        try:
            pack_item = struct.pack('8B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('<Q', pack_item)[0]
    elif data_type == 'int64':
        try:
            pack_item = struct.pack('8B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('<q', pack_item)[0]
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
        return struct.unpack('<I', pack_item)[0]
    elif data_type == 'int32':
        try:
            pack_item = struct.pack('4B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('<i', pack_item)[0]
    elif data_type == 'float':
        try:
            pack_item = struct.pack('4B', *data)
        except:  # pylint: disable=bare-except
            return False

        unpack_value = struct.unpack('<f', pack_item)[0]
        # use decimal, float type is a special case
        if conf and conf['value_accuracy']:
            precision = conf['value_accuracy']
            decimal_wrapped = decimal.Decimal(unpack_value)
            try:
                unpack_value = float(round(decimal_wrapped, precision))
            except:
                unpack_value = 0
        return unpack_value
    elif data_type == 'uint16':
        try:
            pack_item = struct.pack('2B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('<H', pack_item)[0]
    elif data_type == 'int16':
        try:
            pack_item = struct.pack('2B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('<h', pack_item)[0]
    elif data_type == 'uint8':
        try:
            pack_item = struct.pack('1B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('<B', pack_item)[0]
    elif data_type == 'int8':
        try:
            pack_item = struct.pack('1B', *data)
        except:  # pylint: disable=bare-except
            return False
        return struct.unpack('<b', pack_item)[0]
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
    else:
        return False


def decode_value(data_type, data, conf=None):
    ret_value = do_decode_value(data_type, data, conf)

    return filter_nan(ret_value)


def encode_value(data_type, data):
    payload = []

    if data_type == 'uint64':
        payload += list(struct.unpack("8B", struct.pack("<Q", data)))
    elif data_type == 'int64':
        payload += list(struct.unpack("8B", struct.pack("<q", data)))
    elif data_type == 'double':
        payload += list(struct.unpack("8B",
                                      struct.pack("<d", float(data))))
    elif data_type == 'uint32':
        payload += list(struct.unpack("4B", struct.pack("<I", data)))
    elif data_type == 'int32':
        payload += list(struct.unpack("4B", struct.pack("<i", data)))
    elif data_type == 'float':
        payload += list(struct.unpack("4B", struct.pack("<f", data)))
    elif data_type == 'uint16':
        payload += list(struct.unpack("2B", struct.pack("<H", data)))
    elif data_type == 'int16':
        payload += list(struct.unpack("2B", struct.pack("<h", data)))
    elif data_type == 'uint8':
        payload += list(struct.unpack("1B", struct.pack("<B", data)))
    elif data_type == 'int8':
        payload += list(struct.unpack("1B", struct.pack("<b", data)))
    elif 'char' in data_type:
        c_len = int(data_type.replace('char', ''))
        if isinstance(data, int):
            length = len(str(data))
            payload += list(struct.unpack('{0}B'.format(length),
                                          bytearray(str(data), 'utf-8')))
        else:
            length = len(data)
            payload += list(struct.unpack('{0}B'.format(length),
                                          bytearray(data, 'utf-8')))
        for i in range(c_len-length):
            payload += [0x00]
    elif data_type == 'ip4':
        ip_address = data.split('.')
        ip_address_v4 = list(map(int, ip_address))
        for i in range(4):
            payload += list(struct.unpack("1B",
                                          struct.pack("<B", ip_address_v4[i])))
    elif data_type == 'ip6':
        ip_address = data.split('.')
        payload += list(struct.unpack('6B',
                                      bytearray(ip_address, 'utf-8')))

    return payload
