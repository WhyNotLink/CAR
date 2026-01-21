import socket
import threading
import time
import cv2
import struct

from motor import CarMotor
from joystick import joystick_to_speed
import config

from tripod import get_distance, turn_left_90

# ===== 全局变量 =====
angle = 0
strength = 0
last_recv_time = time.time()
mode = "auto"  # auto / manual
running = True
lock = threading.Lock()
conn = None
server = None
cap = None
client_socket = None
ult_flag = False

FPS = 10
frame_interval = 1.0 / FPS

motor = CarMotor(
    config.LEFT_FORWARD,
    config.LEFT_BACKWARD,
    config.LEFT_PWM,
    config.RIGHT_FORWARD,
    config.RIGHT_BACKWARD,
    config.RIGHT_PWM
)

auto_left = 0
auto_right = 0
ECS_IP = "47.105.118.110"
ECS_PORT = 8088


# ===== ECS 视频发送线程 =====
def ecs_sender_worker():
    global cap, client_socket, running, mode
    while running:
        if mode != "auto":
            time.sleep(0.05)
            continue

        if cap is None:
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

        if client_socket is None:
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(5)
                client_socket.connect((ECS_IP, ECS_PORT))
            except:
                client_socket = None
                time.sleep(1)
                continue

        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(frame_interval)
            continue

        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        frame_bytes = buffer.tobytes()
        header = struct.pack("dI", time.time(), len(frame_bytes))
        try:
            client_socket.sendall(header + frame_bytes)
        except:
            try: client_socket.close()
            except: pass
            client_socket = None

        time.sleep(frame_interval)


# ===== 手机控制线程 =====
def socket_worker():
    global angle, strength, last_recv_time, mode, running, conn, server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('', config.SERVER_PORT))
    server.listen(1)
    server.settimeout(1.0)
    
    while running:
        try:
            conn, addr = server.accept()
            last_recv_time = time.time()
            f = conn.makefile('r')

            while running:
                line = f.readline()
                if not line:
                    break
                msg = line.strip()
                with lock:
                    last_recv_time = time.time()

                if msg == "s":
                    mode = "manual"
                    conn.sendall(b"s\n")
                elif msg == "z":
                    mode = "auto"
                    angle = 0
                    strength = 0
                    conn.sendall(b"z\n")
                elif msg.startswith("angle:") and mode == "manual":
                    parts = msg.split(',')
                    angle = int(parts[0].split(':')[1])
                    strength = int(parts[1].split(':')[1])

            f.close()
            conn.close()
            conn = None

        except:
            print("APP连接断开")
            time.sleep(1)


# ===== ECS 手势控制线程 =====
def ecs_receiver_worker():
    global client_socket, running, mode, motor, ult_flag
    while running:
        if client_socket is None:
            time.sleep(0.1)
            continue

        try:
            header = client_socket.recv(4)
            if not header or len(header) < 4:
                time.sleep(0.05)
                continue

            length = struct.unpack("I", header)[0]
            data = b""
            while len(data) < length:
                packet = client_socket.recv(length - len(data))
                if not packet:
                    break
                data += packet

            msg = data.decode("utf-8")
            with lock:
                if mode == "auto":
                    if msg == "FIST":
                        print("停车")
                        ult_flag = False
                        motor.stop()
                    elif msg == "OPEN":
                        print("前进")
                        ult_flag = True
                        motor.set_speed(0.3, 0.3)

        except:
            print("ECS 连接断开")
            time.sleep(0.1)


# ===== 主程序 =====
def main():
    global running, conn, server, motor

    threading.Thread(target=socket_worker, daemon=True).start()
    threading.Thread(target=ecs_sender_worker, daemon=True).start()
    threading.Thread(target=ecs_receiver_worker, daemon=True).start()

    try:
        while True:
            with lock:
                a = angle
                s = strength
                current_mode = mode
                conn_alive = conn is not None
                ecs_alive = client_socket is not None

            if current_mode == "auto" and not ecs_alive:
                motor.stop()
                time.sleep(1 / config.CONTROL_HZ)
                continue

            if current_mode == "auto" and ult_flag == True:
                dist = get_distance()
                print(f"Distance: {dist:.2f} m")
                if(dist<=0.2):
                    turn_left_90(motor)

            if current_mode == "manual":
                with lock:
                    left, right = joystick_to_speed(a, s, config.MAX_POWER)
                    motor.set_speed(left, right)

            time.sleep(1 / config.CONTROL_HZ)

    except KeyboardInterrupt:
        running = False
        try: conn.close()
        except: pass
        try: server.close()
        except: pass
        motor.stop()


if __name__ == "__main__":
    main()
