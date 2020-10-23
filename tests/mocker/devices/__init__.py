class Parameter(object):
    def __init__(self, data_type, value):
        self._data_type = data_type
        self._value = value

    @property
    def data_type(self):
        return self._data_type

    @data_type.setter
    def data_type(self, data_type):
        self._data_type = data_type

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
