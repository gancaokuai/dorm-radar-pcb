#pragma once

#include <stddef.h>
#include <stdint.h>

namespace dorm_radar {

constexpr uint16_t kProtocolMagic = 0xD042;
constexpr uint8_t kProtocolVersion = 1;
constexpr uint8_t kPacketTypeDetection = 1;

enum PacketFlag : uint8_t {
    kFlagTargetPresent = 1 << 0,
    kFlagTargetInZone = 1 << 1,
    kFlagAlert = 1 << 2,
    kFlagRadarHealthy = 1 << 3,
};

struct __attribute__((packed)) DetectionPacket {
    uint16_t magic;
    uint8_t version;
    uint8_t type;
    uint16_t sequence;
    uint32_t uptime_ms;
    uint32_t radar_frame_age_ms;
    uint16_t alert_ms;
    int16_t x_mm;
    int16_t y_mm;
    int16_t speed_cm_s;
    uint16_t distance_mm;
    uint8_t target_count;
    uint8_t flags;
    uint8_t crc8;
};

static_assert(sizeof(DetectionPacket) == 27, "DetectionPacket layout changed");

uint8_t crc8(const uint8_t* data, size_t length);

void finalizeDetectionPacket(DetectionPacket* packet);

bool validateDetectionPacket(const uint8_t* data, size_t length);

bool validateDetectionPacket(const DetectionPacket& packet);

}  // namespace dorm_radar

