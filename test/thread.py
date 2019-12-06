import threading
import time
 
def thread1():
    while True:
        time.sleep(0.1)
        print(time.strftime('%H:%M:%S'),'hahaha')
 
def thread2():
    while True:
        time.sleep(0.2)
        print(time.strftime('%H:%M:%S'),'lalala')
 
def thread3():
    while True:
        time.sleep(0.1)
        print(time.strftime('%H:%M:%S'),'dadada')

threads = [thread1, thread2, thread3]
for th in threads:
    func = threading.Thread(target=th)
    func.start()