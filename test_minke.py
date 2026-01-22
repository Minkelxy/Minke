import serial
import time
import struct
import argparse


def crc16_calculate(data):
    """
    计算CRC16校验值
    """
    crc = 0xFFFF
    crc16_table = [
        0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
        0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400,
        0x0001, 0xCC00, 0xD800, 0x1401, 0xF000, 0x3C01, 0x2801, 0xE400,
        0xA000, 0x6C01, 0x7801, 0xB400, 0x5001, 0x9C00, 0x8800, 0x4401,
        0x0002, 0xCC03, 0xD803, 0x1402, 0xF002, 0x3C03, 0x2803, 0xE402,
        0xA002, 0x6C03, 0x7803, 0xB402, 0x5002, 0x9C03, 0x8803, 0x4402,
        0x0003, 0xCC02, 0xD802, 0x1403, 0xF003, 0x3C02, 0x2802, 0xE403,
        0xA003, 0x6C02, 0x7802, 0xB403, 0x5003, 0x9C02, 0x8802, 0x4403,
        0x0004, 0xCC05, 0xD805, 0x1404, 0xF004, 0x3C05, 0x2805, 0xE404,
        0xA004, 0x6C05, 0x7805, 0xB404, 0x5004, 0x9C05, 0x8805, 0x4404,
        0x0005, 0xCC04, 0xD804, 0x1405, 0xF005, 0x3C04, 0x2804, 0xE405,
        0xA005, 0x6C04, 0x7804, 0xB405, 0x5005, 0x9C04, 0x8804, 0x4405,
        0x0006, 0xCC07, 0xD807, 0x1406, 0xF006, 0x3C07, 0x2807, 0xE406,
        0xA006, 0x6C07, 0x7807, 0xB406, 0x5006, 0x9C07, 0x8807, 0x4406,
        0x0007, 0xCC06, 0xD806, 0x1407, 0xF007, 0x3C06, 0x2806, 0xE407,
        0xA007, 0x6C06, 0x7806, 0xB407, 0x5007, 0x9C06, 0x8806, 0x4407,
        0x0008, 0xCC09, 0xD809, 0x1408, 0xF008, 0x3C09, 0x2809, 0xE408,
        0xA008, 0x6C09, 0x7809, 0xB408, 0x5008, 0x9C09, 0x8809, 0x4408,
        0x0009, 0xCC08, 0xD808, 0x1409, 0xF009, 0x3C08, 0x2808, 0xE409,
        0xA009, 0x6C08, 0x7808, 0xB409, 0x5009, 0x9C08, 0x8808, 0x4409,
        0x000A, 0xCC0B, 0xD80B, 0x140A, 0xF00A, 0x3C0B, 0x280B, 0xE40A,
        0xA00A, 0x6C0B, 0x780B, 0xB40A, 0x500A, 0x9C0B, 0x880B, 0x440A,
        0x000B, 0xCC0A, 0xD80A, 0x140B, 0xF00B, 0x3C0A, 0x280A, 0xE40B,
        0xA00B, 0x6C0A, 0x780A, 0xB40B, 0x500B, 0x9C0A, 0x880A, 0x440B,
        0x000C, 0xCC0D, 0xD80D, 0x140C, 0xF00C, 0x3C0D, 0x280D, 0xE40C,
        0xA00C, 0x6C0D, 0x780D, 0xB40C, 0x500C, 0x9C0D, 0x880D, 0x440C,
        0x000D, 0xCC0C, 0xD80C, 0x140D, 0xF00D, 0x3C0C, 0x280C, 0xE40D,
        0xA00D, 0x6C0C, 0x780C, 0xB40D, 0x500D, 0x9C0C, 0x880C, 0x440D,
        0x000E, 0xCC0F, 0xD80F, 0x140E, 0xF00E, 0x3C0F, 0x280F, 0xE40E,
        0xA00E, 0x6C0F, 0x780F, 0xB40E, 0x500E, 0x9C0F, 0x880F, 0x440E,
        0x000F, 0xCC0E, 0xD80E, 0x140F, 0xF00F, 0x3C0E, 0x280E, 0xE40F,
        0xA00F, 0x6C0E, 0x780E, 0xB40F, 0x500F, 0x9C0E, 0x880E, 0x440F
    ]
    
    for byte in data:
        tbl_idx = crc ^ byte
        crc = (crc >> 8) ^ crc16_table[tbl_idx & 0xFF]
    
    return crc


