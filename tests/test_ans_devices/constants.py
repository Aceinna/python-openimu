import os

DEFAULT_PROCESS_TIMEOUT_SEC = 1
DEFAULT_TIME_TO_CHECK_FOR_ADDITIONAL_OUTPUT_SEC = 0.2
USING_WINDOWS = os.name == "nt"


class ProcessTimeoutError(ValueError):
    """Raised when no response is recieved from python driver after the timeout has been triggered"""

    pass
