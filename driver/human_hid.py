import time
import random
import math
from hid_driver import InputDevice

class HumanHID:
    def __init__(self, port, screen_width=1920, screen_height=1080):
        """
        :param port: 串口号
        :param screen_width: 屏幕宽度 (像素), 用于计算精确的抖动距离
        :param screen_height: 屏幕高度 (像素)
        """
        self.device = InputDevice(port)
        self.screen_w = screen_width
        self.screen_h = screen_height
        
        # 记录当前逻辑坐标 (0.0 ~ 1.0)
        self.current_x = 0.5
        self.current_y = 0.5

    def __enter__(self):
        self.device.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.device.close()

    # ================= 核心算法: 像素级贝塞尔曲线 =================
    def _get_bezier_points(self, start, end, control1, control2, steps):
        path = []
        for t in range(steps + 1):
            t /= steps
            x = (1-t)**3 * start[0] + 3*(1-t)**2 * t * control1[0] + \
                3*(1-t) * t**2 * control2[0] + t**3 * end[0]
            y = (1-t)**3 * start[1] + 3*(1-t)**2 * t * control1[1] + \
                3*(1-t) * t**2 * control2[1] + t**3 * end[1]
            path.append((x, y))
        return path

    def _generate_human_path(self, start_x, start_y, end_x, end_y, steps):
        # 1. 将百分比坐标转为虚拟像素坐标 (方便计算距离)
        sx_px, sy_px = start_x * self.screen_w, start_y * self.screen_h
        ex_px, ey_px = end_x * self.screen_w, end_y * self.screen_h
        
        dist_px = math.hypot(ex_px - sx_px, ey_px - sy_px)
        
        # 2. 控制点偏移逻辑 (单位：像素)
        # 距离越远，弧度可以越大，但也限制最大值
        # 偏移量在 [20px, 150px] 之间波动，或者距离的 20%
        offset_limit_px = min(dist_px * 0.2, 150)
        offset_limit_px = max(20, offset_limit_px) # 最小偏移 20px

        # 生成随机偏移 (像素)
        def get_random_offset():
            return random.uniform(-offset_limit_px, offset_limit_px)

        # 3. 计算控制点 (在像素空间)
        # 控制点1：靠近起点
        c1x_px = sx_px + (ex_px - sx_px) * 0.25 + get_random_offset()
        c1y_px = sy_px + (ey_px - sy_px) * 0.25 + get_random_offset()
        
        # 控制点2：靠近终点
        c2x_px = sx_px + (ex_px - sx_px) * 0.75 + get_random_offset()
        c2y_px = sy_px + (ey_px - sy_px) * 0.75 + get_random_offset()

        # 4. 转回百分比坐标
        c1 = (c1x_px / self.screen_w, c1y_px / self.screen_h)
        c2 = (c2x_px / self.screen_w, c2y_px / self.screen_h)

        return self._get_bezier_points((start_x, start_y), (end_x, end_y), c1, c2, steps)

    # ================= 对外接口: 拟人移动 =================
    def move_to(self, x, y, duration=0.5, jitter_pixels=3):
        """
        拟人化绝对移动
        :param x, y: 目标百分比 (0.0 - 1.0)
        :param duration: 移动耗时 (秒)
        :param jitter_pixels: 终点随机抖动范围 (单位: 像素)。设为 0 关闭抖动。
        """
        target_x, target_y = x, y

        # 1. 像素级抖动处理 (Jitter)
        if jitter_pixels > 0:
            # 将像素转换为百分比偏移量
            offset_x_percent = jitter_pixels / self.screen_w
            offset_y_percent = jitter_pixels / self.screen_h
            
            target_x += random.uniform(-offset_x_percent, offset_x_percent)
            target_y += random.uniform(-offset_y_percent, offset_y_percent)

        # 2. 计算步数 (基于移动距离和时间，保证平滑度)
        # 最小每秒 60 帧，或者每移动 10 像素至少 1 帧
        steps = int(max(duration * 60, 5))
        
        path = self._generate_human_path(self.current_x, self.current_y, 
                                         target_x, target_y, steps)
        
        dt = duration / steps
        for px, py in path:
            self.device.mouse_move_to(px, py)
            time.sleep(dt)
        
        self.current_x = target_x
        self.current_y = target_y
        
        # 3. 拟人停顿
        time.sleep(random.uniform(0.05, 0.12))

    # ================= 对外接口: 拟人点击 =================
    def click(self, button='left'):
        self.device.mouse_down(button)
        time.sleep(random.uniform(0.06, 0.14)) # 随机按键时长
        self.device.mouse_up(button)

    def click_at(self, x, y, button='left', duration=0.6, jitter_pixels=3):
        """
        移动并点击
        :param jitter_pixels: 允许的点击误差 (像素)
        """
        self.move_to(x, y, duration=duration, jitter_pixels=jitter_pixels)
        self.click(button)

    # ================= 对外接口: 拟人输入 =================
    def type(self, text, wpm=80):
        # 计算打字间隔
        base_interval = 60 / (wpm * 5)
        
        for char in text:
            # 高斯分布延迟
            delay = abs(random.gauss(base_interval, base_interval * 0.4))
            delay = max(0.03, delay)
            
            if random.random() < 0.05: # 5% 概率思考卡顿
                delay += random.uniform(0.2, 0.5)

            # 调用底层无延迟输入，由这里控制节奏
            self.device.type_string(char, interval=0.0)
            time.sleep(delay)

    # ================= 对外接口: 拖拽 =================
    def drag_drop(self, start_x, start_y, end_x, end_y, duration=1.0):
        # 移动到起点 (允许 3 像素误差)
        self.move_to(start_x, start_y, duration=duration*0.4, jitter_pixels=3)
        
        self.device.mouse_down('left')
        time.sleep(random.uniform(0.1, 0.2))
        
        # 拖拽到终点 (允许 3 像素误差)
        self.move_to(end_x, end_y, duration=duration, jitter_pixels=3)
        
        time.sleep(random.uniform(0.1, 0.2))
        self.device.mouse_up('left')