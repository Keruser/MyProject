import machine
import time
import ssd1306
from machine import Pin, PWM, ADC, SoftI2C

print("--- 智能停车系统 V5.1 (UI修复版) ---")

# =========================================
# 1. 硬件初始化
# =========================================
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=400000)
oled = None
try:
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
    oled.fill(0)
    oled.text("SYSTEM READY", 20, 25)
    oled.show()
except Exception as e:
    print("屏幕错误:", e)

servo_pin = PWM(Pin(15), freq=50)
buzzer_pin = PWM(Pin(4))
buzzer_pin.duty_u16(0)

# 按钮
btn_in = Pin(12, Pin.IN, Pin.PULL_UP)
btn_out = Pin(14, Pin.IN, Pin.PULL_UP)
mode_switch = Pin(27, Pin.IN, Pin.PULL_UP)
pot = ADC(Pin(34))
pot.atten(ADC.ATTN_11DB)

# =========================================
# 2. 全局变量
# =========================================
TOTAL_SPOTS = 5
current_free = 5
need_reset = False 

# =========================================
# 3. 功能函数
# =========================================

def gate_control(angle):
    duty = int(1638 + (angle / 180) * (8192 - 1638))
    servo_pin.duty_u16(duty)

def play_music(type):
    if type == 1: 
        for f in [523, 784]: 
            buzzer_pin.freq(f); buzzer_pin.duty_u16(30000); time.sleep_ms(80)
        buzzer_pin.duty_u16(0)
    elif type == 2:
        for f in [784, 523]:
            buzzer_pin.freq(f); buzzer_pin.duty_u16(30000); time.sleep_ms(100)
        buzzer_pin.duty_u16(0)
    elif type == 3:
        for _ in range(3):
            buzzer_pin.freq(2000); buzzer_pin.duty_u16(30000); time.sleep_ms(50)
            buzzer_pin.duty_u16(0); time.sleep_ms(50)

def update_screen(free, total, mode, angle=0):
    if not oled: return
    oled.fill(0)
    
    if mode == "AUTO":
        oled.text("SMART PARKING", 10, 0)
        oled.hline(0, 10, 128, 1)
        
        # 显示文字：Free (空闲)
        oled.text("Free: " + str(free) + "/" + str(total), 5, 25)
        
        # --- [关键修复] 进度条逻辑 ---
        # 外框宽度是 118 (从x=5开始，到x=123结束)
        oled.rect(5, 45, 118, 8, 1) # 画外框
        
        if total > 0:
            # 修复点：乘以 118 而不是 100，保证能填满整个框
            w = int((free / total) * 118)
            oled.fill_rect(5, 45, w, 8, 1) # 画填充
            
        if free == 0:
            oled.fill_rect(90, 20, 38, 15, 1) 
            oled.text("FULL", 92, 24, 0)      
            
    else:
        # 维护模式界面
        oled.fill_rect(0, 0, 128, 12, 1)
        oled.text("MAINTENANCE", 20, 2, 0)
        oled.text("Angle: " + str(angle), 10, 25)
        
        oled.rect(5, 45, 118, 8, 1)
        # 这里也同步修复，让维护模式的角度条也能填满
        w = int((angle / 180) * 118)
        oled.fill_rect(5, 45, w, 8, 1)
        
    oled.show()

# =========================================
# 4. 主循环
# =========================================
gate_control(0)
update_screen(current_free, TOTAL_SPOTS, "AUTO")
print("系统运行中...")

while True:
    # A. 维护模式
    if mode_switch.value() == 0:
        need_reset = True
        val = pot.read()
        angle = int((val / 4095) * 180)
        gate_control(angle)
        update_screen(0, 0, "MANUAL", angle)
        time.sleep(0.1) 
        continue 

    # B. 自动模式
    if need_reset:
        gate_control(0)
        update_screen(current_free, TOTAL_SPOTS, "AUTO")
        need_reset = False

    # 1. 进场
    if btn_in.value() == 0:
        time.sleep_ms(20)
        if btn_in.value() == 0:
            if current_free > 0:
                print(">>> 进场")
                play_music(1)
                gate_control(90)
                current_free -= 1
                update_screen(current_free, TOTAL_SPOTS, "AUTO")
                time.sleep(1.5)
                gate_control(0)
            else:
                print("!!! 满位")
                play_music(3)
                time.sleep(0.2)
            while btn_in.value() == 0: pass

    # 2. 出场
    elif btn_out.value() == 0:
        time.sleep_ms(20)
        if btn_out.value() == 0:
            if current_free < TOTAL_SPOTS:
                print("<<< 出场")
                play_music(2)
                gate_control(90)
                current_free += 1
                update_screen(current_free, TOTAL_SPOTS, "AUTO")
                time.sleep(1.5)
                gate_control(0)
            while btn_out.value() == 0: pass