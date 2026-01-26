/*
 * usb_descriptors.c
 * 包含身份池、动态描述符回调以及修复链接错误的桩函数
 */
#include "usb_descriptors.h"
#include "tusb.h"
#include "esp_random.h"
#include "esp_log.h"
#include <string.h>

// =============================================================================
// 0. 修复链接错误：提供 tinyusb_set_descriptors 桩函数
// =============================================================================
// 当禁用 CONFIG_TINYUSB_DESC_USE_DEFAULT 时，必须提供此函数以满足 tinyusb_driver_install 的调用
esp_err_t tinyusb_set_descriptors(const tinyusb_config_t *config) {
    // 因为我们直接接管了 tud_descriptor_xxx_cb 回调，所以这里不需要做任何事
    return ESP_OK; 
}

// =============================================================================
// 1. 身份池定义
// =============================================================================
typedef struct {
    uint16_t vid;
    uint16_t pid;
    const char* manufacturer;
    const char* product;
    const char* serial;
} usb_identity_t;

static const usb_identity_t identity_pool[] = {
    {0x046D, 0xC077, "Logitech", "G102 Prodigy", "SN-LOGI-2026A"},
    {0x1532, 0x0067, "Razer", "DeathAdder Elite", "RZ-DEATH-9912"},
    {0x045E, 0x00CB, "Microsoft", "USB Optical Mouse", "MS-OFFICE-3301"},
    {0x0951, 0x16A4, "Kingston", "HyperX Keyboard", "KHX-S3-8821"}
};

#define IDENTITY_COUNT (sizeof(identity_pool) / sizeof(usb_identity_t))
static uint8_t g_id_idx = 0;

void minke_select_identity(uint8_t index) {
    if (index < IDENTITY_COUNT) g_id_idx = index;
}

void minke_select_random_identity(void) {
    g_id_idx = esp_random() % IDENTITY_COUNT;
}

// =============================================================================
// 2. 动态描述符回调 (TinyUSB 核心回调)
// =============================================================================

// A. 设备描述符回调
uint8_t const *tud_descriptor_device_cb(void) {
    static tusb_desc_device_t desc = {
        .bLength = sizeof(tusb_desc_device_t),
        .bDescriptorType = TUSB_DESC_DEVICE,
        .bcdUSB = 0x0200,
        .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
        .bcdDevice = 0x0100,
        .iManufacturer = 0x01, .iProduct = 0x02, .iSerialNumber = 0x03,
        .bNumConfigurations = 0x01
    };
    // 注入当前身份池的 VID/PID
    desc.idVendor = identity_pool[g_id_idx].vid;
    desc.idProduct = identity_pool[g_id_idx].pid;
    return (uint8_t const *) &desc;
}

// B. 配置描述符回调
uint8_t const desc_hid_report[] = {
    // A. 键盘 (ID 1)
    TUD_HID_REPORT_DESC_KEYBOARD( HID_REPORT_ID(REPORT_ID_KEYBOARD) ),

    // B. 相对鼠标 (ID 2: 5字节格式，包含滚轮与Pan)
    0x05, 0x01, 0x09, 0x02, 0xA1, 0x01, 0x85, REPORT_ID_MOUSE_REL,
    0x09, 0x01, 0xA1, 0x00, 0x05, 0x09, 0x19, 0x01, 0x29, 0x03, 0x15, 0x00,
    0x25, 0x01, 0x95, 0x03, 0x75, 0x01, 0x81, 0x02, 0x95, 0x01, 0x75, 0x05,
    0x81, 0x03, 0x05, 0x01, 0x09, 0x30, 0x09, 0x31, 0x15, 0x81, 0x25, 0x7F,
    0x95, 0x02, 0x75, 0x08, 0x81, 0x06, 0x09, 0x38, 0x15, 0x81, 0x25, 0x7F,
    0x95, 0x01, 0x75, 0x08, 0x81, 0x06, 0x05, 0x0C, 0x0A, 0x38, 0x02, 0x15,
    0x81, 0x25, 0x7F, 0x95, 0x01, 0x75, 0x08, 0x81, 0x06, 0xC0, 0xC0,

    // C. 绝对鼠标 (ID 3)
    0x05, 0x01, 0x09, 0x02, 0xA1, 0x01, 0x85, REPORT_ID_MOUSE_ABS,
    0x09, 0x01, 0xA1, 0x00, 0x05, 0x09, 0x19, 0x01, 0x29, 0x03, 0x15, 0x00,
    0x25, 0x01, 0x95, 0x03, 0x75, 0x01, 0x81, 0x02, 0x95, 0x01, 0x75, 0x05,
    0x81, 0x03, 0x05, 0x01, 0x09, 0x30, 0x09, 0x31, 0x15, 0x00, 0x26, 0xFF,
    0x7F, 0x95, 0x02, 0x75, 0x10, 0x81, 0x02, 0xC0, 0xC0
};

uint8_t const *tud_hid_descriptor_report_cb(uint8_t instance) {
    return desc_hid_report;
}

uint8_t const desc_configuration[] = {
    TUD_CONFIG_DESCRIPTOR(1, 1, 0, (TUD_CONFIG_DESC_LEN + TUD_HID_DESC_LEN), 0x20, 100),
    TUD_HID_DESCRIPTOR(0, 0, HID_ITF_PROTOCOL_NONE, sizeof(desc_hid_report), 0x81, CFG_TUD_HID_EP_BUFSIZE, 10)
};

uint8_t const *tud_descriptor_configuration_cb(uint8_t index) {
    return desc_configuration;
}

// C. 字符串描述符回调
static uint16_t _desc_str[32];
uint16_t const *tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void) langid;
    uint8_t chr_count;
    const usb_identity_t* id = &identity_pool[g_id_idx];

    if (index == 0) {
        memcpy(&_desc_str[1], (uint16_t[]){0x0904}, 2);
        chr_count = 1;
    } else {
        const char* str = (index == 1) ? id->manufacturer : (index == 2) ? id->product : id->serial;
        if (!str) return NULL;
        chr_count = strlen(str);
        if (chr_count > 31) chr_count = 31;
        for (uint8_t i = 0; i < chr_count; i++) _desc_str[1 + i] = str[i];
    }
    _desc_str[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * chr_count + 2));
    return _desc_str;
}