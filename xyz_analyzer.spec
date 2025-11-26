# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 收集Streamlit所需的所有数据文件
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

streamlit_datas = collect_data_files('streamlit')
altair_datas = collect_data_files('altair')

# 收集所有必要的隐藏导入
hiddenimports = [
    'streamlit',
    'streamlit.web.cli',
    'streamlit.runtime.scriptrunner.magic_funcs',
    'altair',
    'PIL',
    'PIL._tkinter_finder',
    'numpy',
    'matplotlib',
    'scipy',
    'scipy.ndimage',
    'scipy.special',
    'scipy.special.cython_special',
]

# 添加所有Streamlit子模块
hiddenimports += collect_submodules('streamlit')
hiddenimports += collect_submodules('altair')

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app.py', '.'),
        ('process_xyz.py', '.'),
    ] + streamlit_datas + altair_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='XYZ分析工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加自定义图标路径
)
