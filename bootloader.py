def start_bootloader(self):
        '''Starts bootloader
            :returns:
                True if bootloader mode entered, False if failed
        '''
        self.set_quiet()
        C = [0x55, 0x55, ord('J'), ord('I'), 0x00 ]
        crc = self.calc_crc(C[2:4] + [0x00])    # for some reason must add a payload byte to get correct CRC
        crc_msb = (crc & 0xFF00) >> 8
        crc_lsb = (crc & 0x00FF)
        C.insert(len(C), crc_msb)
        C.insert(len(C), crc_lsb)
        self.write(C)
        time.sleep(1)   # must wait for boot loader to be ready
        R = self.read(5)
        if R[0] == 85 and R[1] == 85:
            self.packet_type =  '{0:1c}'.format(R[2]) + '{0:1c}'.format(R[3])
            if self.packet_type == 'JI':
                self.read(R[4]+2)
                print('bootloader ready')
                time.sleep(2)
                self.reset_buffer()
                return True
            else: 
                return False
        else:
            return False
    
def start_app(self):
    '''Starts app
    '''
    self.set_quiet()
    C = [0x55, 0x55, ord('J'), ord('A'), 0x00 ]
    crc = self.calc_crc(C[2:4] + [0x00])    # for some reason must add a payload byte to get correct CRC
    crc_msb = (crc & 0xFF00) >> 8
    crc_lsb = (crc & 0x00FF)
    C.insert(len(C), crc_msb)
    C.insert(len(C), crc_lsb)
    self.write(C)
    time.sleep(1)
    R = self.read(7)    
    if R[0] == 85 and R[1] == 85:
        self.packet_type =  '{0:1c}'.format(R[2]) + '{0:1c}'.format(R[3])
        print(self.packet_type)

def write_block(self, buf, data_len, addr):
    '''Executed WA command to write a block of new app code into memory
    '''
    print(data_len, addr)
    C = [0x55, 0x55, ord('W'), ord('A'), data_len+5]
    addr_3 = (addr & 0xFF000000) >> 24
    addr_2 = (addr & 0x00FF0000) >> 16
    addr_1 = (addr & 0x0000FF00) >> 8
    addr_0 = (addr & 0x000000FF)
    C.insert(len(C), addr_3)
    C.insert(len(C), addr_2)
    C.insert(len(C), addr_1)
    C.insert(len(C), addr_0)
    C.insert(len(C), data_len)
    for i in range(data_len):
        C.insert(len(C), ord(buf[i]))
    crc = self.calc_crc(C[2:C[4]+5])  
    crc_msb = int((crc & 0xFF00) >> 8)
    crc_lsb = int((crc & 0x00FF))
    C.insert(len(C), crc_msb)
    C.insert(len(C), crc_lsb)
    status = 0
    while (status == 0):
        self.write(C)
        if addr == 0:
            time.sleep(10)
        R = self.read(12)  #longer response
        if len(R) > 1 and R[0] == 85 and R[1] == 85:
            self.packet_type =  '{0:1c}'.format(R[2]) + '{0:1c}'.format(R[3])
            print(self.packet_type)
            if self.packet_type == 'WA':
                status = 1
            else:
                sys.exit()
                print('retry 1')
                status = 0
        else:
            print(len(R))
            print(R)
            self.reset_buffer()
            time.sleep(1)
            print('no packet')
            sys.exit()
        
def upgrade_fw(self,file):
    '''Upgrades firmware of connected 380 device to file provided in argument
    '''
    print('upgrade fw')
    max_data_len = 240
    write_len = 0
    fw = open(file, 'rb').read()
    fs_len = len(fw)

    if not self.start_bootloader():
        print('Bootloader Start Failed')
        return False
    
    time.sleep(1)
    while (write_len < fs_len):
        packet_data_len = max_data_len if (fs_len - write_len) > max_data_len else (fs_len-write_len)
        # From IMUView 
        # Array.Copy(buf,write_len,write_buf,0,packet_data_len);
        write_buf = fw[write_len:(write_len+packet_data_len)]
        self.write_block(write_buf, packet_data_len, write_len)
        write_len += packet_data_len
    time.sleep(1)
    # Start new app
    self.start_app()