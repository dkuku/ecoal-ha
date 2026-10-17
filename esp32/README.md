# eCoal ESP32 Hardware Bridge & Standalone Web Server

Ten moduł pozwala na podłączenie mikrokontrolera **ESP32** (np. ESP32-C3 lub ESP32-S3) bezpośrednio do sterownika kotła eCoal przez port szeregowy UART/RS-232.

Dzięki temu ten sam nowoczesny interfejs WWW (Single Page Application z `custom_components/ecoal/www/`) jest serwowany bezpośrednio z pamięci flash mikrokontrolera (LittleFS), umożliwiając sterowanie piecem z telefonu lub przeglądarki nawet przy wyłączonym serwerze Home Assistant.

---

## 1. Wybór Płytki: ESP32-C3 vs ESP32-S3

| Cecha | ESP32-C3 (Rekomendowany budżet) | ESP32-S3 (Rekomendowany dla zaawansowanych) |
|---|---|---|
| **Rdzenie** | 1x RISC-V 160 MHz | 2x Xtensa LX7 240 MHz |
| **Pamięć Flash** | 4 MB Flash | 8 MB / 16 MB Flash + 2/8 MB PSRAM |
| **Pamięć LittleFS** | ok. 1.5 - 2 MB (więcej niż potrzeba na UI) | 4 - 8 MB (miejsce na długą historię i wykresy) |
| **Cena** | ok. 12 - 18 PLN | ok. 25 - 40 PLN |
| **Dodatkowe opcje** | Kompaktowy rozmiar, mały pobór prądu | Obsługa zewnętrznych wyświetlaczy dotykowych SPI/RGB |

**Werdykt:**
* **ESP32-C3** jest w zupełności wystarczający do obsługi mostka UART, serwera WWW i interfejsu SPA.
* **ESP32-S3** warto wybrać, jeśli planujesz w przyszłości podpiąć fizyczny ekran LCD/OLED przy kotle lub logować dane historyczne do pamięci flash.

---

## 2. Schemat Podłączenia (Hardware Wiring)

> [!WARNING]
> Sterownik eCoal posiada na płycie głównej standardowe poziomy napięć RS-232 ($\pm 12\text{V}$) na zewnętrznym gnieździe lub poziomy TTL (5V/3.3V) na złączu wewnętrznym. **Nigdy nie podłączaj linii $\pm 12\text{V}$ bezpośrednio do pinów GPIO ESP32 (3.3V), gdyż trwale uszkodzi to procesor!** Użyj konwertera **MAX3232**.

### Połączenie przez konwerter MAX3232 (do portu RS-232 kotła):
```
[ Sterownik eCoal DB9 ]            [ Moduł MAX3232 ]           [ ESP32-C3 / S3 ]
  Pin 2 (RxD) -------------> T1OUT / R1IN
  Pin 3 (TxD) <------------- R1OUT / T1IN
  Pin 5 (GND) -------------> GND -----------------------------> GND
                             VCC -----------------------------> 3.3V lub 5V
                             TTL RxD <------------------------- GPIO 21 (TxD1)
                             TTL TxD -------------------------> GPIO 20 (RxD1)
```

* **Domyślne parametry transmisji UART eCoal:** `19200 baud`, `8 bitów danych`, `brak parzystości (None)`, `1 bit stopu` (19200 8N1).

---

## 3. Struktura Pamięci Flash (LittleFS)

Pliki interfejsu SPA z katalogu `custom_components/ecoal/www/` są wgrywane 1:1 do partycji LittleFS ESP32:
```
data/
├── index.html        (Główny pulpit SPA ze schematem hydraulicznym SVG)
├── style.css         (Responsywne style Dark Mode)
├── app.js            (Główny kontroler aplikacji JS)
├── protocol.js       (Silnik binarny eCoal, CRC8, ramki statusu)
├── adapter.js        (Wymienne adaptery transportowe)
└── params.js         (Baza 122 parametrów sterownika)
```

Aby skopiować najnowszy kod interfejsu do folderu ESP32, uruchom skrypt:
```bash
./esp32/sync_www.sh
```

---

## 4. Wgrywanie Oprogramowania (Arduino IDE / PlatformIO)

1. Otwórz projekt [`esp32/ecoal_bridge.ino`](file:///home/kuku/Projects/ogniwo-furnace-ha/esp32/ecoal_bridge.ino) w Arduino IDE lub PlatformIO.
2. W konfiguracji płytki wybierz:
   * **Partition Scheme:** `Minimal SPIFFS (1.9MB APP with OTA/190KB SPIFFS)` lub `Default 4MB with spiffs/littlefs (1.2MB App / 1.5MB LittleFS)`.
3. Skonfiguruj nazwę sieci Wi-Fi i hasło w kodzie (lub użyj automatycznego trybu AP).
4. Wgraj szkic do mikrokontrolera (`Upload`).
5. Wgraj pliki interfejsu do LittleFS za pomocą wtyczki **ESP32 LittleFS Data Upload**.
6. Po uruchomieniu ESP32 wyświetli adres IP w monitorze portu szeregowego (np. `http://192.168.1.150`).
7. Wejdź na ten adres w przeglądarce telefonu lub komputera – pełny panel kotła z animowanym schematem uruchomi się natychmiast!

---

## 5. Jak to działa pod maską?

* Przeglądarka ładuje pliki statyczne HTML/JS/CSS z pamięci LittleFS ESP32.
* Kontroler JS (`app.js`) w trybie autonomicznym wysyła zapytania `GET /?com=<HEX>` bezpośrednio do serwera HTTP na ESP32.
* ESP32 odbiera ciąg heksadecymalny, zamienia go na bajty binarne i wysyła przez sprzętowy port UART (`Serial1`) do procesora kotła.
* ESP32 odbiera odpowiedź kotła, sprawdza sumę kontrolną CRC8 i odsyła do przeglądarki format `[2, 1, 6, ...]`.
* Dzięki temu ten sam kod działa zamiennie w **Home Assistant**, na **ESP32**, przez **Web Serial API** lub w **Symulatorze Mock**.
