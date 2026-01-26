from human_hid import HumanHID
import time

# 建议：在画图软件（如 MSPaint）里运行这个脚本
# 你会看到鼠标画出漂亮的曲线，而不是生硬的直线

PORT = "COM3"

if __name__ == "__main__":
    print("🚀 启动拟人化引擎...")
    
    with HumanHID(PORT) as human:
        print("3秒后开始表演，请打开 画图工具 或 浏览器...")
        time.sleep(3)
        
        # 1. 顺滑移动 (画一个 8 字型 或 无限符号)
        # 注意：move_to 是绝对坐标，0.5 是屏幕中心
        print("1. 演示顺滑曲线移动...")
        human.move_to(0.2, 0.2, duration=0.8)
        human.move_to(0.8, 0.2, duration=0.8)
        human.move_to(0.2, 0.8, duration=0.8)
        human.move_to(0.8, 0.8, duration=0.8)
        human.move_to(0.5, 0.5, duration=0.5)
        
        # 2. 随机散布点击 (模拟连点，但每次位置都不同)
        print("2. 演示随机散布点击...")
        center_x, center_y = 0.5, 0.5
        for i in range(5):
            # 即使我们传入相同的坐标，human层会自动加入随机抖动
            # 你会发现鼠标围绕中心点像打靶一样分布
            human.click_at(center_x, center_y, duration=0.3)
            
        # 3. 拟人打字 (变速)
        print("3. 演示拟人打字...")
        # 找个输入框
        human.click_at(0.5, 0.5) 
        human.type("Hello Human! I am barely a bot...", wpm=60)
        
        # 4. 拖拽测试
        print("4. 演示拖拽...")
        human.drag_drop(0.2, 0.5, 0.8, 0.5, duration=1.5)
        
    print("✅ 演示结束")