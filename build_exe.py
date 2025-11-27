"""
PyInstaller 打包脚本
用于将 Streamlit 面形分析工具打包成 Windows 可执行文件

使用方法:
1. 确保已安装所有依赖: pip install -r requirements.txt
2. 安装 PyInstaller: pip install pyinstaller
3. 运行此脚本: python build_exe.py
"""

import os
import sys
import subprocess
import shutil

def clean_build_dirs():
    """清理之前的构建目录"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"清理目录: {dir_name}")
            shutil.rmtree(dir_name)
    
    # 清理旧的 spec 文件
    spec_file = 'surface_analyzer.spec'
    if os.path.exists(spec_file):
        print(f"删除旧的 spec 文件: {spec_file}")
        os.remove(spec_file)

def create_spec_file():
    """创建 PyInstaller spec 文件"""
    spec_content = """# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata

block_cipher = None

# 收集包元数据 - 这是修复 PackageNotFoundError 的关键
datas = []

# 尝试收集各个包的元数据，如果包不存在则跳过
packages_to_collect = [
    'streamlit',
    'numpy',
    'matplotlib',
    'scipy',
    'pillow',
]

for pkg in packages_to_collect:
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass  # 如果包没有元数据或不存在，跳过

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app.py', '.'),
        ('process_xyz.py', '.'),
        ('analyze_data.py', '.'),
    ] + datas,
    hiddenimports=[
        'streamlit',
        'streamlit.web.cli',
        'streamlit.runtime.scriptrunner.magic_funcs',
        'streamlit.runtime.scriptrunner.script_runner',
        'streamlit.runtime.state',
        'streamlit.runtime.state.session_state',
        'streamlit.runtime.state.session_state_proxy',
        'streamlit.runtime.uploaded_file_manager',
        'streamlit.components.v1',
        'streamlit.components.v1.components',
        'numpy',
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.backends.backend_agg',
        'scipy',
        'scipy.linalg',
        'PIL',
        'PIL.Image',
        'zipfile',
        'io',
        'tempfile',
        'webbrowser',
        'threading',
        'altair',
        'altair.vegalite.v5',
        'altair.vegalite.v5.api',
        'altair.vegalite.v5.schema',
        'altair.vegalite.v5.schema.core',
        'altair.vegalite.v5.schema.channels',
        'pyarrow',
        'pydeck',
        'tornado',
        'tornado.web',
        'tornado.websocket',
        'watchdog',
        'watchdog.observers',
        'watchdog.events',
        'click',
        'click.core',
        'toml',
        'validators',
        'packaging',
        'packaging.version',
        'packaging.specifiers',
        'packaging.requirements',
        'importlib_metadata',
        'cachetools',
        'gitpython',
        'pympler',
        'blinker',
        'requests',
        'protobuf',
        'google.protobuf',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'setuptools',
        'pip',
        'wheel',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 收集 Streamlit 的所有数据文件
import streamlit
streamlit_path = os.path.dirname(streamlit.__file__)

a.datas += Tree(streamlit_path, prefix='streamlit', excludes=['*.pyc', '*.pyo', '__pycache__'])

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='面形分析工具',
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
    icon=None,  # 可以在这里指定图标文件路径
)
"""
    
    spec_file = 'surface_analyzer.spec'
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"已创建 spec 文件: {spec_file}")
    return spec_file

def build_exe(spec_file):
    """使用 PyInstaller 构建可执行文件"""
    print("\n开始构建可执行文件...")
    print("这可能需要几分钟时间，请耐心等待...\n")
    
    cmd = ['pyinstaller', '--clean', spec_file]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print("\n✅ 构建成功!")
        print(f"可执行文件位置: dist\\面形分析工具.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 构建失败: {e}")
        return False
    except FileNotFoundError:
        print("\n❌ 错误: 未找到 PyInstaller")
        print("请先安装 PyInstaller: pip install pyinstaller")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("面形分析工具 - PyInstaller 打包脚本")
    print("=" * 60)
    print()
    
    # 检查是否在正确的目录
    required_files = ['launcher.py', 'app.py', 'process_xyz.py', 'requirements.txt']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print("❌ 错误: 缺少必要的文件:")
        for f in missing_files:
            print(f"  - {f}")
        print("\n请确保在项目根目录下运行此脚本!")
        sys.exit(1)
    
    # 清理旧的构建文件
    print("步骤 1/3: 清理旧的构建文件")
    clean_build_dirs()
    print()
    
    # 创建 spec 文件
    print("步骤 2/3: 创建 PyInstaller spec 文件")
    spec_file = create_spec_file()
    print()
    
    # 构建可执行文件
    print("步骤 3/3: 构建可执行文件")
    success = build_exe(spec_file)
    
    if success:
        print("\n" + "=" * 60)
        print("打包完成!")
        print("=" * 60)
        print("\n使用说明:")
        print("1. 可执行文件位于: dist\\面形分析工具.exe")
        print("2. 双击运行即可启动应用")
        print("3. 应用会自动在浏览器中打开")
        print("\n注意事项:")
        print("- 首次运行可能需要几秒钟启动")
        print("- 请确保防火墙允许程序运行")
        print("- 如需分发，可以直接复制 dist\\面形分析工具.exe 文件")
    else:
        print("\n打包失败，请检查错误信息")
        sys.exit(1)

if __name__ == '__main__':
    main()
