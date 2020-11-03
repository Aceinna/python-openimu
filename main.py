import os
import sys
import runpy

setattr(sys, '__dev__', True)

SRC_PATH = os.path.join(os.getcwd(), 'src')
EXECUTOR_PATH = os.path.join(SRC_PATH, 'aceinna', 'executor.py')

sys.path.append('./src')
runpy.run_path(EXECUTOR_PATH, run_name='__main__')
