import time
import pyautogui
import pyperclip
from hid_driver import InputDevice

# ================= 关键配置 =================
pyautogui.FAILSAFE = False  # 禁用防故障保护，允许移动到 (0,0)
SERIAL_PORT = 'COM3'        # ⚠️ 修改为你的实际串口号
DELAY_BETWEEN_TESTS = 1.0

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def test_absolute_move(device, screen_w, screen_h):
    log("🔵 [测试 1] 绝对移动精度测试")
    targets = [
        (0.1, 0.1, "左上"), 
        (0.5, 0.5, "中心"), 
        (0.9, 0.9, "右下"),
        (0.0001, 0.0001, "极限左上(0,0)"), # 之前报错的地方
        (1.0, 1.0, "极限右下")
    ]
    
    for px, py, name in targets:
        device.mouse_move_to(px, py)
        # 稍微增加等待时间，确保系统坐标更新
        time.sleep(0.5) 
        
        real_x, real_y = pyautogui.position()
        expect_x, expect_y = int(px * (screen_w-1)), int(py * (screen_h-1))
        
        # 计算误差
        dist = ((real_x - expect_x)**2 + (real_y - expect_y)**2)**0.5
        
        if dist < 20: 
            log(f"   ✅ {name}通过: 目标({expect_x},{expect_y}) -> 实际({real_x},{real_y})")
        else:
            log(f"   ❌ {name}偏差过大: 误差 {dist:.1f}px")

def test_relative_move_logic(device):
    log("\n🔵 [测试 2] 相对移动拆包逻辑测试 (防溢出)")
    # 归位中心
    sw, sh = pyautogui.size()
    pyautogui.moveTo(sw//2, sh//2)
    time.sleep(0.5)
    start_x = pyautogui.position().x

    # 测试 1: 大数值正向移动 (500)
    move_dist = 500
    log(f"   👉 发送指令: 向右移动 {move_dist}")
    device.mouse_move(move_dist, 0)
    time.sleep(1.0) # 等待多次发送完成
    
    end_x = pyautogui.position().x
    diff = end_x - start_x
    
    # 由于系统加速，500单位通常 > 500像素，或者略少，关键是不能反向
    if diff > 100: 
        log(f"   ✅ 正向拆包成功: 实际移动 {diff} px")
    elif diff < 0:
        log(f"   ❌ 失败: 发生反向移动 (int8溢出未修复)")
    else:
        log(f"   ❌ 失败: 移动幅度过小")

    # 测试 2: 大数值负向移动 (-500)
    pyautogui.moveTo(sw//2, sh//2)
    time.sleep(0.5)
    start_x = pyautogui.position().x
    log(f"   👈 发送指令: 向左移动 -500")
    device.mouse_move(-500, 0)
    time.sleep(1.0)
    
    diff = pyautogui.position().x - start_x
    if diff < -100:
        log(f"   ✅ 负向拆包成功: 实际移动 {diff} px")
    else:
        log(f"   ❌ 失败: 实际移动 {diff} px")

def test_drag_drop(device):
    log("\n🔵 [测试 3] 拖拽功能 (Mouse Down/Up)")
    sw, sh = pyautogui.size()
    
    # 移动到屏幕左侧
    device.mouse_move_to(0.2, 0.5)
    time.sleep(0.5)
    
    log("   ✊ 按下左键...")
    device.mouse_down('left')
    time.sleep(0.2)
    
    log("   ➡️ 拖拽中...")
    for _ in range(10):
        device.mouse_move(30, 0) 
        time.sleep(0.05)
        
    log("   ✋ 松开左键")
    device.mouse_up('left')
    
    final_x = pyautogui.position().x
    if final_x > sw * 0.2 + 100:
        log("   ✅ 拖拽动作执行完毕")
    else:
        log("   ❌ 拖拽位移异常")

def test_scroll(device):
    log("\n🔵 [测试 4] 滚轮测试")
    log("   ⚠️  请肉眼观察页面滚动情况")
    
    log("   ⏬ 向下快速滚动 10 格")
    device.mouse_scroll(-10)
    time.sleep(1)
    
    log("   ⏫ 向上快速滚动 10 格")
    device.mouse_scroll(10)
    time.sleep(1)
    log("   ✅ 滚轮指令发送完毕")

def test_typing_and_clipboard(device):
    log("\n🔵 [测试 5] 键盘输入与组合键 (剪贴板验证)")
    
    # 注意：这里需要配合一个打开的文本框，否则Ctrl+C可能复制到空内容
    # 如果剪贴板内容没变，说明复制失败（或者没选中东西）
    
    test_str = "Hello_ESP32"
    log(f"   ⌨️  模拟打字 '{test_str}'...")
    device.type_string(test_str)
    time.sleep(0.5)
    
    log("   ⌨️  全选 (Ctrl+A)")
    device.hotkey('ctrl', 'a')
    time.sleep(0.5)
    
    log("   ⌨️  复制 (Ctrl+C)")
    device.hotkey('ctrl', 'c')
    time.sleep(0.5)
    
    content = pyperclip.paste()
    if test_str.lower() in content.lower():
        log(f"   ✅ 验证成功! 剪贴板内容: '{content}'")
    else:
        log(f"   ❌ 验证失败. 剪贴板内容: '{content}' (请确认焦点在文本框)")

def test_function_keys(device):
    log("\n🔵 [测试 6] 特殊按键测试")
    log("   按一下 Win 键...")
    device.key_press('win')
    time.sleep(1)
    log("   再按一下 Win 键...")
    device.key_press('win')
    time.sleep(1)
    log("   ✅ 特殊按键测试完毕")

# ================= 主程序 =================
if __name__ == "__main__":
    sw, sh = pyautogui.size()
    print(f"🖥️  屏幕分辨率: {sw} x {sh}")
    print(f"🔌 连接串口: {SERIAL_PORT}")
    
    try:
        with InputDevice(SERIAL_PORT) as mouse_kb:
            print("\n🚀 驱动加载成功! 3 秒后开始...")
            print("⚠️  请切换到一个空白记事本窗口，并将输入法切到英文！")
            for i in range(3, 0, -1):
                print(f"   {i}...")
                time.sleep(1)
            
            test_absolute_move(mouse_kb, sw, sh)
            time.sleep(DELAY_BETWEEN_TESTS)
            
            test_relative_move_logic(mouse_kb)
            time.sleep(DELAY_BETWEEN_TESTS)
            
            test_drag_drop(mouse_kb)
            time.sleep(DELAY_BETWEEN_TESTS)
            
            test_scroll(mouse_kb)
            time.sleep(DELAY_BETWEEN_TESTS)
            
            test_function_keys(mouse_kb)
            time.sleep(DELAY_BETWEEN_TESTS)
            
            test_typing_and_clipboard(mouse_kb)
            
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
    
    print("\n🎉 全套测试结束")