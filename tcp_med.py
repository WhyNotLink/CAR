import socket
import pickle
import struct
import time
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

HOST = "0.0.0.0"
PORT = 9999

# ================== Mediapipe 初始化 ==================
MODEL_PATH = "hand_landmarker.task"
options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5,
)
detector = vision.HandLandmarker.create_from_options(options)

payload_size = struct.calcsize("Q")

def detect_gesture(hand):
    wrist = hand[0]
    mcp = hand[9]
    def dist(a, b):
        return ((a.x - b.x)**2 + (a.y - b.y)**2) ** 0.5
    palm = dist(wrist, mcp)
    tip_ids = [8, 12, 16, 20]
    straight = 0
    ratios = []
    for tid in tip_ids:
        r = dist(hand[tid], wrist) / palm
        ratios.append(r)
        if r > 1.55:
            straight += 1
    avg_ratio = sum(ratios)/len(ratios)
    if straight == 0 and avg_ratio < 1.25:
        return "FIST"
    elif straight >= 3 and avg_ratio > 1.55:
        return "OPEN"
    else:
        return "UNKNOWN"

# ================== TCP 长驻服务 ==================
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(5)
print(f"TCP服务启动，监听端口 {PORT}")

while True:
    print("等待小车连接...")
    conn, addr = server_socket.accept()
    print(f"小车已连接: {addr}")
    data = b""

    try:
        while True:
            # 接收消息长度
            while len(data) < payload_size:
                packet = conn.recv(4096)
                if not packet:
                    raise ConnectionResetError
                data += packet

            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

            # 接收整帧
            while len(data) < msg_size:
                packet = conn.recv(4096)
                if not packet:
                    raise ConnectionResetError
                data += packet
            frame_data = data[:msg_size]
            data = data[msg_size:]

            # 反序列化
            frame_dict = pickle.loads(frame_data)
            ts = frame_dict['timestamp']
            frame = frame_dict['frame']

            # 延迟
            latency = (time.time() - ts) * 1000

            # Mediapipe手势识别
            rgb = frame[:, :, ::-1]  # BGR->RGB
            result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
            gesture = "NO_HAND"
            if result.hand_landmarks:
                gesture = detect_gesture(result.hand_landmarks[0])

            # 打印延迟和手势
            print(f"延迟: {latency:.0f} ms | 手势: {gesture}")

    except (ConnectionResetError, BrokenPipeError):
        print("小车断开，等待新连接...")
        conn.close()
        continue
    except KeyboardInterrupt:
        print("服务终止")
        conn.close()
        break

server_socket.close()
detector.close()
