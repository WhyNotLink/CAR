import cv2
import numpy as np

cap = cv2.VideoCapture("http://192.168.137.243:5000/video")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # 例：检测红色
    lower = np.array([0, 120, 70])
    upper = np.array([10, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)

    contours, _ = cv2.findContours(mask,
                                   cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        c = max(contours, key=cv2.contourArea)
        x,y,w,h = cv2.boundingRect(c)
        cx = x + w // 2
        cy = y + h // 2

        cv2.rectangle(frame, (x,y), (x+w,y+h), (255,0,0), 2)
        cv2.circle(frame, (cx,cy), 5, (0,0,255), -1)
        print("RED", cx, cy)

    cv2.imshow("color", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break
