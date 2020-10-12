class InternalCombineAppParseRule:
    '''
    Parse rule for combined app of OpenRTK
    '''

    def __init__(self, name, start_str, data_len_count):
        self.name = name
        self.start_str = start_str
        self.data_len_count = data_len_count
