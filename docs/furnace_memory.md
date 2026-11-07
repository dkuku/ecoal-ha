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
- **Pojemność robocza zasobnika (zaktualizowana 2026-11-04):** **100 kg** (`number.garaz_ecoal_pojemnosc_zasobnika = 100.0 kg`).
- Zasyp 4 worków po 25 kg (100 kg) eliminuje problem przepełniania zasobnika, zsypywania się węgla i blokowania klapy.
- Wcześniejsza pojemność bazowa wynosiła 150 kg (zasyp pod sam brzeg).
- Czas pracy ślimaka do wypalenia 100 kg: $100 / 0,3666 = \mathbf{272,8\text{ min}}$.

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
| **Czas postoju w podtrzymaniu** | `PARAM 13` | **120 min** | Maksymalna wartość sterownika (zwiększono z 45 min po testach 6h postoju) |
| **Czas pracy w podtrzymaniu** | `PARAM 10` | domyślny (~15s) | Podtrzymanie żaru |
| **Korekta dmuchawy** | `PARAM 94` | `0%` | Prawidłowy nadmuch |
| **Stan wyjść** | - | Pompa CWU: OFF, Pompa CO: ON, Dmuchawa: 4%, Ślimak: OFF | Kocioł cichy, brak ciągłego klikania |

---

## 4.1. Optymalizacja Temperatury i Ochrony Przed Przegrzewaniem (2026-11-05)

### Diagnoza problemu (przegrzewanie Kawalerki do 23.9°C):
- Przy pogodzie jesiennej ($T_{zew} \approx 7\text{--}11^\circ\text{C}$) kocioł pracował z nastawą **56°C** (z bezwładnością do 63°C). Kaloryfery pompowały gigantyczną moc do pomieszczeń.
- Użytkownik ręcznie gasił kocioł przełącznikiem `switch.ecoal_auto_mode` (MANUAL OFF) na 5–6 godzin dziennie i w nocy, gdy temperatura w Kawalerce przekraczała 23.5°C.
- Skutek uboczny: kocioł stygł do 29–37°C, ryzykując wygaszenie żaru oraz pracując w strefie agresywnej kondensacji spalin przy ponownym rozruchu.

### Wdrożone nastawy w sterowniku eCoal (2026-11-05):
| Rejestr | Parametr | Wartość przed | Wartość nowa | Cel zmiany |
| :--- | :--- | :--- | :--- | :--- |
| `PARAM 40` | **Zadana temp. kotła CO** | `56°C` | **`50°C`** | Spadek emisji grzejników o ~25-30%, natychmiastowe przejście w podtrzymanie |
| `PARAM 41` | **Obniżenie temp. CO** | `10°C` | **`5°C`** | Temperatura obniżona to bezpieczne **`45°C`** (powyżej punktu rosy) |
| `PARAM 70` | **Czas pracy pompy CO** | `5 min` | **`4 min`** | Krótsza dawka gorącej wody w grzejniki |
| `PARAM 71` | **Czas postoju pompy CO** | `15 min` | **`20 min`** | Dłuższy postój ogranicza oddawanie ciepła do pomieszczeń |
| `PARAM 17` | **Zadana temp. CWU** | `45°C` | `45°C` | Zachowana delta $\Delta T = 5^\circ\text{C}$ (50°C - 45°C) gwarantująca grzanie wody |

---

## 4.2. Przewodnik Sezonowy: Co zmienić, kiedy zrobi się chłodniej na zewnątrz?

Gdy nadejdą chłodniejsze dni i w Kawalerce temperatura spadnie poniżej komfortu (< 21.0–21.5°C), zmieniaj parametry **stopniowo w poniższej kolejności**:

### Krok 1: Umiarkowany chłód na zewnątrz ($T_{zew} = 2\text{--}7^\circ\text{C}$)
1. **Skróć postój pompy CO (`PARAM 71`):**
   - Zmień `PARAM 71` z **20 min** na **15 min** (lub **10 min**).
   - Kaloryfery będą częściej dogrzewane mniejszymi porcjami ciepła.
2. **Podnieś zadaną CO (`PARAM 40`):**
   - Zmień z **50°C** na **`53°C`**.
   - Obniżenie CO (`PARAM 41`) ustaw na **`6°C`** (aby zadana obniżona wynosiła 47°C).

### Krok 2: Mrozy i zima ($T_{zew} < 0^\circ\text{C}$)
1. **Zadana temp. kotła CO (`PARAM 40`):**
   - Zwiększ do **`56°C`** (przy mrozach poniżej -10°C: **`60°C`**).
2. **Zadana temp. CWU (`PARAM 17`):**
   - Zwiększ z 45°C do **`48°C` – `50°C`** (zimą woda z wodociągu ma 5°C i szybciej wychładza bojler).
