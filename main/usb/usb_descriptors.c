/*
 * usb_descriptors.c
 * 包含修改后的 PID (0x4004) 和 纯字节码描述符
 */
#include "usb_descriptors.h"
#include "tusb.h"
#include "class/hid/hid.h"

// =============================================================================
// 0. 补充缺失的 HID 定义
// =============================================================================
#ifndef HID_USAGE_PAGE_DESKTOP
#define HID_USAGE_PAGE_DESKTOP   0x01
#endif

#ifndef HID_USAGE_PAGE_CONSUMER
#define HID_USAGE_PAGE_CONSUMER  0x0C
#endif

#ifndef HID_USAGE_MOUSE
#define HID_USAGE_MOUSE          0x02
#endif

#ifndef HID_USAGE_X
#define HID_USAGE_X              0x30
#endif

#ifndef HID_USAGE_Y
#define HID_USAGE_Y              0x31
#endif

#ifndef HID_USAGE_WHEEL
#define HID_USAGE_WHEEL          0x38
#endif

// =============================================================================
// 1. HID Report Descriptor
// =============================================================================
uint8_t const desc_hid_report[] = {
    // ---------------------------------------------------------
    // A. 键盘 (使用 TinyUSB 标准宏)
    // ---------------------------------------------------------
    TUD_HID_REPORT_DESC_KEYBOARD( HID_REPORT_ID(REPORT_ID_KEYBOARD) ),

    // ---------------------------------------------------------
    // B. 相对鼠标 (Raw Bytes 定义，包含 Wheel 和 Pan)
    // ---------------------------------------------------------
    0x05, 0x01,        // Usage Page (Desktop)
    0x09, 0x02,        // Usage (Mouse)
    0xA1, 0x01,        // Collection (Application)
        0x85, REPORT_ID_MOUSE_REL, // Report ID

        0x09, 0x01,    // Usage (Pointer)
        0xA1, 0x00,    // Collection (Physical)
            // --- 1. 按键 (Buttons) ---
            0x05, 0x09, // Usage Page (Button)
            0x19, 0x01, 0x29, 0x03, // Usage Min 1, Max 3
            0x15, 0x00, 0x25, 0x01, // Logical Min 0, Max 1
            0x95, 0x03, 0x75, 0x01, // Count 3, Size 1
            0x81, 0x02, // Input (Data, Var, Abs)
            
            // Padding (5 bits)
            0x95, 0x01, 0x75, 0x05, // Count 1, Size 5
            0x81, 0x03, // Input (Cnst, Var, Abs)

            // --- 2. 移动 (X, Y) ---
            0x05, 0x01, // Usage Page (Desktop)
            0x09, 0x30, 0x09, 0x31, // Usage X, Y
            0x15, 0x81, 0x25, 0x7F, // Logical Min -127, Max 127
            0x95, 0x02, 0x75, 0x08, // Count 2, Size 8
            0x81, 0x06, // Input (Data, Var, Rel)

            // --- 3. 垂直滚轮 (Wheel) ---
            0x09, 0x38, // Usage Wheel
            0x15, 0x81, 0x25, 0x7F,
            0x95, 0x01, 0x75, 0x08, // Count 1, Size 8
            0x81, 0x06,

            // --- 4. 水平滚轮 (AC Pan) ---
            0x05, 0x0C, // Usage Page (Consumer)
            0x0A, 0x38, 0x02, // Usage AC Pan (0x0238)
            0x15, 0x81, 0x25, 0x7F,
            0x95, 0x01, 0x75, 0x08,
            0x81, 0x06,

        0xC0,          // End Collection
    0xC0,              // End Collection

    // ---------------------------------------------------------
    // C. 绝对鼠标 (保持原样)
    // ---------------------------------------------------------
    HID_USAGE_PAGE ( 0x01 ), 
    HID_USAGE      ( 0x02 ),
    HID_COLLECTION ( HID_COLLECTION_APPLICATION ),
        0x85, REPORT_ID_MOUSE_ABS, 
        HID_USAGE ( 0x01 ),
        HID_COLLECTION ( HID_COLLECTION_PHYSICAL ),
            HID_USAGE_PAGE ( HID_USAGE_PAGE_BUTTON ),
            HID_USAGE_MIN  ( 1 ),
            HID_USAGE_MAX  ( 3 ),
            HID_LOGICAL_MIN( 0 ),
            HID_LOGICAL_MAX( 1 ),
            HID_REPORT_COUNT( 3 ),
            HID_REPORT_SIZE ( 1 ),
            HID_INPUT ( HID_DATA | HID_VARIABLE | HID_ABSOLUTE ),
            
            HID_REPORT_COUNT( 1 ),
            HID_REPORT_SIZE ( 5 ),
            HID_INPUT ( HID_CONSTANT ),

            HID_USAGE_PAGE ( 0x01 ),
            HID_USAGE ( 0x30 ), // X
            HID_USAGE ( 0x31 ), // Y
            HID_LOGICAL_MIN( 0 ),
            HID_LOGICAL_MAX_N( 32767, 2 ),
            HID_REPORT_COUNT( 2 ),
            HID_REPORT_SIZE ( 16 ),
            HID_INPUT ( HID_DATA | HID_VARIABLE | HID_ABSOLUTE ),
        HID_COLLECTION_END,
    HID_COLLECTION_END
};

// =============================================================================
// 2. 配置描述符
// =============================================================================
#define USB_CONFIG_TOTAL_LEN  (TUD_CONFIG_DESC_LEN + TUD_HID_DESC_LEN)

const uint8_t hid_configuration_descriptor[] = {
    TUD_CONFIG_DESCRIPTOR(1, 1, 0, USB_CONFIG_TOTAL_LEN, 0x20, 100),
    TUD_HID_DESCRIPTOR(0, 0, HID_ITF_PROTOCOL_NONE, sizeof(desc_hid_report), 0x81, CFG_TUD_HID_EP_BUFSIZE, 10)
};

// =============================================================================
// 3. 字符串描述符
// =============================================================================
const char *string_desc_arr[USB_STRING_COUNT] = {
    (const char[]) { 0x09, 0x04 }, // 0: English
    "Espressif",                   // 1: Manufacturer
    "ESP32-S3 HID Device",         // 2: Product
    "123456",                      // 3: Serial
};

// =============================================================================
// 4. 设备描述符
// =============================================================================
const tusb_desc_device_t desc_device = {
    .bLength            = sizeof(tusb_desc_device_t),
    .bDescriptorType    = TUSB_DESC_DEVICE,
    .bcdUSB             = 0x0200,
    .bDeviceClass       = 0x00,
    .bDeviceSubClass    = 0x00,
    .bDeviceProtocol    = 0x00,
    .bMaxPacketSize0    = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor           = 0xCAFE,
    
    // ===================================
    // 关键修改：PID 改为 0x4004
    // 强制 Windows 重新识别设备
    // ===================================
    .idProduct          = 0x4004, 
    
    .bcdDevice          = 0x0100,
    .iManufacturer      = 0x01,
    .iProduct           = 0x02,
    .iSerialNumber      = 0x03,
    .bNumConfigurations = 0x01
};

// =============================================================================
// 5. HID Report Callback
// =============================================================================
uint8_t const *tud_hid_descriptor_report_cb(uint8_t instance) {
    (void) instance;
    return desc_hid_report; 
}