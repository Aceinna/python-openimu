import sys
import time

try:
    raise Exception('use local code')
except:
    sys.path.append('./src')
    from aceinna.tools import Detector


def on_find_device(device):
    '''
    callback after find device
    '''
    device.setup(None)

    device.mag_align_start()
    time.sleep(1)
    print('[Ready] Mag align started, please do the operation')

    while device.is_mag_align:
        time.sleep(0.1)

    print('[Complete] Mag align completed, start to save the result')
    device.mag_align_save()
    # device.mag_align_abort() # or you can try to use abort operation to restore the result
    print('[Saved] Mag align result saved')

    print('[Waiting] Sleep 5 sec, to wait device ready')
    time.sleep(5)

    param_list = device.get_params()
    # print(param_list) # print the gA result

    if param_list:
        if param_list['packetType'] == 'error':
            print('[Fail] cannot read param list with gA')

        if param_list['packetType'] == 'inputParams':
            print('[Pass] param len {0}'.format(len(param_list['data'])))

    device.close()


def simple_start():
    detector = Detector()
    detector.find(on_find_device)

if __name__ == '__main__':
    simple_start()
    # parameters_start()
