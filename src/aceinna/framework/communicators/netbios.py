import socket
import time


class netbios_query:
    def __init__(self, name, ip_address_list):
        self.__name = name
        self.__ip_address_list = ip_address_list
        self.__boardcast_address_list = []

        self.__populate()

    def __populate(self):
        for ip_address in self.__ip_address_list:
            split_items = ip_address.split('.')
            split_items[3] = '255'
            boardcast_address = '.'.join(split_items)
            self.__boardcast_address_list.append(boardcast_address)

        self.__port = 137
        self.__nqs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__nqs.setblocking(False)
        self.__query_data = [
            b"\xa9\xfb",  # Transaction ID
            b"\x01\x10",  # Flags Query
            b"\x00\x01",  # Question:1
            b"\x00\x00",  # Answer RRS
            b"\x00\x00",  # Authority RRS
            b"\x00\x00",  # Additional RRS
            b"\x20",      # length of Name:32
            b"NAME",      # Name
            b"\x00",      # NameNull
            b"\x00\x20",  # Query Type:NB
            b"\x00\x01"]  # Class
        self.__query_data[7] = str.encode(self.__netbios_encode(self.__name))

    def __netbios_encode(self, src):
        src = src.ljust(15, "\x20")
        src = src.ljust(16, "\x00")
        names = []
        for c in src:
            char_ord = ord(c)
            high_4_bits = char_ord >> 4
            low_4_bits = char_ord & 0x0f
            names.append(high_4_bits)
            names.append(low_4_bits)
            res = ""
        for name in names:
            res += chr(0x41+name)
        return res

    def query(self):
        wait_count = 10
        send_data = []
        ret = None

        for bytes_ele in self.__query_data:
            for list_ele in bytes_ele:
                send_data.append(list_ele)

        while wait_count:
            for idx, boardcast_address in enumerate(self.__boardcast_address_list):
                try:
                    self.__nqs.sendto(bytes(send_data),
                                    (boardcast_address, self.__port))
                    time.sleep(1)
                    data_rev, ADDR = self.__nqs.recvfrom(1024)
                except Exception as ex:
                    continue

                if len(data_rev) > 0:
                    ret = self.__ip_address_list[idx]
                    break

            if ret:
                break
            else:
                wait_count -= 1

        self.__nqs.close()

        return ret
