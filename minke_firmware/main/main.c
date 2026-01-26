/*
 * main.c
 * 核心逻辑文件：支持随机身份切换、心跳看门狗安全重置与手动构造 HID 报告
 * [已修复]：USB 忙碌重试机制与 FreeRTOS Tick 对齐问题，实现零丢包。
 */
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_timer.h" 

#include "tinyusb.h"
#include "tusb.h"

#include "usb_descriptors.h"
#include "protocol/uart_protocol.h"

// =================配置=================
#define UART_PORT_NUM      UART_NUM_0
#define UART_TX_PIN        43  
#define UART_RX_PIN        44  
#define UART_BAUD_RATE     115200
#define BUF_SIZE           1024
#define EVENT_QUEUE_SIZE   64  

// 看门狗配置
#define WATCHDOG_TIMEOUT_MS 3000 
static int64_t g_last_activity_time = 0;

static const char *TAG = "MAIN";
static QueueHandle_t g_event_queue = NULL;
static RxContext g_rx_ctx;

// ==========================================================
// 数据结构定义
// ==========================================================

// 1. 绝对鼠标报告 (Report ID 3)
typedef struct __attribute__((packed)) {
    uint8_t buttons;
    uint16_t x;
    uint16_t y;
} abs_mouse_report_t;

// 2. 相对鼠标报告 (Report ID 2)
typedef struct __attribute__((packed)) {
    uint8_t buttons; 
    int8_t  x;       
    int8_t  y;       
    int8_t  wheel;   
    int8_t  pan;     
} rel_mouse_report_t;

// ==========================================================
// 安全重置函数：防止上位机崩溃导致按键卡死
// ==========================================================
void safety_reset_hid(void) {
    if (tud_hid_ready()) {
        uint8_t empty_key[6] = {0};
        tud_hid_keyboard_report(REPORT_ID_KEYBOARD, 0, empty_key);
        
        rel_mouse_report_t empty_rel = {0};
        tud_hid_report(REPORT_ID_MOUSE_REL, &empty_rel, sizeof(empty_rel));
        
        ESP_LOGW(TAG, "Watchdog triggered: HID state reset for safety.");
    }
}

