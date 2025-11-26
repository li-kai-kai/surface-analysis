"""
XYZ文件分析工具 - 启动器
自动启动Streamlit服务并打开浏览器
"""
import sys
import os
import webbrowser
import threading
import time
from streamlit.web import cli as stcli

def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)  # 等待服务器启动
    webbrowser.open_new("http://localhost:8501")

def main():
    """主启动函数"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe (onefile模式), 资源文件解压在 sys._MEIPASS
        work_dir = sys._MEIPASS
    else:
        # 如果是开发环境
        work_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 切换工作目录以便Streamlit能找到app.py
    os.chdir(work_dir)
    
    # 在后台线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # 启动Streamlit
    sys.argv = [
        "streamlit",
        "run",
        "app.py",
        "--server.headless=true",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none"  # 禁用文件监视以提高性能
    ]
    
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
