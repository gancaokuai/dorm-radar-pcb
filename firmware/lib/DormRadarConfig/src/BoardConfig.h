#pragma once

#include <stdint.h>

namespace dorm_radar {
namespace config {

// ESP32-C3-WROOM-02 pin mapping from the current KiCad schematic.
constexpr int kRadarRxPin = 5;   // ESP RX <- LD2450 TX
constexpr int kRadarTxPin = 4;   // ESP TX -> LD2450 RX
constexpr int kStatusLedPin = 7;
constexpr bool kLedActiveHigh = false;

constexpr uint32_t kSerialBaud = 115200;
constexpr uint32_t kRadarBaud = 256000;
constexpr uint8_t kEspNowChannel = 1;

constexpr uint32_t kRadarTimeoutMs = 1500;
constexpr uint32_t kLinkTimeoutMs = 1800;
constexpr uint32_t kTelemetryPeriodMs = 500;
constexpr uint32_t kTriggerDelayMs = 0;
constexpr uint32_t kAlertHoldMs = 1500;

// LD2450 coordinates are millimetres in front of the radar.
// Requested wall-mounted area: 8 m wide (4 m left + 4 m right) x 2.8 m deep.
constexpr int32_t kZoneMinXmm = -4000;
constexpr int32_t kZoneMaxXmm = 4000;
constexpr int32_t kZoneMinYmm = 0;
constexpr int32_t kZoneMaxYmm = 2800;
constexpr uint16_t kZoneMinDistanceMm = 100;
constexpr uint16_t kZoneMaxDistanceMm = 5000;

// Reject obviously corrupt coordinates before using them in telemetry.
constexpr int32_t kCoordinateLimitMm = 6000;

}  // namespace config
}  // namespace dorm_radar
