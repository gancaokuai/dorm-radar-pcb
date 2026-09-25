#include <Arduino.h>
#include "F:/DormRadar/firmware/lib/DormRadarConfig/src/BoardConfig.h"
#include "F:/DormRadar/firmware/lib/DormRadarProtocol/src/DormRadarProtocol.h"
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>

namespace cfg = dorm_radar::config;
using dorm_radar::DetectionPacket;

namespace {

QueueHandle_t packetQueue = NULL;
DetectionPacket lastPacket;
bool hasPacket = false;
uint32_t lastPacketMs = 0;
uint32_t lastDebugMs = 0;
volatile uint32_t validPackets = 0;
volatile uint32_t rejectedPackets = 0;
volatile uint32_t droppedPackets = 0;
bool espNowReady = false;

void writeLed(bool on) {
    const uint8_t level =
        cfg::kLedActiveHigh ? (on ? HIGH : LOW) : (on ? LOW : HIGH);
    digitalWrite(cfg::kStatusLedPin, level);
}

#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
void onEspNowRecv(const esp_now_recv_info_t* info, const uint8_t* data,
                  int length) {
    (void)info;
#else
void onEspNowRecv(const uint8_t* macAddress, const uint8_t* data,
                  int length) {
    (void)macAddress;
#endif
    if (!dorm_radar::validateDetectionPacket(data,
                                             static_cast<size_t>(length))) {
        ++rejectedPackets;
        return;
    }

    DetectionPacket packet;
    memcpy(&packet, data, sizeof(packet));
    if (xQueueSend(packetQueue, &packet, 0) != pdTRUE) {
        ++droppedPackets;
        return;
    }
    ++validPackets;
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

    if (esp_now_add_peer(&peer) != ESP_OK) {
        return false;
    }
    return esp_now_register_recv_cb(onEspNowRecv) == ESP_OK;
}

void processQueue(uint32_t nowMs) {
    DetectionPacket packet;
    while (packetQueue != NULL &&
           xQueueReceive(packetQueue, &packet, 0) == pdTRUE) {
        lastPacket = packet;
        lastPacketMs = nowMs;
        hasPacket = true;
    }
}

void updateLed(uint32_t nowMs) {
    const bool linkHealthy =
        hasPacket && nowMs - lastPacketMs <= cfg::kLinkTimeoutMs;

    if (!linkHealthy) {
        writeLed((nowMs % 1000) < 100);
        return;
    }

    const bool alert =
        (lastPacket.flags & dorm_radar::kFlagAlert) != 0;
    writeLed(alert);
}

void printStatus(uint32_t nowMs) {
    if (nowMs - lastDebugMs < 2000) {
        return;
    }
    lastDebugMs = nowMs;

    const bool linkHealthy =
        hasPacket && nowMs - lastPacketMs <= cfg::kLinkTimeoutMs;
    const bool alert =
        linkHealthy && (lastPacket.flags & dorm_radar::kFlagAlert) != 0;

    Serial.printf(
        "[RX] link=%s rssi=local valid=%u rejected=%u dropped=%u seq=%u "
        "alert=%u radar=%u age=%u x=%d y=%d d=%u\n",
        linkHealthy ? "ok" : "lost",
        static_cast<unsigned>(validPackets),
        static_cast<unsigned>(rejectedPackets),
        static_cast<unsigned>(droppedPackets),
        static_cast<unsigned>(lastPacket.sequence),
        alert ? 1 : 0,
        (lastPacket.flags & dorm_radar::kFlagRadarHealthy) ? 1 : 0,
        static_cast<unsigned>(lastPacket.radar_frame_age_ms),
        lastPacket.x_mm,
        lastPacket.y_mm,
        lastPacket.distance_mm);
}

}  // namespace

void setup() {
    Serial.begin(cfg::kSerialBaud);
    delay(100);

    digitalWrite(cfg::kStatusLedPin, HIGH);
    pinMode(cfg::kStatusLedPin, OUTPUT);
    writeLed(false);

    packetQueue = xQueueCreate(8, sizeof(DetectionPacket));
    espNowReady = packetQueue != NULL && initEspNow();

    Serial.printf("[RX] boot, esp-now=%s, channel=%u, queue=%s\n",
                  espNowReady ? "ok" : "failed", cfg::kEspNowChannel,
                  packetQueue != NULL ? "ok" : "failed");
}

void loop() {
    const uint32_t nowMs = millis();
    processQueue(nowMs);
    updateLed(nowMs);
    printStatus(nowMs);
    delay(1);
}




