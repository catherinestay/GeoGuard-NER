/*
 * GeoGuard-NER sensor node (ESP32 + MPU6050 + capacitive soil sensor + SX1276 LoRa)
 * Wakes on a timer, samples, sends one LoRa packet, then deep-sleeps to save power.
 * Local fail-safe: a hard tilt jump fires the siren even without gateway contact.
 *
 * Libraries: LoRa (Sandeep Mistry), MPU6050 (Electronic Cats)
 */
#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <MPU6050.h>
#include <math.h>

// ---------- configuration ----------
#define NODE_ID        "N01"
#define LORA_FREQ      865E6          // 865 MHz (India); use 868E6 / 915E6 elsewhere
#define SLEEP_SECONDS  300            // normal reporting interval
#define WATCH_SLEEP_S  60             // faster reporting when tilt is rising
#define TILT_ALARM_DEG 8.0            // hard local alarm threshold (calibrate in the field)
#define TILT_JUMP_DEG  2.0            // change since last wake that counts as "rising"

// ---------- pins ----------
#define LORA_CS   5
#define LORA_RST  14
#define LORA_DIO0 26
#define SOIL_PIN  34
#define SIREN_PIN 27

// soil sensor calibration: raw ADC in air (dry) and in water (wet) - measure your own probe
#define SOIL_DRY_RAW 3200
#define SOIL_WET_RAW 1400

MPU6050 mpu;
RTC_DATA_ATTR float lastTilt = 0;     // survives deep sleep
RTC_DATA_ATTR uint32_t seq = 0;

float readSoilMoisture() {
  long sum = 0;
  for (int i = 0; i < 16; i++) { sum += analogRead(SOIL_PIN); delay(5); }
  float raw = sum / 16.0;
  float m = (SOIL_DRY_RAW - raw) / (float)(SOIL_DRY_RAW - SOIL_WET_RAW);
  return constrain(m, 0.0f, 1.0f);    // 0 = dry, 1 = saturated
}

void readTiltAndVibration(float &tiltDeg, float &vibration) {
  // Average tilt over a short window; vibration = std-dev of acceleration magnitude (g).
  const int N = 50;
  float sumTilt = 0, sum = 0, sumSq = 0;
  for (int i = 0; i < N; i++) {
    int16_t ax, ay, az;
    mpu.getAcceleration(&ax, &ay, &az);
    float gx = ax / 16384.0f, gy = ay / 16384.0f, gz = az / 16384.0f;
    float mag = sqrtf(gx * gx + gy * gy + gz * gz);
    sumTilt += atan2f(sqrtf(gx * gx + gy * gy), gz) * 180.0f / PI;
    sum += mag; sumSq += mag * mag;
    delay(10);
  }
  tiltDeg = sumTilt / N;
  float mean = sum / N;
  vibration = sqrtf(fmaxf(sumSq / N - mean * mean, 0.0f));
}

void sirenOn(uint32_t ms) {
  digitalWrite(SIREN_PIN, HIGH);
  delay(ms);
  digitalWrite(SIREN_PIN, LOW);
}

void setup() {
  Serial.begin(115200);
  pinMode(SIREN_PIN, OUTPUT);
  digitalWrite(SIREN_PIN, LOW);
  analogReadResolution(12);

  Wire.begin(21, 22);
  mpu.initialize();
  bool imuOk = mpu.testConnection();

  float tilt = 0, vib = 0;
  if (imuOk) readTiltAndVibration(tilt, vib);
  float soil = readSoilMoisture();
  float dTilt = tilt - lastTilt;

  // ---- local fail-safe (works with no gateway/cloud) ----
  bool localAlarm = imuOk && (tilt >= TILT_ALARM_DEG);
  if (localAlarm) sirenOn(10000);

  // ---- LoRa uplink ----
  LoRa.setPins(LORA_CS, LORA_RST, LORA_DIO0);
  bool loraOk = LoRa.begin(LORA_FREQ);
  if (loraOk) {
    // CSV payload: id,seq,soil,tilt,vibration,imu_ok,alarm
    char payload[96];
    snprintf(payload, sizeof(payload), "%s,%lu,%.3f,%.2f,%.4f,%d,%d",
             NODE_ID, (unsigned long)seq, soil, tilt, vib, imuOk, localAlarm);
    LoRa.beginPacket();
    LoRa.print(payload);
    LoRa.endPacket();
    LoRa.sleep();
    Serial.println(payload);
  } else {
    Serial.println("LoRa init failed");
  }

  seq++;
  lastTilt = tilt;
  uint32_t sleepS = (dTilt > TILT_JUMP_DEG || localAlarm) ? WATCH_SLEEP_S : SLEEP_SECONDS;
  esp_sleep_enable_timer_wakeup((uint64_t)sleepS * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {}   // never reached: the node deep-sleeps at the end of setup()
