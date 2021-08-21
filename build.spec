# -*- mode: python -*-
import sys
import os.path as osp
sys.setrecursionlimit(5000)

block_cipher = None
root_path = os.path.join(os.getcwd(),'src')

a = Analysis([os.path.join(root_path,'aceinna','executor.py'),
         ],
         pathex=[root_path],
         binaries=[],
         datas=[
            (os.path.join(root_path,'aceinna','setting'), os.path.join('setting')),
            (os.path.join(root_path,'aceinna','libs'), os.path.join('libs'))
         ],
         hiddenimports=[],
         hookspath=[],
         runtime_hooks=[],
         excludes=[],
         win_no_prefer_redirects=False,
         win_private_assemblies=False,
         cipher=block_cipher,
         noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
         cipher=block_cipher)
exe = EXE(pyz,
         a.scripts,
         a.binaries,
         a.zipfiles,
         a.datas,
         [],
         name='ans-devices',
         debug=False,
         bootloader_ignore_signals=False,
         strip=False,
         upx=True,
         upx_exclude=[],
         runtime_tmpdir=None,
         console=True,
         icon='aceinna.ico')
