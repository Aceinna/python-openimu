# -*- mode: python -*-
import sys
import os.path as osp
sys.setrecursionlimit(5000)

block_cipher = None
root_path = os.path.join(os.getcwd(),'src')

a = Analysis([os.path.join(root_path,'aceinna','executor.py'),
            # os.path.join(os.getcwd(), 'src', 'bootstrap/base.py'),
            # os.path.join(os.getcwd(), 'src', 'bootstrap/cli.py'),
            # os.path.join(os.getcwd(), 'src', 'bootstrap/loader.py'),
            # os.path.join(os.getcwd(), 'src', 'bootstrap/web.py'),
            # os.path.join(os.getcwd(), 'src','devices', 'base/uart_base.py'),
            # os.path.join(os.getcwd(), 'src','devices', 'configs/openimu_predefine.py'),
            # os.path.join(os.getcwd(), 'src','devices', 'configs/openrtk_predefine.py'),
            # os.path.join(os.getcwd(), 'src','devices', 'openimu/uart_provider.py'),
            # os.path.join(os.getcwd(), 'src','devices', 'openrtk/uart_provider.py'),
            # os.path.join(os.getcwd(), 'src','devices', 'device_manager.py'),
            # os.path.join(os.getcwd(), 'src','framework', 'communicator.py'),
            # os.path.join(os.getcwd(), 'src','framework', 'context.py'),
            # os.path.join(os.getcwd(), 'src','framework', 'file_storage.py'),
            # os.path.join(os.getcwd(), 'src','framework', 'utils/helper.py'),
         ],
         pathex=[root_path],
         binaries=[],
         datas=[
            (os.path.join(root_path,'aceinna','setting'), os.path.join('setting'))
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
