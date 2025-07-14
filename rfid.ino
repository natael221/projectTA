#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN D1      // Reset pin
#define SS_PIN  D2      // SDA (SS)

MFRC522 rfid(SS_PIN, RST_PIN); // Instance RFID

void setup() {
  Serial.begin(9600);
  SPI.begin();           // Mulai SPI
  rfid.PCD_Init();       // Inisialisasi RFID
  Serial.println("Scan kartu RFID Anda...");
}

void loop() {
  // Jika tidak ada kartu, keluar
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  // Cetak UID
  Serial.print("UID: ");
  for (byte i = 0; i < rfid.uid.size; i++) {
    Serial.print(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
    Serial.print(rfid.uid.uidByte[i], HEX);
  }
  Serial.println();

  // Cetak angka 1 sebagai tanda kartu terdeteksi
  Serial.println("1");

  // Tunggu hingga kartu diangkat
  delay(1000);
  rfid.PICC_HaltA();       // Stop komunikasi
  rfid.PCD_StopCrypto1();  // Stop enkripsi
}
