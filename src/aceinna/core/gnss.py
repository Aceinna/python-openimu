import struct
from .event_base import EventBase


class ANALYSIS_STATUS:
    INIT = 0
    FOUND_HEADER = 1
    FOUND_PAYLOAD_LENGTH = 2
    FOUND_PACKET_TYPE = 3
    CRC_PASSED = 4


PACKET_HEADER = 0xD3


def bytes_to_usigned_integer(bytes_data: bytes, significant_len=10):
    return struct.unpack(">I", bytes_data)[0] & 2**significant_len-1


def calc_crc(buffer, len):
    crc = 0

    tbl_CRC24Q = [
        0x000000, 0x864CFB, 0x8AD50D, 0x0C99F6, 0x93E6E1, 0x15AA1A, 0x1933EC, 0x9F7F17,
        0xA18139, 0x27CDC2, 0x2B5434, 0xAD18CF, 0x3267D8, 0xB42B23, 0xB8B2D5, 0x3EFE2E,
        0xC54E89, 0x430272, 0x4F9B84, 0xC9D77F, 0x56A868, 0xD0E493, 0xDC7D65, 0x5A319E,
        0x64CFB0, 0xE2834B, 0xEE1ABD, 0x685646, 0xF72951, 0x7165AA, 0x7DFC5C, 0xFBB0A7,
        0x0CD1E9, 0x8A9D12, 0x8604E4, 0x00481F, 0x9F3708, 0x197BF3, 0x15E205, 0x93AEFE,
        0xAD50D0, 0x2B1C2B, 0x2785DD, 0xA1C926, 0x3EB631, 0xB8FACA, 0xB4633C, 0x322FC7,
        0xC99F60, 0x4FD39B, 0x434A6D, 0xC50696, 0x5A7981, 0xDC357A, 0xD0AC8C, 0x56E077,
        0x681E59, 0xEE52A2, 0xE2CB54, 0x6487AF, 0xFBF8B8, 0x7DB443, 0x712DB5, 0xF7614E,
        0x19A3D2, 0x9FEF29, 0x9376DF, 0x153A24, 0x8A4533, 0x0C09C8, 0x00903E, 0x86DCC5,
        0xB822EB, 0x3E6E10, 0x32F7E6, 0xB4BB1D, 0x2BC40A, 0xAD88F1, 0xA11107, 0x275DFC,
        0xDCED5B, 0x5AA1A0, 0x563856, 0xD074AD, 0x4F0BBA, 0xC94741, 0xC5DEB7, 0x43924C,
        0x7D6C62, 0xFB2099, 0xF7B96F, 0x71F594, 0xEE8A83, 0x68C678, 0x645F8E, 0xE21375,
        0x15723B, 0x933EC0, 0x9FA736, 0x19EBCD, 0x8694DA, 0x00D821, 0x0C41D7, 0x8A0D2C,
        0xB4F302, 0x32BFF9, 0x3E260F, 0xB86AF4, 0x2715E3, 0xA15918, 0xADC0EE, 0x2B8C15,
        0xD03CB2, 0x567049, 0x5AE9BF, 0xDCA544, 0x43DA53, 0xC596A8, 0xC90F5E, 0x4F43A5,
        0x71BD8B, 0xF7F170, 0xFB6886, 0x7D247D, 0xE25B6A, 0x641791, 0x688E67, 0xEEC29C,
        0x3347A4, 0xB50B5F, 0xB992A9, 0x3FDE52, 0xA0A145, 0x26EDBE, 0x2A7448, 0xAC38B3,
        0x92C69D, 0x148A66, 0x181390, 0x9E5F6B, 0x01207C, 0x876C87, 0x8BF571, 0x0DB98A,
        0xF6092D, 0x7045D6, 0x7CDC20, 0xFA90DB, 0x65EFCC, 0xE3A337, 0xEF3AC1, 0x69763A,
        0x578814, 0xD1C4EF, 0xDD5D19, 0x5B11E2, 0xC46EF5, 0x42220E, 0x4EBBF8, 0xC8F703,
        0x3F964D, 0xB9DAB6, 0xB54340, 0x330FBB, 0xAC70AC, 0x2A3C57, 0x26A5A1, 0xA0E95A,
        0x9E1774, 0x185B8F, 0x14C279, 0x928E82, 0x0DF195, 0x8BBD6E, 0x872498, 0x016863,
        0xFAD8C4, 0x7C943F, 0x700DC9, 0xF64132, 0x693E25, 0xEF72DE, 0xE3EB28, 0x65A7D3,
        0x5B59FD, 0xDD1506, 0xD18CF0, 0x57C00B, 0xC8BF1C, 0x4EF3E7, 0x426A11, 0xC426EA,
        0x2AE476, 0xACA88D, 0xA0317B, 0x267D80, 0xB90297, 0x3F4E6C, 0x33D79A, 0xB59B61,
        0x8B654F, 0x0D29B4, 0x01B042, 0x87FCB9, 0x1883AE, 0x9ECF55, 0x9256A3, 0x141A58,
        0xEFAAFF, 0x69E604, 0x657FF2, 0xE33309, 0x7C4C1E, 0xFA00E5, 0xF69913, 0x70D5E8,
        0x4E2BC6, 0xC8673D, 0xC4FECB, 0x42B230, 0xDDCD27, 0x5B81DC, 0x57182A, 0xD154D1,
        0x26359F, 0xA07964, 0xACE092, 0x2AAC69, 0xB5D37E, 0x339F85, 0x3F0673, 0xB94A88,
        0x87B4A6, 0x01F85D, 0x0D61AB, 0x8B2D50, 0x145247, 0x921EBC, 0x9E874A, 0x18CBB1,
        0xE37B16, 0x6537ED, 0x69AE1B, 0xEFE2E0, 0x709DF7, 0xF6D10C, 0xFA48FA, 0x7C0401,
        0x42FA2F, 0xC4B6D4, 0xC82F22, 0x4E63D9, 0xD11CCE, 0x575035, 0x5BC9C3, 0xDD8538
    ]

    # TODO: unsigned long
    for i in range(len):
        crc = ((crc << 8) & 0xFFFFFF) ^ tbl_CRC24Q[(crc >> 16) ^ buffer[i]]

    return crc


