#include "Ld2450.h"

#include <string.h>

namespace dorm_radar {
namespace {

const uint8_t kHeader[4] = {0xAA, 0xFF, 0x03, 0x00};
const uint8_t kTail[2] = {0x55, 0xCC};

uint16_t readUInt16Le(const uint8_t* data) {
    return static_cast<uint16_t>(data[0]) |
           static_cast<uint16_t>(static_cast<uint16_t>(data[1]) << 8);
}

int16_t decodeSignedMagnitude(const uint8_t* data) {
    int16_t value = static_cast<int16_t>(
        (static_cast<uint16_t>(data[1]) & 0x7F) << 8 | data[0]);
    if ((data[1] & 0x80) == 0) {
        value = -value;
    }
    return value;
}

uint16_t integerSqrt(uint32_t value) {
    uint32_t result = 0;
    uint32_t bit = 1UL << 30;

    while (bit > value) {
        bit >>= 2;
    }
    while (bit != 0) {
        const uint32_t candidate = result + bit;
        result >>= 1;
        if (value >= candidate) {
            value -= candidate;
            result += bit;
        }
        bit >>= 2;
    }
    return static_cast<uint16_t>(result);
}

uint16_t computedDistance(const RadarTarget& target) {
    const int32_t x = target.x_mm;
    const int32_t y = target.y_mm;
    const uint32_t squared = static_cast<uint32_t>(x * x + y * y);
    return integerSqrt(squared);
}

bool findHeader(const uint8_t* data, size_t length, size_t start, size_t* found) {
    if (data == NULL || found == NULL || length < sizeof(kHeader)) {
        return false;
    }

    for (size_t i = start; i + sizeof(kHeader) <= length; ++i) {
        if (memcmp(data + i, kHeader, sizeof(kHeader)) == 0) {
            *found = i;
            return true;
        }
    }
    return false;
}

}  // namespace

Ld2450Parser::Ld2450Parser() : length_(0) {
    memset(buffer_, 0, sizeof(buffer_));
}

void Ld2450Parser::reset() {
    length_ = 0;
    memset(buffer_, 0, sizeof(buffer_));
}

bool Ld2450Parser::feed(uint8_t byte, uint32_t now_ms, RadarFrame* frame) {
    if (length_ < sizeof(kHeader)) {
        if (byte == kHeader[length_]) {
            buffer_[length_++] = byte;
        } else {
            length_ = 0;
            if (byte == kHeader[0]) {
                buffer_[0] = byte;
                length_ = 1;
            }
        }
        return false;
    }

    buffer_[length_++] = byte;
    if (length_ < kFrameSize) {
        return false;
    }

    const bool valid = memcmp(buffer_, kHeader, sizeof(kHeader)) == 0 &&
                       memcmp(buffer_ + kFrameSize - sizeof(kTail), kTail,
                              sizeof(kTail)) == 0;

    if (valid) {
        if (frame != NULL) {
            *frame = decodeFrame(buffer_, now_ms);
        }
        length_ = 0;
        return true;
    }

    resyncAfterInvalidFrame();
    return false;
}

void Ld2450Parser::resyncAfterInvalidFrame() {
    size_t next = 0;
    if (findHeader(buffer_, kFrameSize, 1, &next)) {
        const size_t remaining = kFrameSize - next;
        memmove(buffer_, buffer_ + next, remaining);
        length_ = remaining;
    } else {
        length_ = 0;
    }
}

RadarFrame Ld2450Parser::decodeFrame(const uint8_t* bytes,
                                     uint32_t now_ms) {
    RadarFrame frame;
    memset(&frame, 0, sizeof(frame));
    frame.timestamp_ms = now_ms;

    for (uint8_t index = 0; index < kLd2450TargetCount; ++index) {
        const uint8_t* raw = bytes + sizeof(kHeader) + index * 8;
        RadarTarget& target = frame.targets[index];

        target.x_mm = decodeSignedMagnitude(raw);
        target.y_mm = decodeSignedMagnitude(raw + 2);
        target.speed_cm_s = decodeSignedMagnitude(raw + 4);
        target.resolution_mm = readUInt16Le(raw + 6);
        target.distance_mm = 0;
        target.valid = target.x_mm != 0 || target.y_mm != 0;

        if (target.valid) {
            target.distance_mm = computedDistance(target);
            ++frame.active_target_count;
        }
    }

    return frame;
}

}  // namespace dorm_radar

