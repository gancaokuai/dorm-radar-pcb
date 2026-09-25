# 防宿管雷达固件 v0.1

这是项目的初步程序部分，目标是先打通最小闭环：

```text
LD2450 -> TX ESP32-C3 -> ESP-NOW -> RX ESP32-C3 -> LED
```

当前版本不包含摄像头、麦克风、云端、充电和联网服务。

## 目录

```text
firmware/
  arduino/tx/tx.ino                 TX 固件
  arduino/rx/rx.ino                 RX 固件
  lib/DormRadarConfig/              引脚和判定参数
  lib/DormRadarProtocol/            ESP-NOW 数据包格式与 CRC
  lib/Ld2450/                       LD2450 UART 流式解析器
  test/native/                      可选的电脑端单元测试
  build.ps1                         使用已安装 Arduino CLI 编译
```

## 当前行为

TX 端：

- 以 256000 baud 读取 LD2450。
- 连续解析 30 字节 LD2450 数据帧，支持串口数据分片。
- 从最多 3 个目标中选择最近目标。
- 默认检测区域为雷达前方 `x = -700..700 mm`、`y = 100..2500 mm`。
- 目标进入区域后立即触发，离开后保持 1500 ms。
- LD2450 坐标使用符号幅值编码，距离由 x/y 计算。
- 每 500 ms 至少发送一次 ESP-NOW；状态变化时立即发送。

RX 端：

- 校验协议版本、包类型和 CRC-8。
- 收到有效警报时点亮 LED。
- 1.8 秒收不到心跳时，以短闪方式提示无线链路丢失。
- 无警报时 LED 熄灭。

## 硬件引脚

| 功能 | ESP32-C3 GPIO |
| --- | ---: |
| LD2450 RX，接雷达 TX | GPIO5 |
| LD2450 TX，接雷达 RX | GPIO4 |
| RX LED 控制 | GPIO7 |
| UART0 TX/RX | GPIO21 / GPIO20 |
| BOOT | GPIO9 |
| EN | EN |

LED 电路为 3.3 V -> 电阻 -> LED 阳极，LED 阴极接 GPIO7，因此固件按低电平点亮处理。

## 编译

需要 Arduino CLI 和 `esp32:esp32` 开发板包。本机已缓存 ESP32 Arduino Core 2.0.14。

```powershell
cd F:\防宿管雷达\firmware
.\build.ps1 all
```

也可以分别编译：

```powershell
.\build.ps1 tx
.\build.ps1 rx
```

输出位于：

```text
firmware\.build\tx\
firmware\.build\rx\
```

## 烧录

1. 将 J3 编程口接到 USB-TTL 串口模块。
2. 使用 Arduino IDE 打开对应的 `tx.ino` 或 `rx.ino`。
3. 开发板选择 `ESP32C3 Dev Module`。
4. UART 下载时需要 GPIO8 上拉到 3.3 V、GPIO9 拉低；否则芯片会进入 USB_BOOT 模式。
5. 两块板必须使用同一个 ESP-NOW 信道，当前固定为信道 1。

## 调参

引脚、区域、触发时间和无线信道都在：

```text
firmware/lib/DormRadarConfig/src/BoardConfig.h
```

首板联调建议：

1. 先只运行 RX，用串口确认其正常启动。
2. 单独运行 TX，确认 LD2450 帧率约为 10 帧/秒。
3. 用实际人体目标记录 x/y，再调整区域边界。
4. 穿过一面墙测试 ESP-NOW 丢包和唤醒延迟。
5. 确认 LED 亮灭逻辑后，再进入低功耗和外壳装配优化。

## 重要说明

当前 LD2450 解析按常见公开帧格式实现：

```text
AA FF 03 00 + 3 * 8 字节目标数据 + 55 CC
```

正式接线前应以手上 LD2450 模块的实际固件说明为准，并先确认波特率、帧头、坐标符号和距离字段。若模块使用不同固件版本，应只修改 `lib/Ld2450`，不要改动无线协议和 RX 端。

ESP-NOW 初版使用广播，不加密。不要将它用于门禁、消防、安防报警或其他安全关键系统。
