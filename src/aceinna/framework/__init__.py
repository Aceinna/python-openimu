import logging
from .app_logger import AppLogger

# disable logging from scapy
logging.getLogger("scapy").setLevel(logging.CRITICAL)
