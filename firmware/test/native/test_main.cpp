#include <DormRadarProtocol.h>
#include <Ld2450.h>

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

namespace {

void putUInt16Le(uint8_t* data, uint16_t value) {
    data[0] = static_cast<uint8_t>(value & 0xFF);
    data[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
}

uint16_t encodeSignedMagnitude(int16_t value) {
    const uint16_t magnitude = static_cast<uint16_t>(
        value < 0 ? -static_cast<int32_t>(value) : value);
    uint16_t raw = magnitude & 0x7FFF;
    if (value >= 0) {
        raw |= 0x8000;
    }
    return raw;
}

void putTarget(uint8_t* frame, uint8_t index, int16_t x, int16_t y,
               int16_t speed, uint16_t resolution) {
    uint8_t* target = frame + 4 + index * 8;
    putUInt16Le(target, encodeSignedMagnitude(x));
    putUInt16Le(target + 2, encodeSignedMagnitude(y));
    putUInt16Le(target + 4, encodeSignedMagnitude(speed));
    putUInt16Le(target + 6, resolution);
}

void makeFrame(uint8_t* frame) {
    memset(frame, 0, 30);
    frame[0] = 0xAA;
    frame[1] = 0xFF;
    frame[2] = 0x03;
    frame[3] = 0x00;
    putTarget(frame, 0, 350, 1200, -25, 1250);
    frame[28] = 0x55;
    frame[29] = 0xCC;
}

void testLd2450Parser() {
    uint8_t frame[30];
    makeFrame(frame);

    dorm_radar::Ld2450Parser parser;
    dorm_radar::RadarFrame parsed;
    bool gotFrame = false;

    const uint8_t noisy[] = {0x00, 0x12, 0xAA};
    for (size_t i = 0; i < sizeof(noisy); ++i) {
        assert(!parser.feed(noisy[i], 10, &parsed));
    }
    for (size_t i = 0; i < sizeof(frame); ++i) {
        gotFrame = parser.feed(frame[i], 1234, &parsed);
    }

    assert(gotFrame);
    assert(parsed.timestamp_ms == 1234);
    assert(parsed.active_target_count == 1);
    assert(parsed.targets[0].valid);
    assert(parsed.targets[0].x_mm == 350);
    assert(parsed.targets[0].y_mm == 1200);
    assert(parsed.targets[0].speed_cm_s == -25);
    assert(parsed.targets[0].distance_mm == 1250);
    assert(parsed.targets[0].resolution_mm == 1250);
}

void testProtocol() {
    dorm_radar::DetectionPacket packet;
    memset(&packet, 0, sizeof(packet));
    packet.sequence = 7;
    packet.uptime_ms = 123456;
    packet.radar_frame_age_ms = 20;
    packet.x_mm = -123;
    packet.y_mm = 456;
    packet.speed_cm_s = 12;
    packet.distance_mm = 500;
    packet.target_count = 1;
    packet.flags = dorm_radar::kFlagTargetPresent |
                   dorm_radar::kFlagTargetInZone |
                   dorm_radar::kFlagAlert |
                   dorm_radar::kFlagRadarHealthy;

    dorm_radar::finalizeDetectionPacket(&packet);
    assert(dorm_radar::validateDetectionPacket(
        reinterpret_cast<const uint8_t*>(&packet), sizeof(packet)));

    packet.sequence = 8;
    assert(!dorm_radar::validateDetectionPacket(
        reinterpret_cast<const uint8_t*>(&packet), sizeof(packet)));
}

}  // namespace

int main() {
    testLd2450Parser();
    testProtocol();
    puts("dorm_radar native tests: OK");
    return 0;
}
