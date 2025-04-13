import win32gui
import socket
import time
from datetime import datetime
from config import *

class Sentinel:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.last_sent = 0

    def detect_popup(self):
        """使用FindWindow检测目标窗口"""
        hwnd = win32gui.FindWindow(TARGET_CLASS, None)
        return hwnd != 0  # 仅检测类名存在即可

    def run(self):
        while getattr(self, "running", True):
            try:
                if self.detect_popup():
                    current_time = time.time()
                    if current_time - self.last_sent > COOLDOWN:
                        self.send_alert()
                        self.last_sent = current_time
                time.sleep(CHECK_INTERVAL)
            except Exception as e:
                print(f"检测异常: {str(e)}")
                time.sleep(5)

    def send_alert(self):
        """发送UDP警报"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"[ALERT] {timestamp} 检测到隐私访问"
        self.sock.sendto(message.encode(), (UDP_IP, UDP_PORT))

    def stop(self):
        """停止监控"""
        self.running = False
        self.sock.close()

if __name__ == "__main__":
    sentinel = Sentinel()
    sentinel.run()