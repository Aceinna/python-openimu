class UPGRADE_EVENT:
    '''
    Event type of Device Message Center
    '''
    FIRST_PACKET = 'first_packet'
    BEFORE_WRITE = 'before_write'
    AFTER_WRITE = 'after_write'

    BEFORE_COMMAND='before_command'
    AFTER_COMMAND='after_command'

    FINISH = 'finish'
    ERROR = 'error'
    PROGRESS = 'progress'


class UPGRADE_GROUP:
    FIRMWARE = 'firmware'
    BEFORE_ALL = 'before_all'
    AFTER_ALL = 'after_all'


from .firmware_worker import FirmwareUpgradeWorker
from .ethernet_sdk_9100_worker import SDKUpgradeWorker as EthernetSDK9100UpgradeWorker
from .sdk_8100_worker import SDKUpgradeWorker as SDK8100UpgradeWorker
from .sdk_9100_worker import SDKUpgradeWorker as SDK9100UpgradeWorker
from .jump_application_worker import JumpApplicationWorker
from .jump_bootloader_worker import JumpBootloaderWorker

