# -*- coding: utf-8 -*-

import time
import threading
from pynput import mouse, keyboard
import vgamepad as vg

# --------------------------------------------------------------------------------
# 设置区域 - 您可以在这里轻松调整参数
# --------------------------------------------------------------------------------

# 鼠标移动转换为手柄摇杆的倍率（灵敏度）
# 数值越大，鼠标轻微移动时手柄摇杆的反应幅度就越大
MOUSE_SENSITIVITY_X = 50

# 鼠标上下移动转换为手柄扳机键的倍率（灵敏度）
# 数值越大，鼠标轻微移动时手柄扳机的按下深度就越大
# 数值为0时关闭扳机转换功能
MOUSE_SENSITIVITY_TRIGGER = 1

# 【新增】定义一个用于将摇杆和扳机复位的按键
# 按下此键后，所有累加的鼠标输入将被清零，手柄会回中
RESET_KEY = keyboard.Key.f8

# 键盘按键映射
# 格式为: '键盘按键': vg.XUSB_BUTTON.手柄按键
KEY_MAPPINGS = {
    'w': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    's': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    'a': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    'd': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
    'j': vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    'k': vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    'u': vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    'i': vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    keyboard.Key.space: vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    keyboard.Key.shift: vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
}

# 脚本更新频率（Hz）
UPDATE_RATE = 60

# --------------------------------------------------------------------------------
# 全局变量 - 请勿随意修改
# --------------------------------------------------------------------------------

try:
    gamepad = vg.VX360Gamepad()
    print("虚拟手柄已成功创建...")
except Exception as e:
    print(f"创建虚拟手柄失败，请确保您已正确安装 vgamepad 驱动。错误: {e}")
    exit()

# 用于存储鼠标位置和线程同步
mouse_x, mouse_y = 0, 0
last_x, last_y = 0, 0
mouse_lock = threading.Lock()

# 【新增】用于累加鼠标输入的变量
current_joystick_x = 0
# 将左右扳机统一为一个轴，正值为右扳机，负值为左扳机
current_trigger_axis = 0

# --------------------------------------------------------------------------------
# 核心功能函数
# --------------------------------------------------------------------------------

def clamp(value, min_val, max_val):
    """一个辅助函数，确保一个值在指定的最小和最大范围内"""
    return max(min_val, min(value, max_val))

def on_move(x, y):
    """当鼠标移动时，由pynput监听器调用的回调函数"""
    global mouse_x, mouse_y
    with mouse_lock:
        mouse_x, mouse_y = x, y

def on_press(key):
    """当键盘按键按下时，由pynput监听器调用的回调函数"""
    global current_joystick_x, current_trigger_axis

    # 【修改】检查是否按下了复位键
    if key == RESET_KEY:
        with mouse_lock:
            current_joystick_x = 0
            current_trigger_axis = 0
        print("--- 输入已复位 ---")
        return # 复位后，不执行下面的按键映射逻辑

    try:
        key_to_check = key.char.lower()
    except AttributeError:
        key_to_check = key

    if key_to_check in KEY_MAPPINGS:
        gamepad.press_button(button=KEY_MAPPINGS[key_to_check])
        gamepad.update()

def on_release(key):
    """当键盘按键释放时，由pynput监听器调用的回调函数"""
    try:
        key_to_check = key.char.lower()
    except AttributeError:
        key_to_check = key

    if key_to_check in KEY_MAPPINGS:
        gamepad.release_button(button=KEY_MAPPINGS[key_to_check])
        gamepad.update()

def start_listeners():
    """在一个单独的线程中启动鼠标和键盘监听器"""
    mouse_listener = mouse.Listener(on_move=on_move)
    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    
    mouse_listener.daemon = True
    keyboard_listener.daemon = True
    
    mouse_listener.start()
    keyboard_listener.start()

def main_loop():
    """主循环，定期更新手柄状态"""
    global last_x, last_y, current_joystick_x, current_trigger_axis

    with mouse_lock:
        last_x, last_y = mouse_x, mouse_y

    while True:
        with mouse_lock:
            delta_x = mouse_x - last_x
            delta_y = mouse_y - last_y
            
            last_x, last_y = mouse_x, mouse_y

            # --- 【修改】累加鼠标移动量 ---
            
            # 累加X轴移动
            current_joystick_x += int(delta_x * MOUSE_SENSITIVITY_X)
            current_joystick_x = clamp(current_joystick_x, -32768, 32767)

            # 累加Y轴移动到扳机轴
            # 向上移动(delta_y < 0)会增加轴的值，向下移动(delta_y > 0)会减少轴的值
            current_trigger_axis -= int(delta_y * MOUSE_SENSITIVITY_TRIGGER)
            current_trigger_axis = clamp(current_trigger_axis, -255, 255)

        # --- 根据累加值更新手柄状态 ---
        
        # 更新左摇杆X轴
        gamepad.left_joystick(x_value=current_joystick_x, y_value=0)
        
        # 根据扳机轴的值来决定哪个扳机被按下
        if current_trigger_axis > 0:
            # 轴为正，按下右扳机，左扳机为0
            gamepad.right_trigger(value=current_trigger_axis)
            gamepad.left_trigger(value=0)
        elif current_trigger_axis < 0:
            # 轴为负，按下左扳机（取绝对值），右扳机为0
            gamepad.left_trigger(value=abs(current_trigger_axis))
            gamepad.right_trigger(value=0)
        else:
            # 轴为0，两个扳机都为0
            gamepad.right_trigger(value=0)
            gamepad.left_trigger(value=0)

        # 发送所有更新到虚拟手柄
        gamepad.update()

        time.sleep(1 / UPDATE_RATE)

# --------------------------------------------------------------------------------
# 脚本入口
# --------------------------------------------------------------------------------
if __name__ == "__main__":
    print("开始运行鼠标转手柄脚本 (输入保持模式)...")
    print("移动鼠标会累加手柄输入，输入状态在复位前将一直保持。")
    print(f"【重要】请按 <{str(RESET_KEY).split('.')[-1]}> 键将摇杆和扳机复位到中心。")
    print("按 Ctrl+C 停止脚本。")

    start_listeners()
    
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n脚本已停止。")
    finally:
        gamepad.reset()
        gamepad.update()
        print("手柄已重置。")