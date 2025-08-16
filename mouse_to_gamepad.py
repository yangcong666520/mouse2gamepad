# -*- coding: utf-8 -*-

import time
import threading
from pynput import mouse, keyboard
import vgamepad as vg

# --------------------------------------------------------------------------------
# 配置(Configs)
# --------------------------------------------------------------------------------

# 鼠标移动转换为手柄摇杆的倍率（灵敏度）
# Joystick sensitivity

MOUSE_SENSITIVITY_X = 100

# 鼠标上下移动转换为手柄扳机键的倍率（灵敏度）
# Trigger sensitivity
MOUSE_SENSITIVITY_TRIGGER = 1

# 将摇杆和扳机复位的按键
# Reset
RESET_KEY = keyboard.Key.f8

# 定义按住时可将扳机完全按下的按键
# 设置为 None 可禁用该功能
FULL_LT_KEY = 'q'  # 按住该键可将左扳机(LT)踩到底
FULL_RT_KEY = 'e'  # 按住该键可将右扳机(RT)踩到底

# 键盘按键映射
# (请遵照下面的格式添加或修改按键)！
# (请遵照下面的格式添加或修改按键)！
# (请遵照下面的格式添加或修改按键)！
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
# --------------------------------------------------------------------------------
# --------------------------------------------------------------------------------
# --------------------------------------------------------------------------------
# 全局变量 - 请勿随意修改(DONT MODIFY)
# --------------------------------------------------------------------------------
# --------------------------------------------------------------------------------
# --------------------------------------------------------------------------------
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

# 用于累加鼠标输入的变量
current_joystick_x = 0
current_trigger_axis = 0

# 用于追踪扳机快捷键是否被按下的状态
lt_key_pressed = False
rt_key_pressed = False

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
    global current_joystick_x, current_trigger_axis, lt_key_pressed, rt_key_pressed

    try:
        key_to_check = key.char.lower()
    except AttributeError:
        key_to_check = key

    # 检查是否按下了复位键
    if key_to_check == RESET_KEY:
        with mouse_lock:
            current_joystick_x = 0
            current_trigger_axis = 0
        print("--- 输入已复位 ---")
        return

    # 检查是否按下了扳机快捷键
    if FULL_LT_KEY and key_to_check == FULL_LT_KEY:
        lt_key_pressed = True
    elif FULL_RT_KEY and key_to_check == FULL_RT_KEY:
        rt_key_pressed = True
    
    # 处理常规按键映射
    elif key_to_check in KEY_MAPPINGS:
        gamepad.press_button(button=KEY_MAPPINGS[key_to_check])
        gamepad.update()

def on_release(key):
    """当键盘按键释放时，由pynput监听器调用的回调函数"""
    global lt_key_pressed, rt_key_pressed
    
    try:
        key_to_check = key.char.lower()
    except AttributeError:
        key_to_check = key

    # 检查是否释放了扳机快捷键
    if FULL_LT_KEY and key_to_check == FULL_LT_KEY:
        lt_key_pressed = False
    elif FULL_RT_KEY and key_to_check == FULL_RT_KEY:
        rt_key_pressed = False
        
    # 处理常规按键映射
    elif key_to_check in KEY_MAPPINGS:
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

            # 累加鼠标移动量
            current_joystick_x += int(delta_x * MOUSE_SENSITIVITY_X)
            current_joystick_x = clamp(current_joystick_x, -32768, 32767)

            current_trigger_axis -= int(delta_y * MOUSE_SENSITIVITY_TRIGGER)
            current_trigger_axis = clamp(current_trigger_axis, -255, 255)

        # --- 根据累加值和按键状态更新手柄 ---
        
        # 更新左摇杆X轴
        gamepad.left_joystick(x_value=current_joystick_x, y_value=0)
        
        # 首先根据鼠标的累积值计算扳机
        lt_from_mouse = 0
        rt_from_mouse = 0
        if current_trigger_axis > 0:
            rt_from_mouse = current_trigger_axis
        elif current_trigger_axis < 0:
            lt_from_mouse = abs(current_trigger_axis)
        
        # 检查快捷键是否覆盖扳机值
        # 如果lt_key_pressed为True，则final_lt_value为255，否则为鼠标计算的值
        final_lt_value = 255 if lt_key_pressed else lt_from_mouse
        final_rt_value = 255 if rt_key_pressed else rt_from_mouse

        gamepad.left_trigger(value=final_lt_value)
        gamepad.right_trigger(value=final_rt_value)

        # 发送所有更新到虚拟手柄
        gamepad.update()

        time.sleep(1 / UPDATE_RATE)

# --------------------------------------------------------------------------------
# 脚本入口
# --------------------------------------------------------------------------------
if __name__ == "__main__":
    print("开始运行鼠标转手柄脚本 (输入保持/快捷扳机模式)...")
    print(f"按 <{str(RESET_KEY).split('.')[-1]}> 键将摇杆和扳机复位。")
    if FULL_LT_KEY:
        print(f"按住 <{FULL_LT_KEY}> 键可将左扳机(LT)完全按下。")
    if FULL_RT_KEY:
        print(f"按住 <{FULL_RT_KEY}> 键可将右扳机(RT)完全按下。")
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
