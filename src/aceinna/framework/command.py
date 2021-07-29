class Command(object):
    _actual_command = []
    _payload_length_format = 'B'
    _packet_type = []

    def __init__(self, packet_type, command_line, payload_length_format='B'):
        self._actual_command = command_line
        self._payload_length_format = payload_length_format
        self._packet_type = packet_type

    @property
    def actual_command(self):
        return self._actual_command

    @property
    def payload_length_format(self):
        return self._payload_length_format

    @property
    def packet_type(self):
        return self._packet_type
