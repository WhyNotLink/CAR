# # motor.py
# from gpiozero import Motor, PWMOutputDevice




# 纯 Windows 模拟版 - 完全移除 gpiozero 依赖，适配你的 main.py
class PWMOutputDevice:
    """模拟 gpiozero.PWMOutputDevice 类，仅用于 Windows 测试"""
    def __init__(self, pin):
        self.pin = pin
        self._value = 0.0

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = max(0.0, min(1.0, val))
        

class Motor:
    """模拟 gpiozero.Motor 类，解决命名冲突问题"""
    def __init__(self, forward, backward):
        # 重命名属性，避免和 forward()/backward() 方法冲突
        self.forward_pin = forward
        self.backward_pin = backward
        

    def forward(self):
        pass

    def backward(self):
        pass

    def stop(self):
        pass




class CarMotor:
    def __init__(self, lf, lb, lpwm, rf, rb, rpwm):
        self.left_motor = Motor(forward=lf, backward=lb)
        self.left_pwm = PWMOutputDevice(lpwm)

        self.right_motor = Motor(forward=rf, backward=rb)
        self.right_pwm = PWMOutputDevice(rpwm)

    def _set_one(self, motor, pwm, speed):
        speed = max(-1.0, min(1.0, speed))
        if speed > 0:
            motor.forward()
            pwm.value = speed
        elif speed < 0:
            motor.backward()
            pwm.value = -speed
        else:
            motor.stop()
            pwm.value = 0

    def set_speed(self, left, right):
        self._set_one(self.left_motor, self.left_pwm, left)
        self._set_one(self.right_motor, self.right_pwm, right)
        print(f"Set speed: left={left:.2f}, right={right:.2f}")

    def stop(self):
        self.left_motor.stop()
        self.right_motor.stop()
        self.left_pwm.value = 0
        self.right_pwm.value = 0
