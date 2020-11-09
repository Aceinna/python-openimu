class Parameter(object):
    def __init__(self, name, data_type, value):
        self._name = name
        self._data_type = data_type
        self._value = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

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
