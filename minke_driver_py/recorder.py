import time
import json
import threading
from pynput import mouse, keyboard

class ActionRecorder:
    def __init__(self, filename="actions.jsonl"):
        self.filename = filename
        self.start_time = None
        self.events = []
        self.recording = False
        
        # 键名清洗映射 (pynput -> hid_driver)
        self.key_map = {
            'Key.ctrl_l': 'ctrl', 'Key.ctrl_r': 'r_ctrl',
            'Key.alt_l': 'alt',   'Key.alt_r': 'r_alt',
            'Key.shift': 'shift', 'Key.shift_r': 'r_shift',
            'Key.enter': 'enter', 'Key.space': 'space',
            'Key.backspace': 'backspace', 'Key.tab': 'tab',
            'Key.esc': 'esc',     'Key.cmd': 'win',
            'Key.caps_lock': 'caps_lock'
        }

    def start(self):
        print(f"🔴 3秒后开始录制，按 【F12】 停止...")
        time.sleep(3)
        print("🔴 正在录制...")
        
        self.events = []
        self.start_time = time.perf_counter() * 1000 # 转为 ms
        self.recording = True

        # 启动监听线程
        with mouse.Listener(on_move=self._on_move, on_click=self._on_click, on_scroll=self._on_scroll) as ml, \
             keyboard.Listener(on_press=self._on_press, on_release=self._on_release) as kl:
            kl.join() # 等待键盘监听结束 (F12)

        self._save()

    def _get_timestamp(self):
        return int(time.perf_counter() * 1000 - self.start_time)

    def _record(self, event_type, **kwargs):
        if not self.recording: return
        data = {
            "t": self._get_timestamp(),
            "e": event_type,
            **kwargs
        }
        self.events.append(data)

    # --- 鼠标回调 ---
    def _on_move(self, x, y):
        self._record("move", x=x, y=y)

    def _on_click(self, x, y, button, pressed):
        btn = str(button).replace("Button.", "")
        self._record("click", b=btn, s=1 if pressed else 0)

    def _on_scroll(self, x, y, dx, dy):
        # 记录滚轮 (dy 通常是 1 或 -1)
        if dy != 0:
            self._record("scroll", dy=int(dy))

    # --- 键盘回调 ---
    def _clean_key(self, key):
        """将 pynput 对象转为字符串"""
        k_str = str(key).replace("'", "")
        return self.key_map.get(k_str, k_str)

    def _on_press(self, key):
        if key == keyboard.Key.f12:
            self.recording = False
            return False # 停止监听
            
        k_name = self._clean_key(key)
        # 避免长按时重复记录 "down" 事件 (系统自动重复)
        # 如果需要完全真实的物理表现，可以不去重；但为了文件体积，建议去重
        if self.events and self.events[-1]['e'] == 'key' and \
           self.events[-1]['k'] == k_name and self.events[-1]['s'] == 1:
            return

        self._record("key", k=k_name, s=1)

    def _on_release(self, key):
        if key == keyboard.Key.f12: return
        k_name = self._clean_key(key)
        self._record("key", k=k_name, s=0)

    def _save(self):
        print(f"💾 录制结束，保存到 {self.filename}...")
        with open(self.filename, 'w', encoding='utf-8') as f:
            for event in self.events:
                f.write(json.dumps(event) + "\n")
        print(f"✅ 保存完成，共 {len(self.events)} 条动作")

if __name__ == "__main__":
    rec = ActionRecorder("combo_test.jsonl")
    rec.start()