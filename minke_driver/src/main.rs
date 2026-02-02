use minke_driver::InputDevice;
use minke_driver::human::HumanDriver;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use chrono::Local;

fn log(msg: &str) {
    println!("[{}] {}", Local::now().format("%H:%M:%S"), msg);
}

fn main() {
    let port = "COM9"; 
    let (sw, sh) = (1920, 1080); 
    
    let raw_device = Arc::new(Mutex::new(
        InputDevice::new(port, 115200, sw, sh).expect("连接失败")
    ));

    // 后台心跳守护
    let hb_dev = Arc::clone(&raw_device);
    thread::spawn(move || {
        loop {
            if let Ok(mut d) = hb_dev.lock() { d.heartbeat(); }
            thread::sleep(Duration::from_millis(1000));
        }
    });

    // 提示用户准备
    log("========================================");
    log("🎨 拟人化『画图』测试准备开始");
    log("👉 请在 5 秒内打开 Windows '画图' 软件，");
    log("👉 选择『铅笔』工具，并将窗口最大化！");
    log("========================================");
    for i in (1..=5).rev() {
        log(&format!("...倒计时 {} 秒...", i));
        thread::sleep(Duration::from_secs(1));
    }

    let mut bot = HumanDriver::new(Arc::clone(&raw_device), sw/2, sh/2);

    // 将鼠标移动到画布中心偏左开始
    bot.move_to_humanly(500, 500, 0.5);

    // ===========================================
    // 测试 1：直线条的非线性移动 (观察起步和刹车)
    // ===========================================
    log("🖊️ 测试 1: 变速画线...");
    { let mut d = raw_device.lock().unwrap(); d.mouse_down(true, false); }
    bot.move_to_humanly(1200, 500, 1.5); 
    { let mut d = raw_device.lock().unwrap(); d.mouse_up(); }

    thread::sleep(Duration::from_millis(500));

    // ===========================================
    // 测试 2：复杂的“V”字折返 (观察过冲和微调)
    // ===========================================
    log("🖊️ 测试 2: 连续折返轨迹...");
    bot.move_to_humanly(500, 700, 0.5); // 起点
    { let mut d = raw_device.lock().unwrap(); d.mouse_down(true, false); }
    
    // 向下画
    bot.move_to_humanly(850, 900, 1.2); 
    // 不松开鼠标，直接向上画
    bot.move_to_humanly(1200, 700, 1.2); 
    
    { let mut d = raw_device.lock().unwrap(); d.mouse_up(); }

    // ===========================================
    // 测试 3：落点抖动测试 (点阵图)
    // ===========================================
    log("🖊️ 测试 3: 多次点击同一目标的落点散布...");
    // 假设我们要点 (1000, 300) 这个按钮 10 次
    for _ in 0..10 {
        bot.move_to_humanly(1000, 300, 0.4);
        {
            let mut d = raw_device.lock().unwrap();
            d.mouse_down(true, false);
            thread::sleep(Duration::from_millis(30)); // 短按
            d.mouse_up();
        }
        // 故意离开一下，再回去点，看下次落点是否一致
        bot.move_to_humanly(1050, 350, 0.2); 
    }

    log("🎉 绘画测试结束！请观察画图板上的线条特征。");
} 