import time
from gpiozero import DistanceSensor

def turn_left_90(motor):
        motor.set_speed(-0.3,0.3)
        time.sleep(0.5)
        motor.stop()
        motor.set_speed(0.3,0.3)

        

# HC-SR04 超声波
# trig -> GPIO20
# echo -> GPIO21
# 返回单位：米
_sensor = DistanceSensor(
    trigger=20,
    echo=21,
    max_distance=4,
    queue_len=3
)

def get_distance():
    return _sensor.distance
