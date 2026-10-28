# Pamięć Konfiguracji Kotła i Dziennik Eksperymentu Spalania

Plik pamięci trwałej do analizy porównawczej po kilku dniach pracy kotła.  
**Data utworzenia:** 2026-10-23 06:42 CEST  
**Cel:** Weryfikacja dobowego zużycia węgla, zachowania podtrzymania i zużycia przekaźnika po likwidacji pułapki termicznej CWU.

---

## 1. Dane Identyfikacyjne i Dostępowe Sprzętu

- **Kocioł:** Ogniwo Eko Plus (palnik retortowy z podawaniem ślimakowym od dołu)
- **Sterownik:** eCoal v0.2.9.16
- **Adres IP sterownika:** `192.168.2.111` (port 80 HTTP)
- **Autoryzacja HTTP:** Basic Auth (`admin` / `admin`)
- **Protokół eCoal:**
  - Status kotła: `GET http://192.168.2.111/?com=02010006000000006103`
  - Zmiana parametru: `CMD 0x02` (2 bajty Little-Endian)
- **Home Assistant:** Host `root@192.168.1.245`
- **Baza Danych Historii:** PostgreSQL na `192.168.30.104:5432` (baza `homeassistant`)
- **Ograniczenie firmware:** Zakres parametrów wyłącznie `0 .. 95`. Rejestry $\ge 96$ zwracają NAK `0x15`.

---

## 2. Kalibracja Podajnika Ślimakowego

- **Wynik kalibracji z 22.10.2026:**
  - Zmierzony czas pracy ślimaka: **136,4 minuty** (8184 sekundy)
  - Wsypany opał (2 worki): **50,0 kg**
  - Stała wydatku ślimaka:
    $$\mathbf{Wydatek = 0,3666\text{ kg/min}} \quad (22,0\text{ kg/h})$$
  - Formuła obliczania spalonego węgla:
    $$\text{Spalony węgiel [kg]} = \text{czas pracy ślimaka [minuty]} \times 0,3666$$

---

## 3. Punkt Bazowy Eksperymentu (Baseline)

### Pojemność zasobnika:
- **Pojemność całkowita zasobnika:** **150 kg** (`number.garaz_ecoal_pojemnosc_zasobnika = 150.0 kg`).
- 22.10.2026 o 17:11 CEST dosypano 2 worki (50 kg) **do pełna** (zasobnik był zapełniony w 100% = 150 kg).
- Oznacza to, że wcześniejszy czas pracy ślimaka 136,4 minuty odpowiadał wypaleniu dokładnie 50 kg (ubytek od pełnego do poziomu na 2 worki).

### Oś czasu i bilans paliwa:
1. **2026-10-22 17:11 CEST (15:11 UTC):**
   - Dosypano **50,0 kg** (2 worki) uzupełniając zasobnik do **150 kg (100% full)**.
   - Zresetowano licznik czasu pracy podajnika do zera (`button.garaz_ecoal_zasypano_zasobnik_100`).
2. **2026-10-22 17:11 do 2026-10-23 06:30 CEST (pierwsze 13,5 h):**
   - Kocioł pracował w stanie uwięzienia na grzaniu CWU (Zadana CO = 53°C, Zadana CWU = 53°C).
   - Przepracował: **3255 sekund** (**54,25 minuty**).
   - Zużył w tym okresie: **19,88 kg** węgla.
   - W zasobniku pozostało na start nowego trybu: **150 kg - 19,88 kg = ~130,1 kg węgla (~87-90%)**.
3. **2026-10-23 06:30 CEST – Wprowadzenie korekty parametrów:**
   - Obniżono zadaną CWU z 53°C do **50°C** (`PARAM 17 -> 50`).
   - Pułapka CWU usunięta: pompa CWU przestała pracować w pętli.
   - W ciągu dnia kocioł grzał jednak dom (pompa CO ciągła), spędzając 90% czasu w grzaniu (1,20 kg/h).
4. **2026-10-23 21:48 CEST – Zatrzymanie i wygaszenie kotła na czas nieobecności:**
   - Wyłączono tryb automatyczny (`CMD_AUTO_OFF` -> `PARAM 51 = 0`, `switch.ecoal_auto_mode = off`).
   - Dmuchawa: OFF, Ślimak: OFF. Kocioł bezpiecznie stygnie (zużycie węgla: 0 kg).
   - Stan licznika w momencie wygaszenia: **6257 sekund** (**104,28 minuty**).
   - Łączne zużycie węgla od pełnego zasypu: **38,23 kg**.
   - Pozostało w zasobniku: **~111,8 kg (82%)**.

---

## 4. Parametry Bieżące po Zmianie (2026-10-23 06:40 CEST)

| Parametr | Rejestr | Wartość | Uwagi |
| :--- | :--- | :--- | :--- |
| **Zadana temp. kotła CO** | `PARAM 40` | **53°C** | Stabilna praca jesienna |
| **Zadana temp. bojlera CWU** | `PARAM 17` | **50°C** | Zapewnia bezpieczną deltę $\Delta T = 3\text{--}7^\circ\text{C}$ |
| **Czas postoju w podtrzymaniu** | `PARAM 13` | **45 min** | Zabezpiecza przekaźnik przed częstym klikaniem |
| **Czas pracy w podtrzymaniu** | `PARAM 10` | domyślny (~15s) | Podtrzymanie żaru |
| **Korekta dmuchawy** | `PARAM 94` | `0%` | Prawidłowy nadmuch |
| **Stan wyjść** | - | Pompa CWU: OFF, Pompa CO: ON, Dmuchawa: 4%, Ślimak: OFF | Kocioł cichy, brak ciągłego klikania |

