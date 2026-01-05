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
    time.sleep(2)
    webbrowser.open_new("http://localhost:8501")

def main():
    """主启动函数"""
    is_frozen = getattr(sys, 'frozen', False)
    
    if is_frozen:
        work_dir = sys._MEIPASS
    else:
        work_dir = os.path.dirname(os.path.abspath(__file__))
    
    os.chdir(work_dir)
    
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    streamlit_args = [
        "streamlit",
        "run",
        "app.py",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]
    
    if is_frozen:
        streamlit_args.extend([
            "--server.fileWatcherType=none",
            "--global.developmentMode=false", 
        ])
    
    sys.argv = streamlit_args
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
