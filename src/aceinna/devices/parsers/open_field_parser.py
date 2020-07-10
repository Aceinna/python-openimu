import struct


def decode_value(data_type, data):
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
        return struct.unpack('<f', pack_item)[0]
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
