#ifndef USB_DESCRIPTORS_H
#define USB_DESCRIPTORS_H

#include "tinyusb.h"
#include "tusb.h"

// Report IDs
#define REPORT_ID_KEYBOARD   1
#define REPORT_ID_MOUSE_REL  2
#define REPORT_ID_MOUSE_ABS  3

#define CFG_TUD_HID_EP_BUFSIZE 64
#define USB_STRING_COUNT 4

// 导出身份切换接口
void minke_select_identity(uint8_t index);
void minke_select_random_identity(void);

// 导出配置数组名，确保 main.c 引用一致
extern const uint8_t desc_configuration[];

#endif