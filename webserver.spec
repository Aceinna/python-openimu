# -*- mode: python -*-
import sys
import os.path as osp
sys.setrecursionlimit(5000)

block_cipher = None
root_path = os.getcwd()

a = Analysis(['webserver.py',
            os.path.join(os.getcwd(), 'openimu', 'bootloader_input_packet.py'),
            os.path.join(os.getcwd(), 'openimu', 'commands.py'),
            os.path.join(os.getcwd(), 'openimu', 'file_storage.py'),
            os.path.join(os.getcwd(), 'openimu', 'global_vars.py'),
            os.path.join(os.getcwd(), 'openimu','imu_input_packet.py'),
            os.path.join(os.getcwd(), 'openimu','openimu.py'),
            os.path.join(os.getcwd(), 'openimu','predefine.py'),
            os.path.join(os.getcwd(), 'openimu','quat.py'),
            os.path.join(os.getcwd(), 'openimu','server.py')
         ],
         pathex=[root_path],
         binaries=[],
         datas=[
            (os.path.join(root_path, 'app_config'),'app_config')
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
         name='openimu-server',
         debug=False,
         bootloader_ignore_signals=False,
         strip=False,
         upx=True,
         upx_exclude=[],
         runtime_tmpdir=None,
         console=True )
