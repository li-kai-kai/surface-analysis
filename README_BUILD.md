# 面形分析工具 - 打包说明

## 快速开始

### 方法一: 使用自动化脚本 (推荐)

1. **安装依赖**
   ```powershell
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. **运行打包脚本**
   ```powershell
   python build_exe.py
   ```

3. **获取可执行文件**
   - 打包完成后，可执行文件位于: `dist\面形分析工具.exe`
   - 直接双击运行即可

### 方法二: 手动打包

如果你想手动控制打包过程，可以按以下步骤操作:

1. **生成 spec 文件**
   ```powershell
   pyi-makespec --onefile --windowed --name "面形分析工具" launcher.py
   ```

2. **编辑 spec 文件**
   - 打开生成的 `面形分析工具.spec` 文件
   - 参考 `build_exe.py` 中的 spec 内容进行修改
   - 确保添加所有必要的 `hiddenimports` 和 `datas`

3. **执行打包**
   ```powershell
   pyinstaller --clean "面形分析工具.spec"
   ```

## 常见问题

### 1. 打包后运行报错 "No module named 'streamlit'"

**解决方案**: 确保 spec 文件中包含了所有 Streamlit 相关的隐藏导入:
```python
hiddenimports=[
    'streamlit',
    'streamlit.web.cli',
    'streamlit.runtime.scriptrunner.magic_funcs',
    # ... 其他导入
]
```

### 2. 打包后运行报错 "PackageNotFoundError"

**解决方案**: 在 spec 文件中添加 Streamlit 的数据文件:
```python
import streamlit
streamlit_path = os.path.dirname(streamlit.__file__)
a.datas += Tree(streamlit_path, prefix='streamlit', excludes=['*.pyc', '*.pyo', '__pycache__'])
```

### 3. 程序启动慢

这是正常现象。PyInstaller 打包的单文件程序需要:
- 解压临时文件到 `%TEMP%` 目录
- 加载所有依赖库
- 启动 Streamlit 服务器

首次启动可能需要 10-30 秒，这是正常的。

### 4. 防火墙警告

Windows 防火墙可能会提示允许网络访问，这是因为 Streamlit 需要启动本地服务器。请选择"允许访问"。

### 5. 文件大小较大

打包后的 exe 文件可能达到 200-500MB，这是因为包含了:
- Python 解释器
- Streamlit 框架
- NumPy, Matplotlib, SciPy 等科学计算库
- 所有依赖的数据文件

这是正常的，无法显著减小。

## 高级配置

### 添加应用图标

1. 准备一个 `.ico` 格式的图标文件
2. 在 spec 文件中修改:
   ```python
   exe = EXE(
       ...
       icon='path/to/your/icon.ico',
   )
   ```

### 显示控制台窗口 (用于调试)

在 spec 文件中修改:
```python
exe = EXE(
    ...
    console=True,  # 改为 True
)
```

### 优化文件大小

1. **使用 UPX 压缩** (已默认启用):
   ```python
   upx=True,
   ```

2. **排除不必要的模块**:
   ```python
   excludes=[
       'pytest',
       'setuptools',
       'pip',
       'wheel',
       'tkinter',  # 如果不需要
   ],
   ```

### 打包为文件夹模式 (更快的启动速度)

修改 spec 文件，将 `EXE` 改为 `COLLECT`:

```python
exe = EXE(
    pyz,
    a.scripts,
    [],  # 不包含 binaries 和 datas
    exclude_binaries=True,
    name='面形分析工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='面形分析工具',
)
```

这样会生成一个文件夹，启动速度更快，但需要分发整个文件夹。

## 分发说明

### 单文件分发 (默认)
- 优点: 只需分发一个 `.exe` 文件
- 缺点: 启动较慢，文件较大
- 适用: 给最终用户使用

### 文件夹分发
- 优点: 启动快，可以看到所有依赖
- 缺点: 需要分发整个文件夹
- 适用: 开发测试环境

## 测试清单

打包完成后，请测试以下功能:

- [ ] 程序能正常启动
- [ ] 浏览器自动打开
- [ ] 可以上传 .xyz 文件
- [ ] 参数调整正常
- [ ] 分析功能正常
- [ ] 图表生成正常
- [ ] 文件下载正常
- [ ] 程序可以正常关闭

## 技术细节

### 打包原理

1. **launcher.py**: 入口文件，负责启动 Streamlit
2. **app.py**: Streamlit 应用主文件
3. **process_xyz.py**: 数据处理模块
4. **PyInstaller**: 将所有 Python 代码和依赖打包成单个可执行文件

### 运行时流程

1. 用户双击 `面形分析工具.exe`
2. PyInstaller 解压文件到临时目录
3. `launcher.py` 启动
4. 启动 Streamlit 服务器 (localhost:8501)
5. 自动打开浏览器访问应用
6. 用户可以正常使用应用

### 依赖说明

主要依赖库:
- **streamlit**: Web 应用框架
- **numpy**: 数值计算
- **matplotlib**: 图表绘制
- **scipy**: 科学计算
- **Pillow**: 图像处理

## 故障排查

### 查看详细错误信息

1. 使用控制台模式运行:
   ```powershell
   # 在 spec 文件中设置 console=True 后重新打包
   ```

2. 或者在命令行中运行:
   ```powershell
   "dist\面形分析工具.exe"
   ```

### 清理缓存

如果遇到奇怪的问题，尝试清理缓存:
```powershell
# 删除构建目录
Remove-Item -Recurse -Force build, dist
# 删除 spec 文件
Remove-Item "面形分析工具.spec"
# 重新打包
python build_exe.py
```

## 联系支持

如果遇到无法解决的问题，请提供:
1. 错误信息截图
2. Python 版本: `python --version`
3. PyInstaller 版本: `pyinstaller --version`
4. 操作系统版本

---

**祝打包顺利! 🎉**
