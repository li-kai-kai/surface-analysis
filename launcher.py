"""
XYZ文件分析工具 - 启动器
自动启动Streamlit服务并提供系统托盘图标
"""

import sys
import os
import webbrowser
import threading
import time
import subprocess
from streamlit.web import cli as stcli
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item


def create_image():
    """创建一个简单的所有程序图标"""
    width = 64
    height = 64
    color1 = (255, 69, 0)  # 橙红色
    color2 = (255, 255, 255)  # 白色

    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)

    # 画一个简单的图形
    dc.rectangle((16, 16, 48, 48), fill=color2)
    dc.rectangle((24, 24, 40, 40), fill=color1)

    return image


def run_tray():
    """运行系统托盘图标"""
    image = create_image()
    menu = (item("Open", open_url), item("Quit", quit_app))
    # 使用英文标题避免 Linux/WSL 下的 Xlib 编码错误
    icon = pystray.Icon("name", image, "Surface Analyzer", menu)
    try:
        icon.run()
    except Exception as e:
        print(
            f"⚠️System tray icon failed to start (likely due to headless environment): {e}"
        )
        print("Running in headless mode. Press Ctrl+C to exit.")


def open_url():
    """打开浏览器访问应用"""
    # Give the server a moment to start before opening the browser
    time.sleep(2)
    webbrowser.open_new("http://localhost:8501")


def quit_app(icon, item):
    """退出应用程序"""
    icon.stop()
    # 强制退出进程，因为Streamlit运行在主进程中，需要彻底退出
    os._exit(0)


def main():
    """主启动函数"""
    is_frozen = getattr(sys, "frozen", False)

    if is_frozen:
        work_dir = sys._MEIPASS
    else:
        work_dir = os.path.dirname(os.path.abspath(__file__))

    os.chdir(work_dir)

    # 启动系统托盘 (在后台线程运行)
    # Streamlit 需要在主线程运行以处理信号
    tray_thread = threading.Thread(target=run_tray, daemon=True)
    tray_thread.start()

    # 启动浏览器 (延迟)
    browser_thread = threading.Thread(target=open_url, daemon=True)
    browser_thread.start()

    # 配置 Streamlit 参数
    streamlit_args = [
        "streamlit",
        "run",
        "app.py",
        "--server.headless=true",
        "--server.address=localhost",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
    ]

    if is_frozen:
        streamlit_args.extend(
            [
                "--server.fileWatcherType=none",
                "--global.developmentMode=false",
            ]
        )

    # 在主线程运行 Streamlit
    sys.argv = streamlit_args
    try:
        sys.exit(stcli.main())
    except SystemExit:
        pass


if __name__ == "__main__":
    main()
