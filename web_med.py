import cv2
import time
import os
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ================== CONFIG ==================
STREAM_URL = "http://47.105.118.110:8088/video"
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

MODEL_PATH = "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)

# ================== GESTURE ==================
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

# ================== MODEL ==================
if not os.path.exists(MODEL_PATH):
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
    num_hands=1,  # 服务器端建议 1
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5,
)
detector = vision.HandLandmarker.create_from_options(options)

# ================== STREAM ==================
cap = cv2.VideoCapture(STREAM_URL)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# ================== LOOP ==================
try:
    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.01)
            continue

        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        result = detector.detect(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        )

        if result.hand_landmarks:
            for hand in result.hand_landmarks:
                gesture = detect_gesture(hand)
                print(gesture)

except KeyboardInterrupt:
    pass

finally:
    cap.release()
    detector.close()
