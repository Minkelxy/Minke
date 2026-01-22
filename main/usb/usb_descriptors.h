#ifndef USB_DESCRIPTORS_H
#define USB_DESCRIPTORS_H

#include "tinyusb.h"
#include "tusb.h"

// Report IDs
#define REPORT_ID_KEYBOARD   1
#define REPORT_ID_MOUSE_REL  2
#define REPORT_ID_MOUSE_ABS  3

// 缓存大小
#define CFG_TUD_HID_EP_BUFSIZE 64

// 字符串数量 (解决编译错误)
#define USB_STRING_COUNT 4

// 导出给 main.c 使用
extern const uint8_t hid_configuration_descriptor[];
extern const tusb_desc_device_t desc_device;
extern const char *string_desc_arr[USB_STRING_COUNT]; 

#endif