import serial
import time
import struct

# ================= 1. 基础键值表 =================
HID_KEY_MAP = {
    'a': 0x04, 'b': 0x05, 'c': 0x06, 'd': 0x07, 'e': 0x08, 'f': 0x09,
    'g': 0x0A, 'h': 0x0B, 'i': 0x0C, 'j': 0x0D, 'k': 0x0E, 'l': 0x0F,
    'm': 0x10, 'n': 0x11, 'o': 0x12, 'p': 0x13, 'q': 0x14, 'r': 0x15,
    's': 0x16, 't': 0x17, 'u': 0x18, 'v': 0x19, 'w': 0x1A, 'x': 0x1B,
    'y': 0x1C, 'z': 0x1D,
    '1': 0x1E, '2': 0x1F, '3': 0x20, '4': 0x21, '5': 0x22, 
    '6': 0x23, '7': 0x24, '8': 0x25, '9': 0x26, '0': 0x27,
    'enter': 0x28, 'esc': 0x29, 'backspace': 0x2A, 'tab': 0x2B,
    'space': 0x2C, ' ': 0x2C,
    '-': 0x2D, '=': 0x2E, '[': 0x2F, ']': 0x30, '\\': 0x31, '#': 0x32, ';': 0x33,
    '\'': 0x34, '`': 0x35, ',': 0x36, '.': 0x37, '/': 0x38,
    'caps_lock': 0x39, 
    'f1': 0x3A, 'f2': 0x3B, 'f3': 0x3C, 'f4': 0x3D, 'f5': 0x3E, 'f6': 0x3F, 
    'f7': 0x40, 'f8': 0x41, 'f9': 0x42, 'f10': 0x43, 'f11': 0x44, 'f12': 0x45,
    'print': 0x46, 'scroll_lock': 0x47, 'pause': 0x48, 'insert': 0x49,
    'home': 0x4A, 'page_up': 0x4B, 'delete': 0x4C, 'end': 0x4D, 'page_down': 0x4E,
    'right': 0x4F, 'left': 0x50, 'down': 0x51, 'up': 0x52,
    'win': 0x08, 'gui': 0x08 # 兼容写法，虽然Win是修饰键，但防止用户查表
}

# ================= 2. 符号转换表 =================
SHIFT_SYMBOLS = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';', '"': '\'', '~': '`', '<': ',', '>': '.', '?': '/',
    'A': 'a', 'B': 'b', 'C': 'c', 'D': 'd', 'E': 'e', 'F': 'f', 'G': 'g', 'H': 'h', 'I': 'i', 'J': 'j', 'K': 'k', 'L': 'l', 'M': 'm',
    'N': 'n', 'O': 'o', 'P': 'p', 'Q': 'q', 'R': 'r', 'S': 's', 'T': 't', 'U': 'u', 'V': 'v', 'W': 'w', 'X': 'x', 'Y': 'y', 'Z': 'z'
}

# ================= 3. 修饰键掩码 =================
MODIFIERS = {
    'ctrl': 0x01, 'l_ctrl': 0x01,
    'shift': 0x02, 'l_shift': 0x02,
    'alt': 0x04, 'l_alt': 0x04,
    'win': 0x08, 'l_win': 0x08, 'gui': 0x08,
    'r_ctrl': 0x10, 'r_shift': 0x20, 'r_alt': 0x40, 'r_win': 0x80
}

MOUSE_BTNS = {'left': 0x01, 'right': 0x02, 'middle': 0x04}

