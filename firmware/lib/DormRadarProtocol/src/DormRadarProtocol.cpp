#include "DormRadarProtocol.h"

#include <string.h>

namespace dorm_radar {

uint8_t crc8(const uint8_t* data, size_t length) {
    uint8_t crc = 0x00;
    if (data == NULL) {
        return crc;
    }

    for (size_t i = 0; i < length; ++i) {
        crc ^= data[i];
        for (uint8_t bit = 0; bit < 8; ++bit) {
            crc = (crc & 0x80) ? static_cast<uint8_t>((crc << 1) ^ 0x07)
                               : static_cast<uint8_t>(crc << 1);
        }
    }
    return crc;
}

void finalizeDetectionPacket(DetectionPacket* packet) {
    if (packet == NULL) {
        return;
    }

    packet->magic = kProtocolMagic;
    packet->version = kProtocolVersion;
    packet->type = kPacketTypeDetection;
    packet->crc8 = crc8(reinterpret_cast<const uint8_t*>(packet),
                        sizeof(DetectionPacket) - 1);
}

bool validateDetectionPacket(const uint8_t* data, size_t length) {
    if (data == NULL || length != sizeof(DetectionPacket)) {
        return false;
    }

    DetectionPacket packet;
    memcpy(&packet, data, sizeof(packet));
    return validateDetectionPacket(packet);
}

bool validateDetectionPacket(const DetectionPacket& packet) {
    if (packet.magic != kProtocolMagic ||
        packet.version != kProtocolVersion ||
        packet.type != kPacketTypeDetection) {
        return false;
    }

    const uint8_t expected = crc8(reinterpret_cast<const uint8_t*>(&packet),
                                  sizeof(DetectionPacket) - 1);
    return expected == packet.crc8;
}

}  // namespace dorm_radar

