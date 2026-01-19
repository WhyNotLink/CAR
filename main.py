import socket
import threading
import time

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
                    print("RX:", msg)

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


def main():
    global running, server

    motor = CarMotor(
        config.LEFT_FORWARD,
        config.LEFT_BACKWARD,
        config.LEFT_PWM,
        config.RIGHT_FORWARD,
        config.RIGHT_BACKWARD,
        config.RIGHT_PWM
    )

    t = threading.Thread(target=socket_worker, daemon=True)
    t.start()

    try:
        while True:
            with lock:
                a = angle
                s = strength
                current_mode = mode
                last_time = last_recv_time

            # ========= 掉线保护 =========
            if time.time() - last_time > config.TIMEOUT_STOP:
                motor.stop()
                continue

            # ========= 自动模式 =========
            if current_mode == "auto":
                motor.stop()   # 以后自动控制逻辑放这里

            # ========= 手动模式 =========
            elif current_mode == "manual":
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