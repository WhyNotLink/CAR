import socket
import struct
import threading
import time
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from flask import Flask, Response
gesture_text = ""  # 用于网页叠加手势文字
gesture = "NO_HAND"
last_sent_gesture = "NO_HAND"

HOST = "0.0.0.0"
PORT = 8088

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

# ================== TCP 服务 ==================
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(5)
print(f"ECS服务启动，监听端口 {PORT}")

# 最新帧共享
latest_frame = None
latest_ts = 0
frame_lock = threading.Lock()

def handle_client(conn, addr):
    global latest_frame, latest_ts, gesture, last_sent_gesture
    print(f"小车已连接: {addr}")
    payload_size = struct.calcsize("dI")  # timestamp(double) + length(uint32)
    data = b""
    try:
        while True:
            # 接收头部
            while len(data) < payload_size:
                packet = conn.recv(4096)
                if not packet:
                    raise ConnectionResetError
                data += packet
            header = data[:payload_size]
            data = data[payload_size:]
            ts, length = struct.unpack("dI", header)

            # 接收帧数据
            while len(data) < length:
                packet = conn.recv(4096)
                if not packet:
                    raise ConnectionResetError
                data += packet
            frame_bytes = data[:length]
            data = data[length:]

            # 解码 JPEG
            frame = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
            with frame_lock:
                latest_frame = frame
                latest_ts = ts

                # if(gesture != last_sent_gesture):
                #     last_sent_gesture = gesture
                #     gesture_bytes = gesture.encode("utf-8")
                #     gesture_header = struct.pack("I", len(gesture_bytes))
                #     conn.sendall(gesture_header + gesture_bytes)
                #     print(f"发送手势: {gesture}")
                

    except (ConnectionResetError, BrokenPipeError):
        print("小车断开连接")
        conn.close()

def process_frames():
    global latest_frame, latest_ts, gesture, last_sent_gesture
    while True:
        with frame_lock:
            if latest_frame is None:
                continue
            frame = latest_frame.copy()
            ts = latest_ts
            latest_frame = None  # 丢掉旧帧

        latency = (time.time() - ts) * 1000  # ms

        # Mediapipe 手势识别
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        
        gesture = "NO_HAND" 
        if result.hand_landmarks:
            hand = result.hand_landmarks[0]

            # 手势识别函数
            wrist = hand[0]
            mcp = hand[9]
            def dist(a, b):
                return ((a.x - b.x)**2 + (a.y - b.y)**2)**0.5
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
                gesture = "FIST"
            elif straight >= 3 and avg_ratio > 1.55:
                gesture = "OPEN"
            else:
                gesture = "UNKNOWN"

        # 只打印非 NO_HAND
        if gesture != "NO_HAND":
            print(f"延迟: {latency:.0f} ms | 手势: {gesture}")
        
            if gesture != last_sent_gesture:
                last_sent_gesture = gesture
                if conn:
                    try:
                        gesture_bytes = gesture.encode("utf-8")
                        gesture_header = struct.pack("I", len(gesture_bytes))
                        conn.sendall(gesture_header + gesture_bytes)
                        print(f"发送手势: {gesture}")
                    except:
                        pass


# # ================== Flask MJPEG Web ==================
# app = Flask(__name__)

# def generate_mjpeg():
#     global latest_frame, gesture_text
#     while True:
#         with frame_lock:
#             if latest_frame is None:
#                 continue
#             frame = latest_frame.copy()
#             text = gesture_text

#         # 在画面上叠加手势文字
#         if text:
#             cv2.putText(frame, text, (10, 30),
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

#         ret, jpeg = cv2.imencode('.jpg', frame)
#         if not ret:
#             continue
#         frame_bytes = jpeg.tobytes()

#         # MJPEG 多部分格式
#         yield (b'--frame\r\n'
#                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# @app.route('/video')
# def video_feed():
#     return Response(generate_mjpeg(),
#                     mimetype='multipart/x-mixed-replace; boundary=frame')

# # 启动 Flask 服务线程
# threading.Thread(target=lambda: app.run(host="0.0.0.0", port=7000, threaded=True), daemon=True).start()


# 启动处理线程
threading.Thread(target=process_frames, daemon=True).start()

# 等待客户端连接
while True:
    conn, addr = server_socket.accept()
    threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
