防宿管雷达 PCB 发布说明
日期: 2026-09-12
KiCad: 10.0.6

板卡:
- TX: 70 mm x 42 mm, 包含 LD2450 接口和 ESP-NOW 发射端
- RX: 68 mm x 42 mm, 仅包含 ESP-NOW 接收端和 LED

设计要点:
- ESP32-C3-WROOM-02 天线区悬出板边，减少 PCB 尺寸并保持天线净空
- 1S 18650 电池输入，无充电功能
- MT3608 升压到 5V
- AP2112K-3.3 给 ESP32 供电
- 双层板，底层 GND 铺铜
- Freerouting 2.4.1 自动布线，单线程模式
- 最终 DRC: 0 个未连接焊盘，0 个电气错误，剩余仅为丝印边缘提示

生产文件:
- TX/gerber, TX/drill, TX/position
- RX/gerber, RX/drill, RX/position
- BOM_common.csv
- TX/DormRadar_TX.kicad_pcb
- RX/DormRadar_RX.kicad_pcb
