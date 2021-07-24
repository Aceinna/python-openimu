import os
from ..tools.openrtk_parse import do_parse as do_parse_openrtk_logs
from ..tools.rtkl_parse import do_parse as do_parse_rtkl_logs
from ..tools.ins401_parse import do_parse as do_parse_ins401_logs
from ..models import LogParserArgs
from ..framework.constants import APP_TYPE
from ..framework.context import APP_CONTEXT

class LogParser:
    _options = None
    _tunnel = None
    _driver = None

    def __init__(self, **kwargs):
        self._build_options(**kwargs)
        APP_CONTEXT.mode = APP_TYPE.DEFAULT

    def listen(self):
        '''Start to do parse
        '''
        self._validate_params()

        setting_file = 'log-parser.json'

        if self._options.log_type == 'openrtk':
            do_parse_openrtk_logs(self._options.path,
                                  self._options.kml_rate,
                                  setting_file)
        elif self._options.log_type == 'rtkl':
            do_parse_rtkl_logs(self._options.path,
                               self._options.kml_rate,
                               setting_file)
        elif self._options.log_type == 'ins401':
            do_parse_ins401_logs(self._options.path,
                               self._options.kml_rate,
                               setting_file)
        else:
            raise ValueError('No matched log parser')

        os._exit(1)

    def _validate_params(self):
        for attr_name in ['log_type', 'path', 'kml_rate']:
            attr_value = getattr(self._options, attr_name)
            if not attr_value:
                raise ValueError(
                    'Parameter {0} should have a value'.format(attr_name))

    def _build_options(self, **options):
        self._options = LogParserArgs(**options)
