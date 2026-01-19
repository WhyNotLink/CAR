import socket
import threading
import time
import cv2
import struct

from motor import CarMotor
from joystick import joystick_to_speed
import config

angle = 0
strength = 0
last_recv_time = time.time()

mode = "auto"      # auto / manual
running = True
lock = threading.Lock()
conn = None
server = None  

# ======== 自动模式视频发送配置 ========
ECS_IP = "47.105.118.110"
ECS_PORT = 8088
cap = None
client_socket = None
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

auto_left=0
auto_right=0
# def init_camera_and_socket():
#     global cap, client_socket
#     cap = cv2.VideoCapture(0)
#     cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
#     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

#     client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     client_socket.connect((ECS_IP, ECS_PORT))

# def send_frame_to_ecs():
#     global cap, client_socket
#     if cap is None or client_socket is None:
#         return
#     ret, frame = cap.read()
#     if not ret:
#         print("摄像头读取失败")
#         return
#     _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
#     frame_bytes = buffer.tobytes()
#     timestamp = time.time()
#     header = struct.pack("dI", timestamp, len(frame_bytes))
#     try:
#         client_socket.sendall(header + frame_bytes)
#     except:
#         print("发送失败")
#         # 发送失败不影响主程序
#         # pass


# ============================================
def ecs_sender_worker():
    global cap, client_socket, running, mode
    while running:
        if mode != "auto":
            time.sleep(0.05)  
            continue

        # 初始化摄像头和socket
        if cap is None:
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

        if client_socket is None:
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(5)
                client_socket.connect((ECS_IP, ECS_PORT))
                print("ECS 连接成功")
            except Exception as e:
                print("ECS 连接失败:", e)
                client_socket = None
                time.sleep(1)
                continue

        # 读取摄像头
        ret, frame = cap.read()
        if not ret or frame is None:
            print("摄像头读取失败")
            time.sleep(frame_interval)
            continue

        # 编码发送
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        frame_bytes = buffer.tobytes()
        timestamp = time.time()
        header = struct.pack("dI", timestamp, len(frame_bytes))
        try:
            client_socket.sendall(header + frame_bytes)
            # print(f"发送帧大小: {len(frame_bytes)} bytes")
        except Exception as e:
            print("发送 ECS 失败:", e)
            try: client_socket.close()
            except: pass
            client_socket = None

        time.sleep(frame_interval)


def socket_worker():
    global angle, strength, last_recv_time, mode, running, conn, server

    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('', config.SERVER_PORT))
    server.listen(1)

    print(f"等待手机连接（端口：{config.SERVER_PORT}）...")

    
    while running:
        try:
            conn, addr = server.accept()
            print("已连接:", addr)
            last_recv_time = time.time()  # 重置超时时间
            f = conn.makefile('r')

            
            while running:
                try:
                    line = f.readline()
                    if not line:  
                        break

                    msg = line.strip()
                    # print("RX:", msg)

                    with lock:
                        last_recv_time = time.time()

                    # ========= 切换手动 =========
                    if msg == "s":
                        with lock:
                            mode = "manual"
                        conn.sendall(b"s\n")
                        print("切换为 MANUAL")

                    # ========= 切换自动 =========
                    elif msg == "z":
                        with lock:
                            mode = "auto"
                            angle = 0
                            strength = 0
                        conn.sendall(b"z\n")
                        print("切换为 AUTO")

                    # ========= 摇杆数据 =========
                    elif msg.startswith("angle:"):
                        with lock:
                            if mode == "manual":
                                parts = msg.split(',')
                                angle = int(parts[0].split(':')[1])
                                strength = int(parts[1].split(':')[1])
                    # auto 模式直接忽略

                except Exception as e:
                    print("处理消息错误:", e)
                    break

            
            f.close()
            conn.close()
            conn = None  
            print("等待新的手机连接...")

        except Exception as e:
            if running:  
                print(f"Socket 监听错误: {e}")
                time.sleep(1) 



def ecs_receiver_worker():
    global client_socket, running, mode, motor, auto_left, auto_right

    while running:
        if client_socket is None:
            time.sleep(0.1)
            continue

        try:
            # 读取 ECS 发来的消息（先读取长度再读取内容）
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
            print(f"ECS消息: {msg}")

            # ======== 根据 ECS 手势控制小车 =========
            with lock:
                if mode == "auto":
                    if msg == "FIST":
                        # 停车
                        print("停车")
                        motor.stop()                
                    elif msg == "OPEN":
                        print("前进")
                        motor.set_speed(0.3,0.3)    
                        # 前进
                   

        except Exception as e:
            # ECS 断开或异常
            # print("接收 ECS 失败:", e)
            time.sleep(0.1)


def main():
    global running, server, motor, auto_left, auto_right


    t = threading.Thread(target=socket_worker, daemon=True)
    t.start()

    threading.Thread(target=ecs_sender_worker, daemon=True).start()
    threading.Thread(target=ecs_receiver_worker, daemon=True).start()

    # init_camera_and_socket()

    try:
        while True:
            with lock:
                a = angle
                s = strength
                current_mode = mode
                last_time = last_recv_time

            # ========= 掉线保护 =========
            # if time.time() - last_time > config.TIMEOUT_STOP:
            #     motor.stop()
            #     continue

            with lock:
                current_mode = mode
                conn_alive = conn is not None        # 手机连接
                ecs_alive = client_socket is not None  # ECS连接
            
            if current_mode == "auto" and (not ecs_alive):
                print("掉线保护触发：ECS 未连接，停车")
                motor.stop()
                continue

            # ========= 自动模式 =========
            if current_mode == "auto":
                pass
                # motor.stop()   
                # send_frame_to_ecs()

            # ========= 手动模式 ======
            elif current_mode == "manual":
                with lock:
                    left, right = joystick_to_speed(a, s, config.MAX_POWER)
                    motor.set_speed(left, right)

            time.sleep(1 / config.CONTROL_HZ)

    except KeyboardInterrupt:
        print("退出中...")
        running = False

        if conn:
            try:
                conn.close()
            except:
                pass
        if server:
            try:
                server.close()
            except:
                pass
        motor.stop()
        t.join(timeout=2)


if __name__ == "__main__":
    main()