3. **Praca ciągła pompy CO (`PARAM 69`):**
   - Zmień `PARAM 69` z `1` (cykliczna) na **`0` (ciągła)**.
   - W mroźne dni woda w instalacji powinna krążyć bez przerw, aby równomiernie ogrzewać cały dom, nie dopuścić do zamarzania rur przy ścianach zewnętrznych i utrzymać wysoką temperaturę powrotu kotła.
   - Temperaturą w poszczególnych pokojach sterują wtedy bezpośrednio głowice termostatyczne na grzejnikach.


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

---

## 7. Ostatnie Modyfikacje Konfiguracyjne

### 2026-11-07 (Eliminacja wychładzania kotła w podtrzymaniu):
- **Problem**: Pompa CO pracowała nieustannie 24/7 (`state: on` non-stop). Po wejściu w podtrzymanie obieg CO w 10–15 minut wychładzał kocioł z 50°C do 49°C, zmuszając go do ciągłego ponownego rozpalania.
- **Przyczyna**: `PARAM 78` (regulator pokojowy) był ustawiony na `0` (wyłączony), przez co sterownik eCoal ignorował fakt, że w domu jest 22.3°C (zadana 19°C), oraz ignorował nastawę pracy cyklicznej `PARAM 69=1` (4m praca / 20m postój).
- **Rozwiązanie**: Przestawiono `PARAM 78` na **`1`** (aktywny programator/regulator pokojowy).
- **Efekt**: Sterownik natychmiast uznał pomieszczenie za dogrzane i aktywował cykliczną przerwę pompy CO (4 minuty pracy / 20 minut postoju). Wymiennik kotła w podtrzymaniu przestał być wysysany z ciepła, a kocioł może bezpiecznie utrzymywać temperaturę przez ponad godzinę bez podawania opału.

---

## 8. Rejestr Zużycia Węgla i Porównanie Efektywności (Benchmark 2026-10 / 2026-11)

### 8.1. Zestawienie dobowe z bazy PostgreSQL (Home Assistant)
Przelicznik kalibracyjny: **0.3666 kg/min** czasu pracy ślimaka.

| Data | Czas pracy ślimaka | Spalony opał [kg] | Śr. temp. zewn. | Tryb / Warunki pracy |
| :---: | :---: | :---: | :---: | :--- |
| **2026-10-28** | 54.6 min | **20.02 kg** | +8.2°C | Praca jesienna, zadana CO 53°C |
| **2026-10-29** | 77.7 min | **28.48 kg** | +10.4°C | Praca ciągła, dogrzewanie domu |
| **2026-10-30** | 68.9 min | **25.26 kg** | +11.0°C | Praca ciągła, dogrzewanie domu |
| **2026-11-02** | 42.7 min | **15.65 kg** | +9.2°C | Ograniczony pobór ciepła |
| **2026-11-03** | 80.5 min | **29.51 kg** | +8.8°C | Postój manualny 5h w dzień |
| **2026-11-04** | 70.5 min | **25.85 kg** | +8.0°C | **Zasyp do pełna 100 kg** (reset licznika o 14:16, postój 6h 18m) |
| **2026-11-05** | 58.5 min | **21.45 kg** | +7.3°C | **Dwa postoje manualne**: noc 5h 19m + dzień 4h 35m |
| **2026-11-06** | 76.4 min | **28.01 kg** | +7.5°C | **Praca ciągła AUTO**: pompa CO chodziła 24/7 non-stop |
| **2026-11-07** | *w trakcie* | **~13.16 kg** (do 16:30) | +7.6°C | **Przełom po włączeniu `PARAM 78 = 1` o 08:10** |

### 8.2. Bezpośredni wpływ zatrzymania pompy CO (Porównanie 2026-11-07)
Dokładne rozbicie dzisiejszego zużycia przed i po aktywacji przerw pompy CO (`PARAM 78 = 1`):

| Okres | Godziny | Czas ślimaka | Węgiel [kg] | Średnie tempo spalania | Stan pompy CO |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Noc (przed zmianą)** | 00:00 – 08:10 (8.17 h) | 25.0 min | **9.17 kg** | **1.12 kg/h** | Pompa CO tłoczyła 24/7 (kocioł stygł w 10 min) |
| **Dzień (po zmianie)** | 08:10 – 16:30 (8.33 h) | 11.0 min | **4.03 kg** | **0.48 kg/h** | **Pompa CO w cyklu 4m praca / 20m postój** |

> **Wynik:** Tempo spalania węgla spadło z **1.12 kg/h do 0.48 kg/h (spadek o 57%)**! Kocioł w podtrzymaniu przestał oddawać ciepło do grzejników i utrzymuje stabilną temperaturę.

### 8.3. Stan zasobnika na dzień 2026-11-07 16:30
- Licznik pracy ślimaka od zasypu 100 kg (04.11 14:16): **203.4 minuty**.
- Łącznie spalono z zasypu 100 kg: $203.4 \times 0.3666 = \mathbf{74.56\text{ kg}}$.
- **Pozostało w zasobniku:** $100.0 - 74.56 = \mathbf{25.44\text{ kg}}$ (ok. 1 pełny worek 25 kg).


