# Dorm Radar PCB

ESP32-C3 based local motion-alert PCB project. The system uses an LD2450 radar on the transmitter board and a local LED on the receiver board. Communication uses ESP-NOW. No camera, microphone, cloud service, or charging circuit is included.

## Boards

- TX board: 70 mm x 42 mm, LD2450 interface and ESP-NOW transmitter
- RX board: 68 mm x 42 mm, ESP-NOW receiver and LED indicator

## Hardware

- ESP32-C3-WROOM-02
- LD2450 24 GHz radar module
- MT3608 5 V boost converter
- AP2112K-3.3 regulator
- External protected 1S 18650 battery pack
- Two-layer PCB with bottom ground plane

## Repository Layout

```text
hardware/kicad/DormRadar/
  DormRadar.kicad_pro
  DormRadar.kicad_sch
  generate_schematic.py
  generate_pcbs.py
  release/
    BOM_common.csv
    BOM_TX.csv
    BOM_RX.csv
    TX/
      DormRadar_TX.kicad_pcb
      DRC.txt
      gerber/
      drill/
      position/
    RX/
      DormRadar_RX.kicad_pcb
      DRC.txt
      gerber/
      drill/
      position/
```

## Firmware

The initial ESP32-C3 firmware MVP is in `firmware/`.

- TX reads the LD2450 radar and sends detection state over ESP-NOW.
- RX validates the packet and drives the local LED.
- The build script uses `F:\DormRadar` as an ASCII junction because the ESP32 GCC toolchain cannot resolve the Chinese project path.
- Build with `F:\防宿管雷达\firmware\build.ps1 all`.

See `firmware/README.md` for pin mapping, thresholds, and first-board bring-up steps.
## Verification

- TX: 0 unconnected pads, 0 electrical errors
- RX: 0 unconnected pads, 0 electrical errors
- Remaining DRC items are silkscreen-only warnings caused by the ESP32 antenna overhang and local reference text placement.
- Freerouting 2.4.1 was used in single-thread mode, then all tracks below 0.20 mm were normalized to at least 0.20 mm.

## Notes

Use this design only in compliance with local rules and do not modify fire, access-control, or safety equipment. The radar should have direct line of sight to the intended detection zone.

## Licensing

This is a multi-licensed project. Firmware is under Apache-2.0, hardware design files are under CERN-OHL-W-2.0, and documentation is under CC BY-SA 4.0. See LICENSING.md and LICENSES/ for details.
