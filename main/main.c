/*
 * main.c
 * 核心逻辑文件：手动构造 HID 报告结构，确保滚轮数据不被系统忽略
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
#define EVENT_QUEUE_SIZE   20 

static const char *TAG = "MAIN";
static QueueHandle_t g_event_queue = NULL;
static RxContext g_rx_ctx;

// ==========================================================
// 数据结构定义 (关键修改)
// ==========================================================

// 1. 绝对鼠标报告 (Report ID 3)
typedef struct __attribute__((packed)) {
    uint8_t buttons;
    uint16_t x;
    uint16_t y;
} abs_mouse_report_t;

// 2. 相对鼠标报告 (Report ID 2)
// 手动定义 5 字节结构，严格对应描述符
typedef struct __attribute__((packed)) {
    uint8_t buttons; // Byte 0
    int8_t  x;       // Byte 1
    int8_t  y;       // Byte 2
    int8_t  wheel;   // Byte 3: 垂直滚轮
    int8_t  pan;     // Byte 4: 水平滚轮 (AC Pan)
} rel_mouse_report_t;


// ==========================================================
// 1. 串口接收任务
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
                    xQueueSend(g_event_queue, &evt, 0);
                }
            }
        }
    }
    free(data);
}

// ==========================================================
// 2. HID 执行任务
// ==========================================================
void hid_process_task(void *arg) {
    InputEvent evt;
    ESP_LOGI(TAG, "HID Task Started");

    while (1) {
        if (!tud_mounted()) {
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }

        if (xQueueReceive(g_event_queue, &evt, pdMS_TO_TICKS(10))) {
            if (evt.delay_ms > 0) vTaskDelay(pdMS_TO_TICKS(evt.delay_ms));

            // 等待 USB 就绪
            int retry = 0;
            while (!tud_hid_ready() && retry < 5) {
                vTaskDelay(pdMS_TO_TICKS(10));
                retry++;
            }
            if (!tud_hid_ready()) continue;

            // 分发处理
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
                    // ================= 关键修改 =================
                    // 使用自定义结构体发送 5 字节数据
                    rel_mouse_report_t report;
                    report.buttons = evt.param.mouse.buttons;
                    report.x       = (int8_t)evt.param.mouse.x; // 强转回 int8
                    report.y       = (int8_t)evt.param.mouse.y; // 强转回 int8
                    report.wheel   = evt.param.mouse.wheel;
                    report.pan     = 0; // 暂时不用水平滚动

                    tud_hid_report(REPORT_ID_MOUSE_REL, &report, sizeof(report));
                    // ===========================================
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
            }
        }
    }
}

// ==========================================================
// 3. 入口
// ==========================================================
void app_main(void) {
    ESP_LOGI(TAG, "System Init...");

    const tinyusb_config_t tusb_cfg = {
        .device_descriptor = &desc_device,
        .string_descriptor = string_desc_arr,
        .string_descriptor_count = USB_STRING_COUNT,
        .external_phy = false,
        .configuration_descriptor = hid_configuration_descriptor, 
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