def create_packet(frame_type, payload):
    """
    创建符合Minke协议的数据包
    """
    # 起始字节
    packet = [0xAA]
    
    # 类型字节
    packet.append(frame_type)
    
    # 长度字节
    packet.append(len(payload))
    
    # 负载数据
    packet.extend(payload)
    
    # 计算CRC
    crc_data = [frame_type] + [len(payload)] + payload
    crc = crc16_calculate(crc_data)
    
    # 添加CRC（低字节在前）
    packet.append(crc & 0xFF)
    packet.append((crc >> 8) & 0xFF)
    
    # 结束字节
    packet.append(0x55)
    
    return packet


def send_packet(ser, packet):
    """
    发送数据包到串口
    """
    ser.write(bytes(packet))
    print(f"Sent packet: {' '.join([f'0x{b:02X}' for b in packet])}")


def test_keyboard(ser, keycode, press=True):
    """
    测试键盘功能
    """
    flags = 0x00 if press else 0x80  # 0x00为按下，0x80为释放
    payload = [keycode, flags, 0x00, 0x00, 0x00]  # [code, flags, reserved, delay_low, delay_high]
    packet = create_packet(0x01, payload)  # 0x01为键盘输入类型
    send_packet(ser, packet)


def test_mouse_move(ser, dx, dy):
    """
    测试鼠标移动功能
    """
    payload = [0x00, dx & 0xFF, dy & 0xFF, 0x00, 0x00]  # [buttons, dx, dy, delay_low, delay_high]
    packet = create_packet(0x02, payload)  # 0x02为鼠标输入类型
    send_packet(ser, packet)


def test_mouse_click(ser, button, press=True):
    """
    测试鼠标点击功能
    """
    btn_value = 0x00
    if button == 'left':
        btn_value = 0x01
    elif button == 'right':
        btn_value = 0x02
    elif button == 'middle':
        btn_value = 0x04
    
    # 如果是释放，则设置高位
    if not press:
        btn_value |= 0x80
    
    payload = [btn_value, 0x00, 0x00, 0x00, 0x00]  # [buttons, dx, dy, delay_low, delay_high]
    packet = create_packet(0x02, payload)  # 0x02为鼠标输入类型
    send_packet(ser, packet)


def test_system_command(ser, cmd):
    """
    测试系统命令
    """
    payload = [cmd, 0x00, 0x00, 0x00, 0x00]  # [command, reserved, reserved, delay_low, delay_high]
    packet = create_packet(0x03, payload)  # 0x03为系统输入类型
    send_packet(ser, packet)


def main():
    parser = argparse.ArgumentParser(description='Test Minke USB HID device')
    parser.add_argument('port', help='Serial port to connect to (e.g., /dev/ttyUSB0 or COM3)')
    parser.add_argument('--baud', type=int, default=921600, help='Baud rate (default: 921600)')
    
    args = parser.parse_args()
    
    try:
        ser = serial.Serial(args.port, args.baud, timeout=1)
        print(f"Connected to {args.port} at {args.baud} baud")
        
        # 等待设备就绪
        time.sleep(2)
        
        print("\nTesting keyboard functionality...")
        print("Pressing 'A' key...")
        test_keyboard(ser, 0x04)  # Press 'A'
        time.sleep(0.5)
        
        print("Releasing 'A' key...")
        test_keyboard(ser, 0x04, False)  # Release 'A'
        time.sleep(1)
        
        print("\nTesting mouse movement...")
        print("Moving mouse right and down...")
        test_mouse_move(ser, 20, 20)  # Move right and down
        time.sleep(1)
        
        print("Moving mouse left and up...")
        test_mouse_move(ser, -20, -20)  # Move left and up
        time.sleep(1)
        
        print("\nTesting mouse click...")
        print("Left mouse button press...")
        test_mouse_click(ser, 'left', True)  # Press left button
        time.sleep(0.2)
        
        print("Left mouse button release...")
        test_mouse_click(ser, 'left', False)  # Release left button
        time.sleep(1)
        
        print("\nSending heartbeat command...")
        test_system_command(ser, 0xFF)  # Heartbeat
        
        print("\nAll tests completed!")
        
        ser.close()
        
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        if 'ser' in locals() and ser.is_open:
            ser.close()


if __name__ == "__main__":
    main()