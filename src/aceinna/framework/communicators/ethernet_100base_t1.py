import time
import collections
from scapy.all import sendp, conf, AsyncSniffer
from ..constants import (BAUDRATE_LIST, INTERFACES)
from ..utils.print import (print_red)
from ..utils import helper
from ..communicator import Communicator


class Ethernet(Communicator):
    '''Ethernet'''

    def __init__(self, options=None):
        super().__init__()
        self.type = INTERFACES.ETH_100BASE_T1
        self.src_mac = None
        self.dst_mac = 'FF:FF:FF:FF:FF:FF'
        self.ethernet_name = None
        self.data = None
        self.iface = None

        self.filter_device_type = None
        self.filter_device_type_assigned = False

        self.iface_confirmed = False
        self.receive_cache = collections.deque(maxlen=1000)
        self.use_length_as_protocol = True
        self.async_sniffer = None

        if options and options.device_type != 'auto':
            self.filter_device_type = options.device_type
            self.filter_device_type_assigned = True

    def handle_iface_confirm_packet(self, packet):
        self.iface_confirmed = True
        self.dst_mac = packet.src

    def confirm_iface(self, iface):
        dst_mac_str = 'FF:FF:FF:FF:FF:FF'

        filter_exp = 'ether dst host ' + \
            iface[1] + ' and ether[16:2] == 0x01cc'
        dst_mac = bytes([int(x, 16) for x in dst_mac_str.split(':')])
        src_mac = bytes([int(x, 16) for x in iface[1].split(':')])

        self.send_async_shake_hand(
            iface[0], dst_mac, src_mac, filter_exp, True)

        if self.iface_confirmed:
            self.iface = iface[0]
            self.src_mac = iface[1]
            self.use_length_as_protocol = True
            print('[NetworkCard]', self.iface)
            return

        dst_mac_str = '04:00:00:00:00:04'
        dst_mac = bytes([int(x, 16) for x in dst_mac_str.split(':')])
        filter_exp = 'ether src host ' + \
            dst_mac_str + ' and ether[16:2] == 0x01cc'

        self.send_async_shake_hand(
            iface[0], dst_mac, src_mac, filter_exp, False)

        if self.iface_confirmed:
            self.iface = iface[0]
            self.src_mac = iface[1]
            self.use_length_as_protocol = False
            print('[NetworkCard]', self.iface)

    def find_device(self, callback, retries=0, not_found_handler=None):
        self.device = None

        # find network connection
        if not self.iface_confirmed:
            ifaces_list = self.get_network_card()
            for i in range(len(ifaces_list)):
                self.confirm_iface(ifaces_list[i])
                if self.iface_confirmed:
                    self.start_listen_data()
                    break
                else:
                    if i == len(ifaces_list) - 1:
                        print_red('No available Ethernet card was found.')
                        return None
        else:
            self.reshake_hand()

        # confirm device
        time.sleep(1)
        self.confirm_device(self)
        if self.device:
            # establish the packet sniff thread
            callback(self.device)
        else:
            print_red(
                'Cannot confirm the device in ethernet 100base-t1 connection')

    def send_async_shake_hand(self, iface, dst_mac, src_mac, filter, use_length_as_protocol):
        pG = [0x01, 0xcc]
        command = helper.build_ethernet_packet(
            dst_mac, src_mac, pG, use_length_as_protocol=use_length_as_protocol)
        async_sniffer = AsyncSniffer(
            iface=iface,
            prn=self.handle_iface_confirm_packet,
            filter=filter)
        async_sniffer.start()
        time.sleep(0.2)
        sendp(command.actual_command, iface=iface, verbose=0)
        time.sleep(0.5)
        async_sniffer.stop()

    def reshake_hand(self):
        if self.async_sniffer and self.async_sniffer.running:
            self.async_sniffer.stop()

        self.iface_confirmed = False
        dst_mac_str = 'FF:FF:FF:FF:FF:FF'

        filter_exp = 'ether dst host ' + \
            self.src_mac + ' and ether[16:2] == 0x01cc'
        dst_mac = bytes([int(x, 16) for x in dst_mac_str.split(':')])
        src_mac = self.get_src_mac()

        self.send_async_shake_hand(
            self.iface, dst_mac, src_mac, filter_exp, True)

        if self.iface_confirmed:
            self.use_length_as_protocol = True
            self.start_listen_data()
            return True

        dst_mac_str = '04:00:00:00:00:04'
        dst_mac = bytes([int(x, 16) for x in dst_mac_str.split(':')])
        filter_exp = 'ether src host ' + \
            dst_mac_str + ' and ether[16:2] == 0x01cc'

        self.send_async_shake_hand(
            self.iface, dst_mac, src_mac, filter_exp, True)

        if self.iface_confirmed:
            self.use_length_as_protocol = False
            self.start_listen_data()
            return True
        else:
            raise Exception('Cannot finish shake hand.')

    def start_listen_data(self):
        '''
        The different mac address make the filter very hard to match
        '''
        hard_code_mac = '04:00:00:00:00:04'
        filter_exp = 'ether src host {0} or {1}'.format(
            self.dst_mac, hard_code_mac)

        self.async_sniffer = AsyncSniffer(
            iface=self.iface, prn=self.handle_recive_packet, filter=filter_exp, store=0)
        self.async_sniffer.start()
        time.sleep(0.1)

    def handle_recive_packet(self, packet):
        packet_raw = bytes(packet)[12:]
        packet_raw_length = packet_raw[0:2]
        packet_type = packet_raw[4:6]

        if packet_type == b'\x01\xcc':
            self.dst_mac = packet.src

            if packet_raw_length == b'\x00\x00':
                self.use_length_as_protocol = False

        self.receive_cache.append(packet_raw[2:])

    def open(self):
        '''
        open
        '''

    def close(self):
        '''
        close
        '''

    def can_write(self):
        if self.iface:
            return True
        return False

    def write(self, data, is_flush=False):
        '''
        write
        '''
        try:
            sendp(data, iface=self.iface, verbose=0)
            # print(data)
        except Exception as e:
            raise

    def read(self, size=100):
        '''
        read
        '''
        if len(self.receive_cache) > 0:
            return self.receive_cache.popleft()
        return []

    def reset_buffer(self):
        '''
        reset buffer
        '''
        self.receive_cache.clear()

    def get_src_mac(self):
        return bytes([int(x, 16) for x in self.src_mac.split(':')])

    def get_dst_mac(self):
        return bytes([int(x, 16) for x in self.dst_mac.split(':')])

    def get_network_card(self):
        network_card_info = []
        for item in conf.ifaces:
            if conf.ifaces[item].ip == '127.0.0.1' or conf.ifaces[item].mac == '':
                continue
            network_card_info.append(
                (conf.ifaces[item].name, conf.ifaces[item].mac))
        return network_card_info
