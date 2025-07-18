#include <ESP8266WiFi.h>
#include <FirebaseESP8266.h>
#include <MFRC522.h>
#include <SPI.h>
#include <NTPClient.h>
#include <WiFiUdp.h>

// --- Koneksi WiFi & Firebase ---
#define WIFI_SSID "Yuli"
#define WIFI_PASSWORD "Yuli3324@1"
#define FIREBASE_HOST "https://esp8226-sp-default-rtdb.asia-southeast1.firebasedatabase.app"
#define FIREBASE_API_KEY "AIzaSyBUAkLsqXNkZHctk-lfklxZKPSAqub76oo"
#define USER_EMAIL "riskitrest@gmail.com"
#define USER_PASSWORD "dryflower0"

// --- RFID ---
#define RST_PIN D2
#define SS_PIN_MASUK D1     // GPIO5
#define SS_PIN_KELUAR D8    // GPIO15

MFRC522 rfidMasuk(SS_PIN_MASUK, RST_PIN);
MFRC522 rfidKeluar(SS_PIN_KELUAR, RST_PIN);

// --- Firebase object ---
FirebaseData firebaseData;
FirebaseAuth auth;
FirebaseConfig config;

// --- NTP Waktu ---
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", 7 * 3600, 60000); // GMT+7

// --- Debounce ---
String lastUIDMasuk = "", lastUIDKeluar = "";
unsigned long lastReadMasuk = 0, lastReadKeluar = 0;
const unsigned long debounceDelay = 1000;

// --- Setup ---
void setup() {
  Serial.begin(9600);
  SPI.begin();

  rfidMasuk.PCD_Init();
  rfidKeluar.PCD_Init();

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");

  timeClient.begin();

  // Init Firebase
  config.api_key = FIREBASE_API_KEY;
  config.database_url = FIREBASE_HOST;
  auth.user.email = USER_EMAIL;
  auth.user.password = USER_PASSWORD;
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);

  Serial.println("RC Masuk & Keluar Siap...");
}

// --- Fungsi: Ambil waktu sekarang dalam format string ---
String getWaktu() {
  timeClient.update();
  time_t rawTime = timeClient.getEpochTime();
  struct tm *timeInfo = localtime(&rawTime);
  char timeBuffer[30];
  sprintf(timeBuffer, "%04d-%02d-%02d %02d:%02d:%02d",
          timeInfo->tm_year + 1900, timeInfo->tm_mon + 1, timeInfo->tm_mday,
          timeInfo->tm_hour, timeInfo->tm_min, timeInfo->tm_sec);
  return String(timeBuffer);
}

// --- Fungsi: Baca UID ---
String bacaUID(MFRC522 &rfid) {
  String uidString = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    uidString += String(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
    uidString += String(rfid.uid.uidByte[i], HEX);
  }
  uidString.toUpperCase();
  return uidString;
}

// --- Loop utama ---
void loop() {
  timeClient.update();

  // ------------------ RC MASUK ------------------
  digitalWrite(SS_PIN_KELUAR, HIGH); // Matikan reader keluar
  digitalWrite(SS_PIN_MASUK, LOW);   // Aktifkan reader masuk

  if (rfidMasuk.PICC_IsNewCardPresent() && rfidMasuk.PICC_ReadCardSerial()) {
    String uid = bacaUID(rfidMasuk);

    if (uid != lastUIDMasuk || millis() - lastReadMasuk > debounceDelay) {
      lastUIDMasuk = uid;
      lastReadMasuk = millis();

      String waktuMasuk = getWaktu();
      Serial.println("[MASUK] UID: " + uid + " | Waktu: " + waktuMasuk);

      // Kirim ke Firebase
      Firebase.setString(firebaseData, "/DataSementara/" + uid + "/idRfid", uid);
      Firebase.setString(firebaseData, "/DataSementara/" + uid + "/waktuMasuk", waktuMasuk);
      Firebase.setString(firebaseData, "/DataTerakhir/idRfid", uid);
      Firebase.setString(firebaseData, "/DataTerakhir/Waktu", waktuMasuk);
    }

    rfidMasuk.PICC_HaltA();
  }

  // ------------------ RC KELUAR ------------------
  digitalWrite(SS_PIN_MASUK, HIGH);  // Matikan reader masuk
  digitalWrite(SS_PIN_KELUAR, LOW);  // Aktifkan reader keluar

  if (rfidKeluar.PICC_IsNewCardPresent() && rfidKeluar.PICC_ReadCardSerial()) {
    String uid = bacaUID(rfidKeluar);

    if (uid != lastUIDKeluar || millis() - lastReadKeluar > debounceDelay) {
      lastUIDKeluar = uid;
      lastReadKeluar = millis();

      String waktuKeluar = getWaktu();
      Serial.println("[KELUAR] UID: " + uid + " | Waktu: " + waktuKeluar);

      // Ambil data sementara
      if (Firebase.getJSON(firebaseData, "/DataSementara/" + uid)) {
        FirebaseJson &json = firebaseData.jsonObject();
        FirebaseJsonData jsonData;
        json.get(jsonData, "waktuMasuk");
        String waktuMasuk = jsonData.stringValue;

        FirebaseJson logData;
        logData.set("idRfid", uid);
        logData.set("waktuMasuk", waktuMasuk);
        logData.set("waktuKeluar", waktuKeluar);

        if (Firebase.pushJSON(firebaseData, "/Data", logData)) {
          Serial.println("Log masuk-keluar berhasil disimpan.");
          Firebase.deleteNode(firebaseData, "/DataSementara/" + uid);
        } else {
          Serial.println("Gagal push log: " + firebaseData.errorReason());
        }

        Firebase.setString(firebaseData, "/DataTerakhir/idRfid", uid);
        Firebase.setString(firebaseData, "/DataTerakhir/Waktu", waktuKeluar);
      } else {
        Serial.println("Data masuk tidak ditemukan untuk UID: " + uid);
      }
    }

    rfidKeluar.PICC_HaltA();
  }

  delay(10); // ✅ Taruh delay kecil di akhir loop
}

