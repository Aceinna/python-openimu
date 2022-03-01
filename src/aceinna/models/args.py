class KeyValuesArgumentBase(object):
    '''
    Object Argument Base
    '''
    default_values = {}

    def __init__(self, **options):
        keys = self.default_values.keys()
        for key in keys:
            value = self._prepare_value(options, key)
            setattr(self, key, value)

    def _prepare_value(self, input_args, key):
        value = input_args.get(key)
        if not value:
            value = self.default_values.get(key)
        return value

    def __str__(self):
        str_out = ''
        keys = self.default_values.keys()
        for key in keys:
            value = getattr(self, key)
            str_out = str_out+str(key)+"="+str(value)+" "
        return str_out


class WebserverArgs(KeyValuesArgumentBase):
    '''
    Argument define for start webserver
    '''
    default_values = {
        'interface': 'uart',
        'device_type': 'auto',
        'port': 'auto',
        'baudrate': 'auto',
        'com_port': 'auto',
        'debug': False,
        'with_data_log': False,
        'console_log': False,
        'set_user_para': False,
        'ntrip_client': False,
        'force_bootloader': False,
        'para_path': None
    }


class DetectorArgs(KeyValuesArgumentBase):
    '''
    Argument define for detect device
    '''
    default_values = {
        'device_type': 'auto',
        'baudrate': 'auto',
        'com_port': 'auto'
    }


class LogParserArgs(KeyValuesArgumentBase):
    '''
    Argument define for log parser
    '''
    default_values = {
        'log_type': 'openrtk',
        'path': '.',
        'kml_rate': 5,
        'powerdr': 'false'
    }
