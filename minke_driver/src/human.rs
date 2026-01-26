use crate::InputDevice;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use rand::Rng;
use rand_distr::{Normal, Distribution};

pub struct HumanDriver {
    pub device: Arc<Mutex<InputDevice>>,
    pub cur_x: f32,
    pub cur_y: f32,
}

impl HumanDriver {
    /// 初始化拟人化驱动器，建议传入当前真实的鼠标坐标
    pub fn new(device: Arc<Mutex<InputDevice>>, start_x: u16, start_y: u16) -> Self {
        Self {
            device,
            cur_x: start_x as f32,
            cur_y: start_y as f32,
        }
    }

    /// 【高级拟人移动】
    /// 包含：三次贝塞尔曲线、三次缓动加速、随机过冲和落点抖动
    pub fn move_to_humanly(&mut self, target_x: u16, target_y: u16, duration_sec: f32) {
        let mut rng = rand::thread_rng();
        let start = (self.cur_x, self.cur_y);
        
        // 1. 落点抖动 (Jitter)：人手点击不会每次都在同一个像素点
        // 模拟 1-3 像素的随机偏差，呈现正态分布感
        let end = (
            target_x as f32 + rng.gen_range(-2.0..2.0),
            target_y as f32 + rng.gen_range(-2.0..2.0)
        );

        // 2. 随机生成两个控制点
        // 控制点 1：靠近起点，决定起步弧度
        let ctrl1 = (
            start.0 + (end.0 - start.0) * 0.2 + rng.gen_range(-40.0..40.0),
            start.1 + (end.1 - start.1) * 0.2 + rng.gen_range(-40.0..40.0)
        );
        // 控制点 2：靠近终点，通过加大随机范围模拟惯性带来的“过冲”潜力
        let ctrl2 = (
            start.0 + (end.0 - start.0) * 0.8 + rng.gen_range(-20.0..60.0),
            start.1 + (end.1 - start.1) * 0.8 + rng.gen_range(-20.0..60.0)
        );

        // 3. 计算步数 (建议 60-100Hz，符合主流采样率)
        let steps = (duration_sec * 80.0) as u32; 
        let interval = Duration::from_secs_f32(duration_sec / steps as f32);

        for i in 0..=steps {
            // 4. 三次缓动加速 (Ease-in-out)：慢-快-慢，符合人体力学
            let t_linear = i as f32 / steps as f32;
            let t_eased = Self::ease_in_out_cubic(t_linear);

            let (px, py) = Self::bezier_cubic(t_eased, start, ctrl1, ctrl2, end);
            
            if let Ok(mut dev) = self.device.lock() {
                // 调用 lib.rs 里的 mouse_abs 发送绝对坐标
                dev.mouse_abs(px as u16, py as u16);
            }
            thread::sleep(interval);
        }

        // 更新当前记录位置
        self.cur_x = end.0;
        self.cur_y = end.1;
    }

    /// 【拟人化点击】
    /// 模拟真实手指按压时间 (带有小幅随机波动)
    pub fn click_humanly(&mut self, left: bool, right: bool) {
        let mut rng = rand::thread_rng();
        if let Ok(mut dev) = self.device.lock() {
            dev.mouse_down(left, right);
            // 模拟按下去的瞬间停顿：30ms-70ms 之间
            thread::sleep(Duration::from_millis(rng.gen_range(30..75)));
            dev.mouse_up();
        }
    }

    /// 【拟人化打字】
    /// 模拟 WPM 语速，并引入基于正态分布的按键间隔抖动
    pub fn type_humanly(&mut self, text: &str, base_wpm: f32) {
        // 计算基础延迟 (WPM 转为平均延迟)
        let base_delay_ms = 60.0 / (base_wpm * 5.0) * 1000.0;
        // 构造标准差为 30% 的正态分布，模拟手指长短和熟练度带来的差异
        let normal_dist = Normal::new(base_delay_ms, base_delay_ms * 0.3).unwrap();
        let mut rng = rand::thread_rng();

        for ch in text.chars() {
            let keycode = match ch.to_ascii_lowercase() {
                'a'..='z' => ch.to_ascii_lowercase() as u8 - b'a' + 0x04,
                ' ' => 0x2C,
                _ => 0,
            };

            if keycode != 0 {
                if let Ok(mut dev) = self.device.lock() {
                    dev.key_down(keycode, 0);
                    // 模拟按键按住的物理时长
                    thread::sleep(Duration::from_millis(rng.gen_range(25..60)));
                    dev.key_up();
                }
            }

            // 执行基于正态分布的随机停顿
            let delay = normal_dist.sample(&mut rng).max(10.0) as u64;
            thread::sleep(Duration::from_millis(delay));
        }
    }

    // ==========================================
    // 数学辅助函数
    // ==========================================

    /// 三次缓动函数实现
    fn ease_in_out_cubic(t: f32) -> f32 {
        if t < 0.5 {
            4.0 * t * t * t
        } else {
            1.0 - (-2.0 * t + 2.0).powi(3) / 2.0
        }
    }

    /// 三次贝塞尔曲线公式实现
    /// P = (1-t)^3*P0 + 3*t*(1-t)^2*P1 + 3*t^2*(1-t)*P2 + t^3*P3
    fn bezier_cubic(t: f32, p0: (f32, f32), p1: (f32, f32), p2: (f32, f32), p3: (f32, f32)) -> (f32, f32) {
        let u = 1.0 - t;
        let tt = t * t;
        let uu = u * u;
        let uuu = uu * u;
        let ttt = tt * t;

        let x = uuu * p0.0 + 3.0 * uu * t * p1.0 + 3.0 * u * tt * p2.0 + ttt * p3.0;
        let y = uuu * p0.1 + 3.0 * uu * t * p1.1 + 3.0 * u * tt * p2.1 + ttt * p3.1;
        (x, y)
    }
}