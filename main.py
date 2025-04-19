import win32gui
import time
from datetime import datetime
import threading
import asyncio
import websockets
from config import *

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
        return hwnd != 0

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

async def main():
    sentinel = Sentinel()

    server = await websockets.serve(handler, "0.0.0.0", 8765)
    print("WebSocket服务器启动，监听端口 8765")

    sentinel_task = asyncio.create_task(sentinel.run_loop())

    try:
        await asyncio.Future()  # 程序阻塞直到取消
    except KeyboardInterrupt:
        print("收到退出信号，正在关闭...")
    finally:
        sentinel.stop()
        sentinel_task.cancel()
        server.close()
        await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())