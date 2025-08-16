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

class ConfigEditorV2(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("手柄映射脚本配置工具 v2")
        self.geometry("650x680") # 增加了窗口高度以容纳新选项
        self.resizable(False, False)

        self.target_file_path = tk.StringVar()
        self.config_data = {}
        
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
        settings_frame.columnconfigure(2, weight=1)

        self.widgets = {}
        self._create_setting_row(settings_frame, "MOUSE_SENSITIVITY_X", "鼠标X轴灵敏度:", 0, 1, 1000)
        self._create_setting_row(settings_frame, "MOUSE_SENSITIVITY_TRIGGER", "鼠标扳机灵敏度:", 1, 1, 100)
        self._create_setting_row(settings_frame, "UPDATE_RATE", "更新频率 (Hz):", 2, 30, 240)
        self._create_hotkey_row(settings_frame, "RESET_KEY", "复位按键:", 3, can_disable=False)
        # 【新增】为新的扳机快捷键创建设置行
        self._create_hotkey_row(settings_frame, "FULL_LT_KEY", "快捷键: 左扳机全开", 4, can_disable=True)
        self._create_hotkey_row(settings_frame, "FULL_RT_KEY", "快捷键: 右扳机全开", 5, can_disable=True)

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
        ttk.Label(parent, text=label_text).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        var = tk.IntVar()
        slider = ttk.Scale(parent, from_=from_, to=to, orient=tk.HORIZONTAL, variable=var, command=lambda v, k=key: self._update_entry_from_slider(k))
        slider.grid(row=row, column=2, sticky="ew", padx=5)
        entry = ttk.Entry(parent, textvariable=var, width=5)
        entry.grid(row=row, column=3, sticky="w", padx=5)
        self.widgets[key] = {'var': var, 'slider': slider, 'entry': entry}

    def _create_hotkey_row(self, parent, key, label_text, row, can_disable=False):
        """【修改】创建一个用于设置快捷键的行，可包含启用/禁用复选框"""
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", padx=5, pady=5)
        
        enabled_var = tk.BooleanVar(value=True)
        if can_disable:
            checkbutton = ttk.Checkbutton(parent, text="启用", variable=enabled_var, command=lambda k=key: self._toggle_hotkey_state(k))
            checkbutton.grid(row=row, column=1, sticky="w")
        
        var = tk.StringVar(value="尚未设置")
        entry = ttk.Entry(parent, textvariable=var, state="readonly")
        entry.grid(row=row, column=2, sticky="ew", padx=5)
        
        button = ttk.Button(parent, text="点击设置", command=lambda k=key: self._capture_key(k))
        button.grid(row=row, column=3, sticky="w", padx=5)
        
        self.widgets[key] = {'var': var, 'entry': entry, 'button': button}
        if can_disable:
            self.widgets[key]['enabled_var'] = enabled_var
            self.widgets[key]['checkbutton'] = checkbutton

    def _toggle_hotkey_state(self, key):
        """【新增】切换快捷键输入框和按钮的可用状态"""
        widget_info = self.widgets[key]
        is_enabled = widget_info['enabled_var'].get()
        new_state = tk.NORMAL if is_enabled else tk.DISABLED
        
        widget_info['entry'].config(state=new_state)
        widget_info['button'].config(state=new_state)
        
        if not is_enabled:
            widget_info['var'].set("已禁用")
        else:
            # 重新启用时，恢复显示原来的值
            display_val = self._format_key_for_display(self.config_data.get(key, ''))
            widget_info['var'].set(display_val)

    def _update_entry_from_slider(self, key):
        self.widgets[key]['var'].set(int(self.widgets[key]['slider'].get()))

    def _browse_file(self):
        filepath = filedialog.askopenfilename(title="选择要配置的Python脚本", filetypes=[("Python Files", "*.py")])
        if filepath:
            self.target_file_path.set(filepath)
            self._load_config()

    def _load_config(self):
        filepath = self.target_file_path.get()
        if not filepath: return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析函数，用于安全地提取值
            def parse_value(pattern, default_val):
                match = re.search(pattern, content)
                return match.group(1) if match else default_val

            self.config_data['MOUSE_SENSITIVITY_X'] = int(parse_value(r"MOUSE_SENSITIVITY_X\s*=\s*(\d+)", "250"))
            self.config_data['MOUSE_SENSITIVITY_TRIGGER'] = int(parse_value(r"MOUSE_SENSITIVITY_TRIGGER\s*=\s*(\d+)", "10"))
            self.config_data['UPDATE_RATE'] = int(parse_value(r"UPDATE_RATE\s*=\s*(\d+)", "60"))
            self.config_data['RESET_KEY'] = parse_value(r"RESET_KEY\s*=\s*(.+)", "keyboard.Key.f1")
            # 【新增】解析新的扳机键配置
            self.config_data['FULL_LT_KEY'] = parse_value(r"FULL_LT_KEY\s*=\s*(.+)", "None")
            self.config_data['FULL_RT_KEY'] = parse_value(r"FULL_RT_KEY\s*=\s*(.+)", "None")
            
            mappings_match = re.search(r"KEY_MAPPINGS\s*=\s*\{([\s\S]*?)\}", content, re.MULTILINE)
            key_mappings = {}
            if mappings_match:
                for match in re.finditer(r"(['\"]?[\w\.]+['\"]?)\s*:\s*(vg\.XUSB_BUTTON\.[\w_]+)", mappings_match.group(1)):
                    key_mappings[match.group(1)] = match.group(2)
            self.config_data['KEY_MAPPINGS'] = key_mappings
            
            self._update_gui_from_config()
            messagebox.showinfo("成功", "配置已成功加载！")
        except Exception as e:
            messagebox.showerror("加载失败", f"无法解析配置文件。\n错误: {e}")

    def _format_key_for_display(self, key_str):
        """【新增】将脚本中的按键字符串格式化为可读的显示字符串"""
        if not key_str or key_str == 'None':
            return "已禁用"
        return key_str.replace("keyboard.Key.", "").replace("'", "").capitalize()

    def _update_gui_from_config(self):
        for key, widget_info in self.widgets.items():
            if key in self.config_data:
                value_str = str(self.config_data[key])
                if 'enabled_var' in widget_info: # 这是一个快捷键行
                    is_enabled = (value_str != 'None')
                    widget_info['enabled_var'].set(is_enabled)
                    if is_enabled:
                        widget_info['var'].set(self._format_key_for_display(value_str))
                    else:
                        widget_info['var'].set("已禁用")
                    self._toggle_hotkey_state(key) # 更新控件状态
                else: # 这是一个数值行
                    widget_info['var'].set(int(value_str))

        self.keymap_tree.delete(*self.keymap_tree.get_children())
        for key, val in self.config_data.get('KEY_MAPPINGS', {}).items():
            self.keymap_tree.insert("", tk.END, values=(self._format_key_for_display(key), val.replace("vg.XUSB_BUTTON.", "")), tags=(key, val))

    def _save_config(self):
        filepath = self.target_file_path.get()
        if not filepath: return
        if not messagebox.askyesno("确认保存", "确定要将当前配置写入文件吗？\n将自动创建一个.bak备份文件。"):
            return
        try:
            backup_path = filepath + ".bak"
            shutil.copy(filepath, backup_path)
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 更新函数，用于替换行内容
            def get_new_line(line, key, value):
                return f"{key} = {value}\n" if line.strip().startswith(key) else line

            new_lines = []
            for line in lines:
                processed_line = line
                # 更新基本配置
                for key, widget_info in self.widgets.items():
                    if line.strip().startswith(key):
                        if 'enabled_var' in widget_info: # 快捷键
                            value = self.config_data[key] if widget_info['enabled_var'].get() else 'None'
                            processed_line = get_new_line(line, key, value)
                        elif 'var' in widget_info: # 数值
                            processed_line = get_new_line(line, key, widget_info['var'].get())
                        break # 找到匹配项后跳出内层循环
                new_lines.append(processed_line)
            
            # 重建KEY_MAPPINGS字典
            final_lines = []
            in_mapping_dict = False
            for line in new_lines:
                if line.strip().startswith("KEY_MAPPINGS"):
                    final_lines.append(line)
                    in_mapping_dict = True
                    for item in self.keymap_tree.get_children():
                        key_full, val_full = self.keymap_tree.item(item, 'tags')
                        final_lines.append(f"    {key_full}: {val_full},\n")
                elif in_mapping_dict and line.strip() == "}":
                    final_lines.append(line)
                    in_mapping_dict = False
                elif not in_mapping_dict:
                    final_lines.append(line)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(final_lines)
            
            messagebox.showinfo("成功", f"配置已成功保存！\n原始文件已备份为: {os.path.basename(backup_path)}")
        except Exception as e:
            messagebox.showerror("保存失败", f"写入文件时发生错误。\n错误: {e}")

    # --- 以下是按键捕捉和映射管理的相关函数，与上一版相同，无需修改 ---
    def _capture_key(self, config_key):
        self.capture_window = tk.Toplevel(self); self.capture_window.title("按键捕捉"); self.capture_window.geometry("200x100"); self.capture_window.transient(self); self.capture_window.grab_set()
        ttk.Label(self.capture_window, text="请按下一个按键...").pack(pady=20, expand=True)
        self.capture_window.bind("<KeyPress>", lambda e, k=config_key: self._on_key_captured(e, k))
        self.wait_window(self.capture_window)

    def _on_key_captured(self, event, config_key):
        key_name, full_key_str = self._format_key_from_event(event)
        if config_key in self.widgets: self.widgets[config_key]['var'].set(key_name)
        self.config_data[config_key] = full_key_str
        if hasattr(self, '_capture_result'): self._capture_result = (key_name, full_key_str)
        self.capture_window.destroy()

    def _format_key_from_event(self, event):
        key_name = event.keysym
        if len(key_name) == 1 and key_name.isalpha(): return key_name.lower(), f"'{key_name.lower()}'"
        else:
            key_name_lower = key_name.lower().replace('_l', '').replace('_r', '')
            return key_name.capitalize(), f"keyboard.Key.{key_name_lower}"

    def _add_mapping_dialog(self):
        dialog = tk.Toplevel(self); dialog.title("添加新映射"); dialog.geometry("350x150"); dialog.transient(self); dialog.grab_set()
        frame = ttk.Frame(dialog, padding="10"); frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="键盘按键:").grid(row=0, column=0, padx=5, pady=10, sticky="w")
        key_var = tk.StringVar(value="点击右侧按钮设置"); ttk.Entry(frame, textvariable=key_var, state="readonly").grid(row=0, column=1, sticky="ew")
        self._capture_result = None
        ttk.Button(frame, text="设置", command=lambda: self._capture_key("_temp_mapping_key")).grid(row=0, column=2, padx=5)
        ttk.Label(frame, text="手柄按键:").grid(row=1, column=0, padx=5, pady=10, sticky="w")
        gamepad_var = tk.StringVar(); gamepad_combo = ttk.Combobox(frame, textvariable=gamepad_var, values=self.gamepad_buttons, state="readonly"); gamepad_combo.grid(row=1, column=1, columnspan=2, sticky="ew")
        if self.gamepad_buttons: gamepad_combo.current(0)
        btn_frame = ttk.Frame(frame); btn_frame.grid(row=2, column=0, columnspan=3, pady=10)
        def on_ok():
            if not self._capture_result: messagebox.showwarning("提示", "请先设置一个键盘按键！", parent=dialog); return
            key_display, key_full = self._capture_result; val_display = gamepad_var.get(); val_full = f"vg.XUSB_BUTTON.{val_display}"
            self.keymap_tree.insert("", tk.END, values=(key_display, val_display), tags=(key_full, val_full)); dialog.destroy()
        ttk.Button(btn_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT)

    def _remove_selected_mapping(self):
        selected_items = self.keymap_tree.selection()
        if not selected_items: messagebox.showwarning("提示", "请先在列表中选择要删除的映射！"); return
        if messagebox.askyesno("确认删除", "确定要删除选中的映射吗？"):
            for item in selected_items: self.keymap_tree.delete(item)

if __name__ == "__main__":
    app = ConfigEditorV2()
    app.mainloop()
