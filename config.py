# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import os
import shutil
from vgamepad.win.vigem_commons import XUSB_BUTTON

# --------------------------------------------------------------------------------
# 脚本主体 - 图形化配置编辑器
# --------------------------------------------------------------------------------

class ConfigEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("手柄映射脚本配置工具")
        self.geometry("650x600")
        self.resizable(False, False)

        self.target_file_path = tk.StringVar()
        self.config_data = {}
        
        # 用于存储从vgamepad库解析出的所有可用手柄按键名称
        self.gamepad_buttons = self._get_gamepad_buttons()

        self._create_widgets()

    def _get_gamepad_buttons(self):
        """获取所有可用的vgamepad按键名称"""
        buttons = [
            attr for attr in dir(XUSB_BUTTON)
            if isinstance(getattr(XUSB_BUTTON, attr), int)
        ]
        return sorted(buttons)

    def _create_widgets(self):
        """创建GUI界面上的所有组件"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="第一步: 选择脚本文件", padding="10")
        file_frame.pack(fill=tk.X, expand=True)
        
        ttk.Entry(file_frame, textvariable=self.target_file_path, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(file_frame, text="浏览...", command=self._browse_file).pack(side=tk.LEFT)

        # 2. 参数设置区域
        settings_frame = ttk.LabelFrame(main_frame, text="第二步: 修改参数", padding="10")
        settings_frame.pack(fill=tk.X, expand=True, pady=10)
        settings_frame.columnconfigure(1, weight=1)

        # 各项参数的标签和输入框
        self.widgets = {}
        self._create_setting_row(settings_frame, "MOUSE_SENSITIVITY_X", "鼠标X轴灵敏度:", 0, 1, 1000)
        self._create_setting_row(settings_frame, "MOUSE_SENSITIVITY_TRIGGER", "鼠标扳机灵敏度:", 1, 1, 100)
        self._create_setting_row(settings_frame, "UPDATE_RATE", "更新频率 (Hz):", 2, 30, 240)
        self._create_reset_key_row(settings_frame, "RESET_KEY", "复位按键:", 3)

        # 3. 按键映射区域
        map_frame = ttk.LabelFrame(main_frame, text="第三步: 管理键盘映射", padding="10")
        map_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("keyboard_key", "gamepad_button")
        self.keymap_tree = ttk.Treeview(map_frame, columns=columns, show="headings")
        self.keymap_tree.heading("keyboard_key", text="键盘按键")
        self.keymap_tree.heading("gamepad_button", text="手柄按键")
        self.keymap_tree.column("keyboard_key", width=150, anchor=tk.CENTER)
        self.keymap_tree.column("gamepad_button", width=350, anchor=tk.CENTER)
        self.keymap_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(map_frame, orient=tk.VERTICAL, command=self.keymap_tree.yview)
        self.keymap_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        map_buttons_frame = ttk.Frame(map_frame)
        map_buttons_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10,0))
        ttk.Button(map_buttons_frame, text="添加映射", command=self._add_mapping_dialog).pack(pady=5)
        ttk.Button(map_buttons_frame, text="删除选中", command=self._remove_selected_mapping).pack(pady=5)
        
        # 4. 操作按钮区域
        action_frame = ttk.Frame(main_frame, padding=(0, 10, 0, 0))
        action_frame.pack(fill=tk.X, expand=True)
        ttk.Button(action_frame, text="保存配置", command=self._save_config).pack(side=tk.RIGHT)
        ttk.Button(action_frame, text="重新加载", command=self._load_config).pack(side=tk.RIGHT, padx=10)

    def _create_setting_row(self, parent, key, label_text, row, from_, to):
        """创建一个带标签、滑块和输入框的设置行"""
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", padx=5, pady=5)
        
        var = tk.IntVar()
        slider = ttk.Scale(parent, from_=from_, to=to, orient=tk.HORIZONTAL, variable=var, command=lambda v, k=key: self._update_entry_from_slider(k))
        slider.grid(row=row, column=1, sticky="ew", padx=5)
        
        entry = ttk.Entry(parent, textvariable=var, width=5)
        entry.grid(row=row, column=2, sticky="w", padx=5)
        
        self.widgets[key] = {'var': var, 'slider': slider, 'entry': entry}

    def _create_reset_key_row(self, parent, key, label_text, row):
        """创建用于设置复位键的行"""
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", padx=5, pady=5)
        var = tk.StringVar(value="尚未设置")
        entry = ttk.Entry(parent, textvariable=var, state="readonly")
        entry.grid(row=row, column=1, sticky="ew", padx=5)
        button = ttk.Button(parent, text="点击设置", command=lambda k=key: self._capture_key(k))
        button.grid(row=row, column=2, sticky="w", padx=5)
        self.widgets[key] = {'var': var, 'entry': entry, 'button': button}

    def _update_entry_from_slider(self, key):
        """当滑块移动时，更新对应的输入框值"""
        self.widgets[key]['var'].set(int(self.widgets[key]['slider'].get()))

    def _browse_file(self):
        """打开文件对话框选择脚本文件"""
        filepath = filedialog.askopenfilename(
            title="选择要配置的Python脚本",
            filetypes=[("Python Files", "*.py")]
        )
        if filepath:
            self.target_file_path.set(filepath)
            self._load_config()

    def _load_config(self):
        """从文件中加载配置到GUI"""
        filepath = self.target_file_path.get()
        if not filepath:
            messagebox.showerror("错误", "请先选择一个脚本文件！")
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用正则表达式解析配置项
            self.config_data['MOUSE_SENSITIVITY_X'] = int(re.search(r"MOUSE_SENSITIVITY_X\s*=\s*(\d+)", content).group(1))
            self.config_data['MOUSE_SENSITIVITY_TRIGGER'] = int(re.search(r"MOUSE_SENSITIVITY_TRIGGER\s*=\s*(\d+)", content).group(1))
            self.config_data['UPDATE_RATE'] = int(re.search(r"UPDATE_RATE\s*=\s*(\d+)", content).group(1))
            self.config_data['RESET_KEY'] = re.search(r"RESET_KEY\s*=\s*(.+)", content).group(1)

            # 解析复杂的字典KEY_MAPPINGS
            mappings_match = re.search(r"KEY_MAPPINGS\s*=\s*\{([\s\S]*?)\}", content, re.MULTILINE)
            key_mappings = {}
            if mappings_match:
                mappings_str = mappings_match.group(1)
                pattern = re.compile(r"(['\"]?[\w\.]+['\"]?)\s*:\s*(vg\.XUSB_BUTTON\.[\w_]+)")
                for match in pattern.finditer(mappings_str):
                    key_mappings[match.group(1)] = match.group(2)
            self.config_data['KEY_MAPPINGS'] = key_mappings

            # 更新GUI显示
            self._update_gui_from_config()
            messagebox.showinfo("成功", "配置已成功加载！")
        except Exception as e:
            messagebox.showerror("加载失败", f"无法解析配置文件，请确保文件格式正确。\n错误: {e}")

    def _update_gui_from_config(self):
        """将加载到的配置数据显示在GUI上"""
        for key, widget_info in self.widgets.items():
            if key in self.config_data:
                # 特殊处理RESET_KEY，只显示可读部分
                if key == 'RESET_KEY':
                    display_val = self.config_data[key].replace("keyboard.Key.", "")
                    widget_info['var'].set(display_val)
                else:
                    widget_info['var'].set(self.config_data[key])
        
        # 更新按键映射列表
        self.keymap_tree.delete(*self.keymap_tree.get_children())
        if 'KEY_MAPPINGS' in self.config_data:
            for key, val in self.config_data['KEY_MAPPINGS'].items():
                key_display = key.replace("keyboard.Key.", "").replace("'", "")
                val_display = val.replace("vg.XUSB_BUTTON.", "")
                self.keymap_tree.insert("", tk.END, values=(key_display, val_display), tags=(key, val))

    def _save_config(self):
        """将GUI上的配置保存回文件"""
        filepath = self.target_file_path.get()
        if not filepath:
            messagebox.showerror("错误", "请先选择一个脚本文件！")
            return
        
        if not messagebox.askyesno("确认保存", "确定要将当前配置写入文件吗？\n将自动创建一个.bak备份文件。"):
            return

        try:
            # 创建备份
            backup_path = filepath + ".bak"
            shutil.copy(filepath, backup_path)

            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 更新基本配置
            new_lines = []
            in_mapping_dict = False
            for line in lines:
                if line.strip().startswith("MOUSE_SENSITIVITY_X"):
                    new_lines.append(f"MOUSE_SENSITIVITY_X = {self.widgets['MOUSE_SENSITIVITY_X']['var'].get()}\n")
                elif line.strip().startswith("MOUSE_SENSITIVITY_TRIGGER"):
                    new_lines.append(f"MOUSE_SENSITIVITY_TRIGGER = {self.widgets['MOUSE_SENSITIVITY_TRIGGER']['var'].get()}\n")
                elif line.strip().startswith("UPDATE_RATE"):
                    new_lines.append(f"UPDATE_RATE = {self.widgets['UPDATE_RATE']['var'].get()}\n")
                elif line.strip().startswith("RESET_KEY"):
                    # 从StringVar中获取的是显示值，需要从原始config_data里获取完整值
                    new_lines.append(f"RESET_KEY = {self.config_data['RESET_KEY']}\n")
                elif line.strip().startswith("KEY_MAPPINGS"):
                    new_lines.append(line)
                    in_mapping_dict = True
                    # 写入新的字典内容
                    for item in self.keymap_tree.get_children():
                        key_full, val_full = self.keymap_tree.item(item, 'tags')
                        new_lines.append(f"    {key_full}: {val_full},\n")
                elif in_mapping_dict and line.strip() == "}":
                    new_lines.append(line)
                    in_mapping_dict = False
                elif not in_mapping_dict:
                    new_lines.append(line)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            messagebox.showinfo("成功", f"配置已成功保存！\n原始文件已备份为: {os.path.basename(backup_path)}")

        except Exception as e:
            messagebox.showerror("保存失败", f"写入文件时发生错误。\n错误: {e}")
            
    def _capture_key(self, config_key):
        """弹出一个窗口用于捕捉用户的键盘输入"""
        self.capture_window = tk.Toplevel(self)
        self.capture_window.title("按键捕捉")
        self.capture_window.geometry("200x100")
        self.capture_window.transient(self)
        self.capture_window.grab_set()
        
        ttk.Label(self.capture_window, text="请按下一个按键...").pack(pady=20, expand=True)
        
        self.capture_window.bind("<KeyPress>", lambda e, k=config_key: self._on_key_captured(e, k))
        self.wait_window(self.capture_window)

    def _on_key_captured(self, event, config_key):
        """当捕捉到按键后调用的处理函数"""
        key_name = event.keysym
        full_key_str = ""

        # 判断是普通字符键还是特殊功能键
        if len(key_name) == 1 and key_name.isalpha():
            full_key_str = f"'{key_name.lower()}'"
            display_name = key_name.lower()
        else:
            # pynput的特殊键命名通常与tkinter的keysym一致或类似
            special_keys = {'space', 'shift_l', 'shift_r', 'alt_l', 'alt_r', 'control_l', 'control_r', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12'}
            key_name_lower = key_name.lower()
            if key_name_lower in special_keys:
                 # 统一左右shift, alt, ctrl
                if key_name_lower.endswith(('_l', '_r')):
                    key_name_lower = key_name_lower[:-2]
                full_key_str = f"keyboard.Key.{key_name_lower}"
                display_name = key_name.capitalize()
            else: # 如果是不常见的特殊键，直接用keysym
                full_key_str = f"keyboard.Key.{key_name_lower}"
                display_name = key_name

        if config_key in self.widgets:
            self.widgets[config_key]['var'].set(display_name)
        
        # 更新config_data中的原始值以备保存
        self.config_data[config_key] = full_key_str
        
        # 如果是从添加映射对话框调用的，则返回捕获的值
        if hasattr(self, '_capture_result'):
            self._capture_result = (display_name, full_key_str)

        self.capture_window.destroy()

    def _add_mapping_dialog(self):
        """弹出用于添加新按键映射的对话框"""
        dialog = tk.Toplevel(self)
        dialog.title("添加新映射")
        dialog.geometry("350x150")
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 键盘按键行
        ttk.Label(frame, text="键盘按键:").grid(row=0, column=0, padx=5, pady=10, sticky="w")
        key_var = tk.StringVar(value="点击右侧按钮设置")
        ttk.Entry(frame, textvariable=key_var, state="readonly").grid(row=0, column=1, sticky="ew")
        
        # 存储捕捉结果的变量
        self._capture_result = None
        ttk.Button(frame, text="设置", command=lambda: self._capture_key("_temp_mapping_key")).grid(row=0, column=2, padx=5)

        # 手柄按键行
        ttk.Label(frame, text="手柄按键:").grid(row=1, column=0, padx=5, pady=10, sticky="w")
        gamepad_var = tk.StringVar()
        gamepad_combo = ttk.Combobox(frame, textvariable=gamepad_var, values=self.gamepad_buttons, state="readonly")
        gamepad_combo.grid(row=1, column=1, columnspan=2, sticky="ew")
        if self.gamepad_buttons:
            gamepad_combo.current(0)
            
        # 确认/取消按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        def on_ok():
            if not self._capture_result:
                messagebox.showwarning("提示", "请先设置一个键盘按键！", parent=dialog)
                return
            
            key_display, key_full = self._capture_result
            val_display = gamepad_var.get()
            val_full = f"vg.XUSB_BUTTON.{val_display}"
            
            self.keymap_tree.insert("", tk.END, values=(key_display, val_display), tags=(key_full, val_full))
            dialog.destroy()

        ttk.Button(btn_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT)
        
    def _remove_selected_mapping(self):
        """删除在列表中选中的按键映射"""
        selected_items = self.keymap_tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先在列表中选择要删除的映射！")
            return
        
        if messagebox.askyesno("确认删除", "确定要删除选中的映射吗？"):
            for item in selected_items:
                self.keymap_tree.delete(item)

if __name__ == "__main__":
    app = ConfigEditor()
    app.mainloop()