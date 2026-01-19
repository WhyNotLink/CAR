import cv2
import socket
import struct
import time

ECS_IP = "47.105.118.110"
ECS_PORT = 8088

# TCP 连接
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((ECS_IP, ECS_PORT))

# 摄像头
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

FPS = 20
frame_interval = 1.0 / FPS

try:
    while True:
        start_time = time.time()
        ret, frame = cap.read()
        if not ret:
            continue

        # JPEG 压缩
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        frame_bytes = buffer.tobytes()

        # 消息结构: timestamp + frame length + frame bytes
        timestamp = time.time()
        header = struct.pack("dI", timestamp, len(frame_bytes))
        client_socket.sendall(header + frame_bytes)

        # 控制帧率
        elapsed = time.time() - start_time
        sleep_time = frame_interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

except KeyboardInterrupt:
    print("小车端退出")
finally:
    cap.release()
    client_socket.close()
