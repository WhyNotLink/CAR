# config.py

# GPIO 定义
LEFT_FORWARD  = 22
LEFT_BACKWARD = 27
LEFT_PWM      = 18

RIGHT_FORWARD  = 24
RIGHT_BACKWARD = 25
RIGHT_PWM      = 23

# 网络
SERVER_PORT = 12345

# 控制参数
CONTROL_HZ = 50           # 控制频率
MAX_POWER = 0.6           # 最大速度
TIMEOUT_STOP = 0.5        # 失联自动停车（秒）
