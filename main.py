import os
import win32gui
import time
from datetime import datetime
import threading
import asyncio
import websockets
import json
import sys

from PIL import Image, ImageDraw
import pystray

# 载入配置
def load_config(filepath='config.json'):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS  # PyInstaller临时目录
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_path, filepath)
    with open(full_path, 'r', encoding='utf-8') as f:
        return json.load(f)

config = load_config()

TARGET_CLASS = config.get("TARGET_CLASS", "ATL:00007FF637DAA9A0")
CHECK_INTERVAL = config.get("CHECK_INTERVAL", 0.5)
HEARTBEAT_INTERVAL = config.get("HEARTBEAT_INTERVAL", 60)
COOLDOWN = config.get("COOLDOWN", 2)
TRAY_TOOLTIP = config.get("TRAY_TOOLTIP", "火绒剑")

CLIENTS = set()
CLIENTS_LOCK = threading.Lock()

async def notify_clients(message: str):
    with CLIENTS_LOCK:
        clients = list(CLIENTS)
    if clients:
        await asyncio.wait([client.send(message) for client in clients])

async def handler(websocket, path):
    with CLIENTS_LOCK:
        CLIENTS.add(websocket)
    print(f"客户端连接: {websocket.remote_address}")
    try:
        async for message in websocket:
            print(f"收到客户端消息: {message}")
    except websockets.ConnectionClosed:
        pass
    finally:
        with CLIENTS_LOCK:
            CLIENTS.remove(websocket)
        print(f"客户端断开: {websocket.remote_address}")

class Sentinel:
    def __init__(self):
        self.last_sent = 0
        self.last_heartbeat = 0
        self.running = True

    def detect_popup(self):
        hwnd = win32gui.FindWindow(TARGET_CLASS, None)
        if hwnd != 0:
            # print(f"检测到窗口: {TARGET_CLASS}")
            return True
        else:
            # print(f"未检测到窗口: {TARGET_CLASS}")
            return False

    async def send_alert(self):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"[ALERT] {timestamp} 检测到隐私访问"
        print(f"发送警报消息: {message}")
        await notify_clients(message)

    async def send_heartbeat(self):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"[HEARTBEAT] {timestamp} 检测端正常运行"
        print(f"发送心跳消息: {message}")
        await notify_clients(message)

    async def run_loop(self):
        while self.running:
            current_time = time.time()

            if current_time - self.last_heartbeat >= HEARTBEAT_INTERVAL:
                await self.send_heartbeat()
                self.last_heartbeat = current_time

            if self.detect_popup():
                if current_time - self.last_sent > COOLDOWN:
                    await self.send_alert()
                    self.last_sent = current_time

            await asyncio.sleep(CHECK_INTERVAL)

    def stop(self):
        self.running = False
        print("服务已停止")

def create_image():
    # fallback 图标，16x16像素，白底黑点
    width = 16
    height = 16
    color1 = (0, 0, 0)
    color2 = (255, 255, 255)

    image = Image.new('RGB', (width, height), color2)
    dc = ImageDraw.Draw(image)

    dc.ellipse([2, 2, width-2, height-2], fill=color1)
    return image

def get_icon_path():
    if getattr(sys, 'frozen', False):
        # PyInstaller打包后的临时路径
        base_path = sys._MEIPASS
    else:
        # 普通运行时路径
        base_path = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_path, 'resources', 'icon.ico')
    if not os.path.exists(icon_path):
        print(f"警告：图标文件不存在: {icon_path}，将使用默认绘制图标")
        return None
    return icon_path

def run_tray_icon(stop_func):
    def on_quit(icon, item):
        print("托盘退出菜单被点击，准备关闭程序...")
        stop_func()
        icon.stop()

    icon_path = get_icon_path()
    if icon_path:
        # 关键修改：这里用 Image.open 加载图标文件
        try:
            image = Image.open(icon_path)
        except Exception as e:
            print(f"加载图标失败: {e}，使用默认绘制图标")
            image = create_image()
        icon = pystray.Icon("monitor", image, TRAY_TOOLTIP, menu=pystray.Menu(
            pystray.MenuItem("退出", on_quit)
        ))
    else:
        icon = pystray.Icon("monitor", create_image(), TRAY_TOOLTIP, menu=pystray.Menu(
            pystray.MenuItem("退出", on_quit)
        ))

    icon.run()

async def main_async(stop_event):
    sentinel = Sentinel()

    server = await websockets.serve(handler, "0.0.0.0", 8765)
    print("WebSocket服务器启动，监听端口 8765")
    sentinel_task = asyncio.create_task(sentinel.run_loop())

    await stop_event.wait()  # 等待退出信号

    sentinel.stop()
    sentinel_task.cancel()
    server.close()
    await server.wait_closed()

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    stop_event = asyncio.Event()

    def stop_all():
        # 线程安全设置退出事件
        loop.call_soon_threadsafe(stop_event.set)

    # 启动托盘线程（后台）
    tray_thread = threading.Thread(target=run_tray_icon, args=(stop_all,), daemon=True)
    tray_thread.start()

    try:
        loop.run_until_complete(main_async(stop_event))
    except asyncio.CancelledError:
        pass
    finally:
        loop.close()
        print("程序已退出")

if __name__ == "__main__":
    main()