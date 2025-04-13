import socket

UDP_IP = "0.0.0.0"  # 监听所有网卡
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("警报接收端已启动，等待消息...")
while True:
    data, addr = sock.recvfrom(1024)
    print(f"收到来自 {addr} 的警报: {data.decode()}")