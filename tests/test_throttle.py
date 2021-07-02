import sys
import time
try:
    from aceinna.framework.decorator import throttle
except:
    sys.path.append('./src')
    from aceinna.framework.decorator import throttle


@throttle(seconds=0.01)
def greeting():
    print('hello world', time.time())


if __name__ == '__main__':
    for i in range(100):
        greeting()
        time.sleep(0.001)
