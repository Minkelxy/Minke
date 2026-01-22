#include "uart_protocol.h"
#include <string.h>

void rx_context_init(RxContext* ctx) {
    memset(ctx, 0, sizeof(RxContext));
    ctx->received_count = 0;
}

// ---------------------------------------------------------
// 核心解析逻辑
// ---------------------------------------------------------
static void parse_frame(const uint8_t* buf, InputEvent* evt) {
    memset(evt, 0, sizeof(InputEvent));
    
    evt->type     = buf[1];
    // 延迟固定在最后两字节 (Index 8, 9)
    evt->delay_ms = (uint16_t)(buf[8] | (buf[9] << 8));

    if (evt->type == EVENT_TYPE_KEYBOARD) {
        // === 键盘映射 ===
        // Buf[2]: Keycode
        // Buf[3]: Flags (Press/Release)
        // Buf[4]: Modifier (Ctrl/Shift...)
        evt->param.key.keycode  = buf[2];
        evt->param.key.flags    = buf[3];
        evt->param.key.modifier = buf[4]; 
    } 
    else {
        // === 鼠标映射 (REL / ABS) ===
        // Buf[2]: Buttons
        // Buf[3]: Wheel (滚轮)
        // Buf[4-5]: X
        // Buf[6-7]: Y
        evt->param.mouse.buttons = buf[2];
        evt->param.mouse.wheel   = (int8_t)buf[3];
        evt->param.mouse.x       = (int16_t)(buf[4] | (buf[5] << 8));
        evt->param.mouse.y       = (int16_t)(buf[6] | (buf[7] << 8));
    }
}

// ---------------------------------------------------------
// 自愈逻辑 (保持不变)
// ---------------------------------------------------------
static void try_resync(RxContext* ctx, uint8_t last_byte) {
    uint8_t temp[FRAME_LEN];
    memcpy(temp, ctx->buffer, FRAME_LEN - 1);
    temp[FRAME_LEN - 1] = last_byte;

    for (int i = 1; i < FRAME_LEN; i++) {
        if (temp[i] == FRAME_HEAD) {
            uint8_t valid_len = FRAME_LEN - i;
            memcpy(ctx->buffer, &temp[i], valid_len);
            ctx->received_count = valid_len;
            return;
        }
    }
    ctx->received_count = 0;
}

bool rx_process_byte(RxContext* ctx, uint8_t byte, InputEvent* evt) {
    if (ctx->received_count == 0) {
        if (byte == FRAME_HEAD) {
            ctx->buffer[0] = byte;
            ctx->received_count = 1;
        }
        return false;
    }

    if (ctx->received_count < FRAME_LEN - 1) {
        ctx->buffer[ctx->received_count++] = byte;
        return false;
    }

    if (byte == FRAME_TAIL) {
        ctx->buffer[FRAME_LEN - 1] = byte;
        parse_frame(ctx->buffer, evt);
        ctx->received_count = 0;
        return true;
    } 
    else {
        try_resync(ctx, byte);
        return false;
    }
}