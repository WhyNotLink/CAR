import cv2
import time
import os
import urllib.request
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ================== CONFIG ==================
STREAM_URL = "http://192.168.137.243:5000/video"
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
HEARTBEAT_TIMEOUT = 5
RECONNECT_INTERVAL = 2

MODEL_PATH = "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
# ================== CONFIG ==================
def detect_gesture(hand):
    wrist = hand[0]
    mcp = hand[9]  # 中指 MCP

    def dist(a, b):
        return ((a.x - b.x)**2 + (a.y - b.y)**2) ** 0.5

    palm = dist(wrist, mcp)

    tip_ids = [8, 12, 16, 20]  # 食指~小指
    straight = 0
    ratios = []

    for tid in tip_ids:
        r = dist(hand[tid], wrist) / palm
        ratios.append(r)
        if r > 1.55:
            straight += 1

    avg_ratio = sum(ratios) / len(ratios)

    if straight == 0 and avg_ratio < 1.25:
        return "FIST"
    elif straight >= 3 and avg_ratio > 1.55:
        return "OPEN"
    else:
        return "UNKNOWN"


# def detect_gesture(hand):
#     wrist = hand[0]
#     mid_mcp = hand[9]

#     def dist(a, b):
#         return ((a.x - b.x)**2 + (a.y - b.y)**2) ** 0.5

#     palm = dist(wrist, mid_mcp)

#     fingers = 0

#     # 食指~小指
#     for tip in [8, 12, 16, 20]:
#         if dist(hand[tip], wrist) / palm > 1.55:
#             fingers += 1

#     # 拇指（单独算）
#     if dist(hand[4], hand[2]) > palm * 0.45:
#         fingers += 1

#     if fingers == 0:
#         return "FIST"
#     elif fingers >= 4:
#         return "OPEN"
#     else:
#         return "UNKNOWN"



# ================== MODEL ==================
if not os.path.exists(MODEL_PATH):
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
    num_hands=2,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5,
)
detector = vision.HandLandmarker.create_from_options(options)

# ================== STREAM ==================
class NetworkStream:
    def __init__(self, url):
        self.url = url
        self.cap = None
        self.last_ok = 0
        self.connected = False
        self.reconnect_ts = 0
        self.connect()

    def connect(self):
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.connected = self.cap.isOpened()
        self.last_ok = time.time()
        self.reconnect_ts = time.time()

    def read(self):
        if not self.cap or not self.cap.isOpened():
            return False, None

        ret, frame = self.cap.read()
        if ret:
            self.last_ok = time.time()
            self.connected = True
            return True, cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

        if time.time() - self.last_ok > HEARTBEAT_TIMEOUT:
            self.connected = False
        return False, None

    def tick(self):
        if not self.connected and time.time() - self.reconnect_ts > RECONNECT_INTERVAL:
            self.connect()

    def release(self):
        if self.cap:
            self.cap.release()

# ================== UI ==================
blank = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), np.uint8)
cv2.putText(blank, "NETWORK DISCONNECTED", (80, FRAME_HEIGHT // 2),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

stream = NetworkStream(STREAM_URL)
prev = time.time()

# ================== LOOP ==================
try:
    while True:
        stream.tick()
        ok, frame = stream.read()

        if not ok:
            frame = blank.copy()
        else:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                result = detector.detect(
                    mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                )
                if result.hand_landmarks:
                    h, w, _ = frame.shape
                    for hand in result.hand_landmarks:
                        pts = []
                        for lm in hand:
                            x, y = int(lm.x * w), int(lm.y * h)
                            pts.append((x, y))
                            cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

                        gesture = detect_gesture(hand)
                        print("Gesture:", gesture)

                        cv2.putText(frame, gesture, (pts[0][0], pts[0][1] - 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

                        for s, e in mp.solutions.hands_landmark.HAND_CONNECTIONS:
                            cv2.line(frame, pts[s], pts[e], (255, 0, 0), 2)
            except Exception:
                pass

        now = time.time()
        fps = int(1 / (now - prev)) if now != prev else 0
        prev = now

        cv2.putText(frame, f"FPS: {fps}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        status = "ONLINE" if stream.connected else "OFFLINE"
        color = (0, 255, 0) if stream.connected else (0, 0, 255)
        cv2.putText(frame, f"STATUS: {status}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        cv2.imshow("MediaPipe Hand Tracking", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    stream.release()
    detector.close()
    cv2.destroyAllWindows()
