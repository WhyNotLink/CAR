# joystick.py
import math

def joystick_to_speed(angle, strength, max_power=1.0):
    power = strength / 100.0 * max_power


    rad = math.radians(angle)

    x = math.cos(rad) * power   # 转向
    y = math.sin(rad) * power   # 前进

    left = y + x
    right = y - x

    max_val = max(abs(left), abs(right), 1.0)
    return left / max_val, right / max_val