class RTCMPacket:
    _payload_length = 0
    _raw_data_bytes = []
    _header_bytes = []
    _payload_length_bytes = []
    _payload_bytes = []

    def __init__(self):
        self._payload_length = 0
        self._raw_data_bytes = []
        self._header_bytes = []
        self._payload_length_bytes = []
        self._payload_bytes = []

    @property
    def payload_length(self):
        return self._payload_length

    def accept_to_header(self, byte_data):
        self._header_bytes.append(byte_data)
        self._raw_data_bytes.append(byte_data)

    def accept_to_length(self, byte_data):
        self._payload_length_bytes.append(byte_data)
        self._raw_data_bytes.append(byte_data)

    def accept_to_payload(self, byte_data):
        self._payload_bytes.append(byte_data)
        self._raw_data_bytes.append(byte_data)

    def calc_payload_length(self):
        self._payload_length = bytes_to_usigned_integer(
            bytes(2)+bytes(self._payload_length_bytes))+3

    def check_crc(self):
        crc_table_value = calc_crc(self._raw_data_bytes, self._payload_length)

        crc_value = bytes_to_usigned_integer(
            bytes(1)+bytes(self._raw_data_bytes[-3:]), 24)
        #print(crc_table_value, crc_value, self._raw_data_bytes[-3:])
        #print(self._payload_length, len(self._raw_data_bytes))
        # if crc_table_value != crc_value:
        #     print(crc_table_value, crc_value, self._raw_data_bytes[-3:])
        return crc_table_value == crc_value

    def get_raw(self):
        return self._raw_data_bytes


class RTCMParser(EventBase):
    read_index = 0
    recevied_buf: bytes = []
    current_analysis_status = ANALYSIS_STATUS.INIT
    current_packet: RTCMPacket
    found_header_count = 0
    crc_passed_count = 0

    def __init__(self):
        super(RTCMParser, self).__init__()

    def receive(self, buf: bytes):
        ''' Recevie a byte array, and emit the parsed data
            - Packet structure: [0xD3 packet_len packet_type payload 3_bytes_crc]
        '''
        self.recevied_buf = buf
        parsed_result = self._analysis()
        if len(parsed_result) > 0:
            self.emit('parsed', parsed_result)

    def get_statistics(self):
        return {
            'found_header_count': self.found_header_count,
            'valid_packet_count': self.crc_passed_count
        }

    def _analysis(self):
        packets = []
        recevied_buf_iter = iter(self.recevied_buf)
        while True:
            try:
                byte_data = next(recevied_buf_iter)
            except StopIteration as e:
                break
            else:
                if self.current_analysis_status == ANALYSIS_STATUS.INIT:
                    is_found_header = self.read_index == 0 and byte_data == PACKET_HEADER
                    # new message
                    if is_found_header:
                        self.found_header_count += 1
                        self.current_packet = RTCMPacket()
                        self.current_packet.accept_to_header(byte_data)
                        self.current_analysis_status = ANALYSIS_STATUS.FOUND_HEADER
                        self.read_index += 1
                    else:
                        self.read_index = 0
                    continue

                if self.current_analysis_status == ANALYSIS_STATUS.FOUND_HEADER:
                    self.current_packet.accept_to_length(byte_data)
                    self.read_index += 1

                    if self.read_index == 3:
                        self.current_packet.calc_payload_length()
                        self.current_analysis_status = ANALYSIS_STATUS.FOUND_PAYLOAD_LENGTH
                    continue

                if self.current_analysis_status == ANALYSIS_STATUS.FOUND_PAYLOAD_LENGTH:
                    self.current_packet.accept_to_payload(byte_data)
                    self.read_index += 1
                    if self.read_index == self.current_packet.payload_length+3:
                        # calculate crc
                        crc_result = self.current_packet.check_crc()
                        if not crc_result:
                            self.current_analysis_status = ANALYSIS_STATUS.INIT
                            self.read_index = 0
                            continue

                        # crc valid
                        self.current_analysis_status = ANALYSIS_STATUS.CRC_PASSED

                    if self.current_analysis_status == ANALYSIS_STATUS.CRC_PASSED:
                        self.crc_passed_count+=1
                        packets.append(self.current_packet.get_raw())
                        self.current_analysis_status = ANALYSIS_STATUS.INIT
                        self.read_index = 0
                    continue

        return packets
