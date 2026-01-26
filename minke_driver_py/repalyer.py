import time
import json
import pyautogui
from human_hid import HumanHID

class ActionReplayer:
    def __init__(self, device_port, screen_res=(1920, 1080)):
        self.port = device_port
        self.sw, self.sh = screen_res

    def play(self, filename, speed=1.0):
        print(f"▶️ 开始回放: {filename} (倍速: {speed})")
        
        # 加载所有数据到内存
        actions = []
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                actions.append(json.loads(line))

        if not actions:
            print("❌ 文件为空")
            return

        with HumanHID(self.port, self.sw, self.sh) as human:
            # 初始时间基准
            start_real_time = time.perf_counter() * 1000
            start_record_time = actions[0]['t']

            for action in actions:
                # 1. 时间同步
                target_offset = (action['t'] - start_record_time) / speed
                current_offset = time.perf_counter() * 1000 - start_real_time
                
                wait_ms = target_offset - current_offset
                if wait_ms > 0:
                    time.sleep(wait_ms / 1000.0)

                # 2. 执行动作
                etype = action['e']
                
                if etype == 'move':
                    # 像素转百分比 (包含安全边距处理在底层驱动中)
                    # 注意：回放时直接用底层 move_to，不需要 jitter，因为录制的轨迹本身就是抖动的
                    human.device.mouse_move_to(action['x'] / self.sw, action['y'] / self.sh)
                
                elif etype == 'click':
                    btn = action['b']
                    if action['s'] == 1:
                        human.device.mouse_down(btn)
                    else:
                        human.device.mouse_up(btn)
                
                elif etype == 'scroll':
                    # 录制的是 dy，通常为 1 或 -1
                    human.device.mouse_scroll(action['dy'])

                elif etype == 'key':
                    key = action['k']
                    if action['s'] == 1:
                        # 对于组合键，这里会连续调用 key_down，例如先 ctrl_down 再 c_down
                        # 底层驱动会自动处理 modifier 逻辑
                        human.device.key_down(key)
                    else:
                        human.device.key_up(key)

        print("🏁 回放结束")

if __name__ == "__main__":
    # 请根据实际屏幕分辨率修改
    player = ActionReplayer("COM3", screen_res=(1920, 1080))
    
    # 录制一个包含 Ctrl+C 的操作然后回放试试
    player.play("combo_test.jsonl", speed=1.0)