class InputDevice:
    def __init__(self, port, baud_rate=115200):
        self.port = port
        self.baud = baud_rate
        self.ser = None
        self.abs_max_x = 32767
        self.abs_max_y = 32767
        # ================= 安全边距配置 =================
        # 防止触达 0 或 32767 的系统热区
        # 10 单位约等于 0.5 像素 (在1080p下)，非常安全且不影响精度
        self.safe_margin = 10 
        
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(2) 
            print(f"Device connected on {self.port}")
        except Exception as e:
            print(f"Connection failed: {e}")
            raise

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Device disconnected")

    def _send_packet(self, type, b2, b3, b4, b5, b6, b7, delay_ms=0):
        if not self.ser: return
        payload = struct.pack('<BBBBBBBBH', 
                              0xAA, type, b2, b3, b4, b5, b6, b7, delay_ms)
        self.ser.write(payload + bytes([0x55]))
        time.sleep(0.005) 

    # ================= 鼠标 API =================

    def mouse_move(self, dx, dy, wheel=0):
        """相对移动"""
        if wheel != 0:
            self._send_packet(0x02, 0, wheel & 0xFF, 0, 0, 0, 0)
        
        max_step = 127
        while dx != 0:
            step = min(dx, max_step) if dx > 0 else max(dx, -max_step)
            x_bytes = struct.pack('<h', step)
            self._send_packet(0x02, 0, 0, x_bytes[0], x_bytes[1], 0, 0)
            dx -= step
        while dy != 0:
            step = min(dy, max_step) if dy > 0 else max(dy, -max_step)
            y_bytes = struct.pack('<h', step)
            self._send_packet(0x02, 0, 0, 0, 0, y_bytes[0], y_bytes[1])
            dy -= step

    def mouse_move_to(self, x_percent, y_percent):
        """
        绝对移动 (含边界保护)
        :param x_percent: 0.0 ~ 1.0
        :param y_percent: 0.0 ~ 1.0
        """
        # 1. 计算原始坐标
        target_x = int(x_percent * self.abs_max_x)
        target_y = int(y_percent * self.abs_max_y)
        
        # 2. 边界钳制 (Clamping)
        # 确保坐标在 [SAFE, MAX-SAFE] 之间，永远不会发送 0 或 32767
        min_val = self.safe_margin
        max_x = self.abs_max_x - self.safe_margin
        max_y = self.abs_max_y - self.safe_margin

        target_x = max(min_val, min(target_x, max_x))
        target_y = max(min_val, min(target_y, max_y))
        
        # 3. 发送
        bx = struct.pack('<h', target_x)
        by = struct.pack('<h', target_y)
        self._send_packet(0x03, 0, 0, bx[0], bx[1], by[0], by[1])

    def mouse_click(self, button='left'):
        btn_mask = MOUSE_BTNS.get(button, 0)
        self._send_packet(0x02, btn_mask, 0, 0, 0, 0, 0)
        time.sleep(0.05)
        self._send_packet(0x02, 0, 0, 0, 0, 0, 0)

    def mouse_down(self, button='left'):
        btn_mask = MOUSE_BTNS.get(button, 0)
        self._send_packet(0x02, btn_mask, 0, 0, 0, 0, 0)

    def mouse_up(self, button='left'):
        self._send_packet(0x02, 0, 0, 0, 0, 0, 0)

    def mouse_scroll(self, steps):
        self.mouse_move(0, 0, wheel=steps)

    # ================= 键盘 API =================

    def key_press(self, key):
        self.key_down(key)
        time.sleep(0.05)
        self.key_up(key)

    def key_down(self, key, modifiers=[]):
        key = str(key).lower()
        code = 0
        mod_mask = 0
        for m in modifiers:
            mod_mask |= MODIFIERS.get(m.lower(), 0)

        if key in MODIFIERS:
            mod_mask |= MODIFIERS[key]
            code = 0 
        else:
            code = HID_KEY_MAP.get(key, 0)

        self._send_packet(0x01, code, 0x00, mod_mask, 0, 0, 0)

    def key_up(self, key):
        self._send_packet(0x01, 0, 0x80, 0, 0, 0, 0)

    def type_string(self, text, interval=0.05):
        for char in text:
            if char in SHIFT_SYMBOLS:
                raw_key = SHIFT_SYMBOLS[char]
                self.key_down(raw_key, modifiers=['shift'])
                time.sleep(0.02)
                self.key_up(raw_key)
            else:
                self.key_press(char)
            time.sleep(interval)

    def hotkey(self, *args):
        mods = []
        keys = []
        for k in args:
            k = str(k).lower()
            if k in MODIFIERS:
                mods.append(k)
            else:
                keys.append(k)
        
        if not keys and mods:
            target = mods[-1]
            others = mods[:-1]
            self.key_down(target, modifiers=others)
            time.sleep(0.1)
            self.key_up(target)
            return

        if keys:
            target_key = keys[-1]
            self.key_down(target_key, modifiers=mods)
            time.sleep(0.1)
            self.key_up(target_key)