---

## 5. Procedura Analizy za Parę Dni (Checklist do Wykonania)

Gdy wrócimy do tematu za parę dni, należy wykonać następujące kroki:

1. **Odczyt stanu licznika ślimaka:**
   ```bash
   python3 -c "
   import urllib.request, base64
   req = urllib.request.Request('http://192.168.2.111/?com=02010006000000006103')
   req.add_header('Authorization', 'Basic ' + base64.b64encode(b'admin:admin').decode())
   raw = [int(x.strip()) for x in urllib.request.urlopen(req).read().decode().split('[')[1].split(']')[0].split(',')]
   feeder_s = raw[64] | (raw[65] << 8) | (raw[66] << 16) | (raw[67] << 24)
   print(f'Licznik podajnika: {feeder_s} s ({feeder_s/60:.2f} min)')
   "
   ```

2. **Obliczenie nowego spalania netto:**
   - Czas pracy podajnika od 23.10 06:30 = $\text{Licznik aktualny [min]} - 54,25\text{ min}$
   - Zużyty węgiel w nowym trybie = $(\text{Licznik aktualny} - 54,25) \times 0,3666\text{ kg}$
   - Liczba godzin od wprowadzenia zmiany: $H = \text{Aktualna data} - (2026\text{-}10\text{-}23\ 06:30)$
   - Nowe średnie tempo spalania = $\frac{\text{Zużyty węgiel netto}}{H / 24}\text{ [kg/dobę]}$
   - **Oczekiwany rezultat:** Spadek zużycia z wcześniejszych **31,4 kg/dobę** do poziomu typowego dla jesieni: **12–16 kg/dobę**.

3. **Weryfikacja ilości węgla w zasobniku:**
   - Całkowite zużycie od zasypu = $\text{Licznik całkowity [min]} \times 0,3666\text{ kg}$.
   - Węgiel pozostały w zasobniku = $150\text{ kg} - (\text{Licznik całkowity [min]} \times 0,3666\text{ kg})$.
   - Cały zasobnik (150 kg) wystarczy na ok. 9–11 dni pracy.
   - Gdy licznik całkowity osiągnie **~136 minut** (czyli za ok. 3–4 dni), z zasobnika ubędzie kolejne 50 kg węgla i znów wejdą dokładnie 2 worki!

4. **Weryfikacja pracy przekaźnika:**
   - Sprawdzenie, czy kocioł nie wracał do pętli ciągłego grzania CWU.
   - Temperatura bojlera powinna oscylować w rejonie 48–51°C.

---

## 6. Architektura Bezpieczeństwa i Zasady Integracji (Fail-Safe & Hardware)

### 6.1. Zabezpieczenia w przypadku awarii firmware / elektroniki
W przypadku zawieszenia oprogramowania układowego, awarii sieci lub błędu skryptów, bezpieczeństwo kotła gwarantują niezależne warstwy:
1. **Mechaniczny Termik STB (Sicherheits-Temperatur-Begrenzer):**
   - Fizyczny bimetal/kapilara w płaszczu wodnym wpięta **szeregowo w zasilanie 230V dmuchawy i ślimaka**.
   - Przekroczenie **90–95°C** bezwarunkowo i mechanicznie odcina zasilanie napędów, gasząc ogień w retorcie bez udziału procesora.
2. **Zawór bezpieczeństwa (1.5–2.5 bar) / Naczynie wzbiorcze:**
   - Zabezpieczenie przed wzrostem ciśnienia i rozerwaniem instalacji hydraulicznej.
3. **Zabezpieczenie przed cofnięciem żaru (BVTS / ochrona podajnika):**
   - Czujnik temperatury rury podajnika (`PARAM_POD_MAX_TEMP`) oraz awaryjne wypychanie żaru (`PARAM_PODAJNIK_CZASWYRZUTU`) lub mechaniczny strażak zalewowy.
4. **Hardware Watchdog Timer (WDT) & Przekaźniki NO:**
   - WDT resetuje procesor w ułamku sekundy przy zawieszeniu pętli.
   - Przekaźniki wykonawcze są w konfiguracji Normally Open (NO) – zanik sygnału sterującego wyłącza dmuchawę i ślimak.

### 6.2. Złota Zasada Smart Home: Home Assistant jako Nadzorca (Supervisor)
- **Nigdy nie sterować surowymi impulsami przekaźników z Home Assistant.**
- HA steruje wyłącznie wartościami zadanymi (`PARAM 40` Zadana CO, `PARAM 17` Zadana CWU, tryb Lato/Zima).
- Niskopoziomowy sterownik kotła (lub dedykowany mikrokontroler) zachowuje pełną autonomię nadzorowania czasów i limitów bezpieczeństwa.

### 6.3. Emulacja czujnika 1-Wire DS18B20 (ESP32 vs Linux SBC)
- **Reżim czasowy 1-Wire Slave (< 15 µs):**
  - Kocioł (Master) oczekuje odpowiedzi bitowej w oknie do 15 mikrosekund.
  - **ESP32:** Dedykowany mikrokontroler (Core 1 w pętli `OneWireHub.poll()`, Core 0 dla Wi-Fi/MQTT) realizuje to bez zakłóceń.
  - **Lichee Pi / Linux SBC:** Brak możliwości stabilnej emulacji programowej z poziomu GPIO w Linuksie z powodu jitteru planisty zadań (scheduler latency) i braku modułu slave w jądrze.

