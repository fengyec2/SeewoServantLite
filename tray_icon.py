import sys
import pystray
from PIL import Image
import main
from config import ICON_PATH, APP_NAME

class TrayManager:
    def __init__(self):
        self.sentinel = main.Sentinel()
        self.icon = None

    def create_icon(self):
        """创建托盘图标"""
        image = Image.open(ICON_PATH) if ICON_PATH else Image.new('RGB', (64,64), 'white')
        menu = pystray.Menu(
            pystray.MenuItem('退出', self.on_exit)
        )
        self.icon = pystray.Icon(APP_NAME, image, APP_NAME, menu)

    def on_exit(self):
        """退出程序"""
        self.sentinel.stop()
        self.icon.stop()
        sys.exit()

    def run(self):
        """启动程序"""
        self.create_icon()
        self.icon.run_detached()
        self.sentinel.run()

if __name__ == "__main__":
    # 隐藏控制台窗口
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    
    tm = TrayManager()
    tm.run()