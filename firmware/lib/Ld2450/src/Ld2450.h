#pragma once

#include <stddef.h>
#include <stdint.h>

namespace dorm_radar {

constexpr uint8_t kLd2450TargetCount = 3;

struct RadarTarget {
    bool valid;
    int16_t x_mm;
    int16_t y_mm;
    int16_t speed_cm_s;
    uint16_t distance_mm;
    uint16_t resolution_mm;
};

struct RadarFrame {
    uint32_t timestamp_ms;
    uint8_t active_target_count;
    RadarTarget targets[kLd2450TargetCount];
};

class Ld2450Parser {
public:
    enum { kFrameSize = 30 };

    Ld2450Parser();

    void reset();

    // Feeds one UART byte. Returns true when a complete valid frame was parsed.
    bool feed(uint8_t byte, uint32_t now_ms, RadarFrame* frame);

private:
    void resyncAfterInvalidFrame();
    static RadarFrame decodeFrame(const uint8_t* bytes, uint32_t now_ms);

    uint8_t buffer_[kFrameSize];
    size_t length_;
};

}  // namespace dorm_radar