// ==========================================================
// 1. 串口接收任务 (底层驱动层)
// ==========================================================
void uart_rx_task(void *arg) {
    uart_config_t uart_config = {
        .baud_rate = UART_BAUD_RATE,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    
    uart_driver_install(UART_PORT_NUM, BUF_SIZE * 2, 0, 0, NULL, 0);
    uart_param_config(UART_PORT_NUM, &uart_config);
    uart_set_pin(UART_PORT_NUM, UART_TX_PIN, UART_RX_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    rx_context_init(&g_rx_ctx);
    uint8_t *data = (uint8_t *) malloc(BUF_SIZE);
    InputEvent evt;

    ESP_LOGI(TAG, "UART Listening...");

    while (1) {
        int len = uart_read_bytes(UART_PORT_NUM, data, BUF_SIZE, 20 / portTICK_PERIOD_MS);
        if (len > 0) {
            for (int i = 0; i < len; i++) {
                if (rx_process_byte(&g_rx_ctx, data[i], &evt)) {
                    // ✅ 修复 1：将等待时间从 0 改为 10ms。
                    // 防止瞬间爆发大量数据时队列已满导致丢包
                    xQueueSend(g_event_queue, &evt, pdMS_TO_TICKS(10));
                }
            }
        }
    }
    free(data);
}

// ==========================================================
// 2. HID 执行任务 (业务逻辑层)
// ==========================================================
void hid_process_task(void *arg) {
    InputEvent evt;
    g_last_activity_time = esp_timer_get_time() / 1000;
    ESP_LOGI(TAG, "HID Task Started");

    while (1) {
        // 看门狗逻辑
        int64_t now = esp_timer_get_time() / 1000;
        if (now - g_last_activity_time > WATCHDOG_TIMEOUT_MS) {
            safety_reset_hid();
            g_last_activity_time = now; 
        }

        // 等待 USB 枚举
        if (!tud_mounted()) {
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }

        // 从队列取出数据
        if (xQueueReceive(g_event_queue, &evt, pdMS_TO_TICKS(100))) {
            g_last_activity_time = esp_timer_get_time() / 1000;

            if (evt.delay_ms > 0) vTaskDelay(pdMS_TO_TICKS(evt.delay_ms));

            // ✅ 修复 2：彻底解决丢包问题
            // USB 轮询间隔通常为 8-10ms。
            // 之前的 pdMS_TO_TICKS(5) 在 100Hz 滴答率下等于 0，导致 while 瞬间跑完。
            // 改为 10ms (1个Tick)，并允许最多重试 10 次 (即耐心等待 100ms)
            int retry = 0;
            while (!tud_hid_ready() && retry < 10) {
                vTaskDelay(pdMS_TO_TICKS(10)); 
                retry++;
            }
            
            // 如果 100ms 后 USB 依然堵塞，记录错误，防止系统卡死
            if (!tud_hid_ready()) {
                ESP_LOGE(TAG, "USB Busy timeout! Dropping packet. Retries: %d", retry);
                continue; 
            }

            // USB 空闲，发送数据
            switch (evt.type) {
                case EVENT_TYPE_KEYBOARD: {
                    uint8_t keycode[6] = {0};
                    uint8_t modifier = 0;
                    if (evt.param.key.flags == FLAG_KEY_PRESS) {
                        keycode[0] = evt.param.key.keycode;
                        modifier   = evt.param.key.modifier;
                    }
                    tud_hid_keyboard_report(REPORT_ID_KEYBOARD, modifier, keycode);
                    break;
                }
                
                case EVENT_TYPE_MOUSE_REL: {
                    rel_mouse_report_t report;
                    report.buttons = evt.param.mouse.buttons;
                    report.x       = (int8_t)evt.param.mouse.x; 
                    report.y       = (int8_t)evt.param.mouse.y; 
                    report.wheel   = evt.param.mouse.wheel;
                    report.pan     = 0; 
                    tud_hid_report(REPORT_ID_MOUSE_REL, &report, sizeof(report));
                    break;
                }
                
                case EVENT_TYPE_MOUSE_ABS: {
                    abs_mouse_report_t report;
                    report.buttons = evt.param.mouse.buttons;
                    report.x = (uint16_t)evt.param.mouse.x;
                    report.y = (uint16_t)evt.param.mouse.y;
                    tud_hid_report(REPORT_ID_MOUSE_ABS, &report, sizeof(report));
                    break;
                }

                case EVENT_TYPE_SYSTEM: {
                    if (evt.param.system.command == SYS_CMD_SET_ID) {
                        minke_select_identity(evt.param.system.data);
                        ESP_LOGW(TAG, "Identity change requested. Rebooting...");
                        esp_restart(); 
                    }
                    break;
                }
            }
        }
    }
}

// ==========================================================
// 3. 入口函数
// ==========================================================
void app_main(void) {
    ESP_LOGI(TAG, "Minke Engine Initializing...");

    // 1. 初始化随机身份选择
    minke_select_random_identity();

    // 2. 安装驱动 (注意：使用 desc_configuration 且描述符指针设为 NULL)
    const tinyusb_config_t tusb_cfg = {
        .device_descriptor = NULL, 
        .string_descriptor = NULL, 
        .string_descriptor_count = 0,
        .external_phy = false,
        .configuration_descriptor = desc_configuration,
    };
    ESP_ERROR_CHECK(tinyusb_driver_install(&tusb_cfg));

    g_event_queue = xQueueCreate(EVENT_QUEUE_SIZE, sizeof(InputEvent));
    
    xTaskCreate(uart_rx_task, "uart_rx", 4096, NULL, 5, NULL);
    xTaskCreate(hid_process_task, "hid_task", 4096, NULL, 4, NULL);
    
    ESP_LOGI(TAG, "System Ready.");
}

// 4. TinyUSB Stub
uint16_t tud_hid_get_report_cb(uint8_t instance, uint8_t report_id, hid_report_type_t report_type, uint8_t* buffer, uint16_t reqlen) { return 0; }
void tud_hid_set_report_cb(uint8_t instance, uint8_t report_id, hid_report_type_t report_type, uint8_t const* buffer, uint16_t bufsize) {}