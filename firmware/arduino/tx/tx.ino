#include <Arduino.h>
#include "F:/DormRadar/firmware/lib/DormRadarConfig/src/BoardConfig.h"
#include "F:/DormRadar/firmware/lib/DormRadarProtocol/src/DormRadarProtocol.h"
#include "F:/DormRadar/firmware/lib/Ld2450/src/Ld2450.h"
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

namespace cfg = dorm_radar::config;
using dorm_radar::DetectionPacket;
using dorm_radar::Ld2450Parser;
using dorm_radar::RadarFrame;
using dorm_radar::RadarTarget;

namespace {

HardwareSerial RadarSerial(1);
Ld2450Parser radarParser;
RadarFrame latestFrame;
bool hasRadarFrame = false;
uint32_t lastRadarFrameMs = 0;
uint16_t packetSequence = 0;
uint32_t lastTelemetryMs = 0;
uint32_t lastDebugMs = 0;
bool espNowReady = false;

bool zoneCandidate = false;
uint32_t zoneCandidateSinceMs = 0;
uint32_t lastZoneSeenMs = 0;
bool alertActive = false;
uint32_t alertSinceMs = 0;

struct TargetSelection {
    bool anyTarget;
    bool anyInZone;
    uint8_t activeTargetCount;
    RadarTarget closest;
    RadarTarget closestInZone;
};

int32_t abs32(int32_t value) {
    return value < 0 ? -value : value;
}

bool saneTarget(const RadarTarget& target, uint16_t* distance) {
    if (!target.valid) {
        return false;
    }

    if (abs32(target.x_mm) > cfg::kCoordinateLimitMm ||
        abs32(target.y_mm) > cfg::kCoordinateLimitMm) {
        return false;
    }

    if (distance != NULL) {
        *distance = target.distance_mm;
    }
    return true;
}

bool targetInZone(const RadarTarget& target) {
    return target.valid &&
           target.x_mm >= cfg::kZoneMinXmm &&
           target.x_mm <= cfg::kZoneMaxXmm &&
           target.y_mm >= cfg::kZoneMinYmm &&
           target.y_mm <= cfg::kZoneMaxYmm &&
           target.distance_mm >= cfg::kZoneMinDistanceMm &&
           target.distance_mm <= cfg::kZoneMaxDistanceMm;
}

TargetSelection selectTargets(const RadarFrame& frame) {
    TargetSelection selection;
    memset(&selection, 0, sizeof(selection));

    uint16_t closestDistance = 0xFFFF;
    uint16_t closestZoneDistance = 0xFFFF;

    for (uint8_t i = 0; i < dorm_radar::kLd2450TargetCount; ++i) {
        uint16_t distance = 0;
        const RadarTarget& target = frame.targets[i];
        if (!saneTarget(target, &distance)) {
            continue;
        }

        ++selection.activeTargetCount;
        selection.anyTarget = true;

        if (distance < closestDistance) {
            closestDistance = distance;
            selection.closest = target;
        }

        if (targetInZone(target)) {
            selection.anyInZone = true;
            if (distance < closestZoneDistance) {
                closestZoneDistance = distance;
                selection.closestInZone = target;
            }
        }
    }

    return selection;
}

void updateAlert(uint32_t nowMs, const TargetSelection& selection,
                 bool radarHealthy) {
    if (!radarHealthy) {
        zoneCandidate = false;
        alertActive = false;
        alertSinceMs = 0;
        return;
    }

    if (selection.anyInZone) {
        lastZoneSeenMs = nowMs;
        if (!zoneCandidate) {
            zoneCandidate = true;
            zoneCandidateSinceMs = nowMs;
        }

        if (!alertActive &&
            nowMs - zoneCandidateSinceMs >= cfg::kTriggerDelayMs) {
            alertActive = true;
            alertSinceMs = nowMs;
        }
        return;
    }

    zoneCandidate = false;
    if (alertActive && nowMs - lastZoneSeenMs > cfg::kAlertHoldMs) {
        alertActive = false;
        alertSinceMs = 0;
    }
}

DetectionPacket makePacket(uint32_t nowMs, const TargetSelection& selection,
                           bool radarHealthy) {
    DetectionPacket packet;
    memset(&packet, 0, sizeof(packet));

    packet.sequence = packetSequence++;
    packet.uptime_ms = nowMs;
    packet.radar_frame_age_ms =
        hasRadarFrame ? nowMs - lastRadarFrameMs : 0xFFFFFFFFUL;
    packet.alert_ms = alertActive ? nowMs - alertSinceMs : 0;
    packet.target_count = selection.activeTargetCount;

    const RadarTarget& reported =
        selection.closestInZone.valid ? selection.closestInZone
                                      : selection.closest;
    packet.x_mm = reported.valid ? reported.x_mm : 0;
    packet.y_mm = reported.valid ? reported.y_mm : 0;
    packet.speed_cm_s = reported.valid ? reported.speed_cm_s : 0;
    packet.distance_mm = reported.valid ? reported.distance_mm : 0;

    if (selection.anyTarget) {
        packet.flags |= dorm_radar::kFlagTargetPresent;
    }
    if (selection.anyInZone) {
        packet.flags |= dorm_radar::kFlagTargetInZone;
    }
    if (alertActive) {
        packet.flags |= dorm_radar::kFlagAlert;
    }
    if (radarHealthy) {
        packet.flags |= dorm_radar::kFlagRadarHealthy;
    }

    dorm_radar::finalizeDetectionPacket(&packet);
    return packet;
}

void sendPacket(const DetectionPacket& packet) {
    if (!espNowReady) {
        return;
    }

    const uint8_t broadcastAddress[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    esp_now_send(broadcastAddress,
                 reinterpret_cast<const uint8_t*>(&packet),
                 sizeof(packet));
}

bool initEspNow() {
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    WiFi.setSleep(false);

    if (esp_wifi_set_ps(WIFI_PS_NONE) != ESP_OK) {
        return false;
    }
    if (esp_wifi_set_channel(cfg::kEspNowChannel,
                             WIFI_SECOND_CHAN_NONE) != ESP_OK) {
        return false;
    }
    if (esp_now_init() != ESP_OK) {
        return false;
    }

    esp_now_peer_info_t peer;
    memset(&peer, 0, sizeof(peer));
    const uint8_t broadcastAddress[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    memcpy(peer.peer_addr, broadcastAddress, sizeof(broadcastAddress));
    peer.channel = cfg::kEspNowChannel;
    peer.ifidx = WIFI_IF_STA;
    peer.encrypt = false;

    return esp_now_add_peer(&peer) == ESP_OK;
}

void processRadar(uint32_t nowMs) {
    while (RadarSerial.available() > 0) {
        const uint8_t byte = static_cast<uint8_t>(RadarSerial.read());
        RadarFrame frame;
        if (radarParser.feed(byte, nowMs, &frame)) {
            latestFrame = frame;
            hasRadarFrame = true;
            lastRadarFrameMs = nowMs;
        }
    }
}

void printStatus(uint32_t nowMs, const TargetSelection& selection,
                 bool radarHealthy) {
    if (nowMs - lastDebugMs < 2000) {
        return;
    }
    lastDebugMs = nowMs;

    Serial.printf(
        "[TX] link=%s radar=%s targets=%u zone=%u alert=%u x=%d y=%d d=%u\n",
        espNowReady ? "ready" : "fail",
        radarHealthy ? "ok" : "stale",
        selection.activeTargetCount,
        selection.anyInZone ? 1 : 0,
        alertActive ? 1 : 0,
        selection.closest.valid ? selection.closest.x_mm : 0,
        selection.closest.valid ? selection.closest.y_mm : 0,
        selection.closest.valid ? selection.closest.distance_mm : 0);
}

}  // namespace

void setup() {
    Serial.begin(cfg::kSerialBaud);
    delay(100);

    RadarSerial.begin(cfg::kRadarBaud, SERIAL_8N1, cfg::kRadarRxPin,
                      cfg::kRadarTxPin);

    espNowReady = initEspNow();
    Serial.printf("[TX] boot, esp-now=%s, channel=%u, radar=%u baud\n",
                  espNowReady ? "ok" : "failed", cfg::kEspNowChannel,
                  cfg::kRadarBaud);
}

void loop() {
    const uint32_t nowMs = millis();
    processRadar(nowMs);

    const bool radarHealthy =
        hasRadarFrame && nowMs - lastRadarFrameMs <= cfg::kRadarTimeoutMs;
    const TargetSelection selection = selectTargets(latestFrame);
    updateAlert(nowMs, selection, radarHealthy);

    static bool lastAlertState = false;
    const bool stateChanged = alertActive != lastAlertState;
    if (stateChanged || nowMs - lastTelemetryMs >= cfg::kTelemetryPeriodMs) {
        const DetectionPacket packet =
            makePacket(nowMs, selection, radarHealthy);
        sendPacket(packet);
        lastTelemetryMs = nowMs;
        lastAlertState = alertActive;
    }

    printStatus(nowMs, selection, radarHealthy);
    delay(1);
}





