#ifndef UART_PROTOCOL_H
#define UART_PROTOCOL_H

#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

// ==========================================
// 1. 协议配置
// ==========================================
#define FRAME_HEAD          0xAA
#define FRAME_TAIL          0x55
#define FRAME_LEN           11  // 固定 11 字节

// ==========================================
// 2. 事件类型定义
// ==========================================
#define EVENT_TYPE_KEYBOARD   0x01
#define EVENT_TYPE_MOUSE_REL  0x02  // 相对鼠标
#define EVENT_TYPE_MOUSE_ABS  0x03  // 绝对鼠标
#define EVENT_TYPE_SYSTEM     0x04  // 系统指令（心跳/身份切换）

// ==========================================
// 3. 系统子指令定义 (仅在 EVENT_TYPE_SYSTEM 时有效)
// ==========================================
#define SYS_CMD_HEARTBEAT     0xFF  // 维持连接心跳
#define SYS_CMD_SET_ID        0x10  // 切换身份池索引

// ==========================================
// 4. 标志位定义
// ==========================================
#define FLAG_KEY_PRESS      0x00
#define FLAG_KEY_RELEASE    0x80

// ==========================================
// 5. 数据结构
// ==========================================
typedef struct {
    uint8_t type;           // 事件类型
    uint16_t delay_ms;      // 延迟（毫秒）

    union {
        // A. 键盘专用参数
        struct {
            uint8_t keycode;    // 键值 (HID Usage ID)
            uint8_t flags;      // 0=Press, 0x80=Release
            uint8_t modifier;   // 修饰键 (Ctrl/Shift/Alt/Win 掩码)
        } key;

        // B. 鼠标专用参数
        struct {
            uint8_t buttons;    // 按键掩码 (Bit0=左, Bit1=右, Bit2=中)
            int8_t  wheel;      // 滚轮步数
            int16_t x;          // X 坐标或位移
            int16_t y;          // Y 坐标或位移
        } mouse;

        // C. 系统专用参数 (新增)
        struct {
            uint8_t command;    // 系统指令代码 (如 SYS_CMD_HEARTBEAT)
            uint8_t data;       // 指令携带的数据 (如身份索引号)
            uint8_t reserved[4]; // 预留对齐
        } system;
    } param;
} InputEvent;

// ==========================================
// 6. 解析上下文
// ==========================================
typedef struct {
    uint8_t buffer[FRAME_LEN];
    uint8_t received_count;
} RxContext;

void rx_context_init(RxContext* ctx);
bool rx_process_byte(RxContext* ctx, uint8_t byte, InputEvent* evt);

#ifdef __cplusplus
}
#endif

#endif