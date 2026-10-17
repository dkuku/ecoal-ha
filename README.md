# eCoal - integracja Home Assistant

Eksperymentalna integracja [Home Assistant](https://www.home-assistant.io/) dla sterowników **eCoal.pl** (producent: eSterownik.pl) stosowanych w piecach na paliwo stałe.

Komunikacja odbywa się bezpośrednio przez protokół HTTP sterownika eCoal - bez potrzeby korzystania z chmury eSterownik.pl.

⚠️ **Używasz na własne ryzyko** - autor nie ponosi odpowiedzialności za ewentualne uszkodzenia pieca lub instalacji grzewczej. PR-y mile widziane!

## Wspierane urządzenia

- Piece ze sterownikiem eCoal.pl (firmware v0.2)
- Testowane na firmware v0.2.9.16a
- Obsługuje obieg CO, CWU oraz ogrzewanie podłogowe (obieg mieszacza)

## Encje

### Climate (termostaty)
| Encja | Opis |
|-------|------|
| Heating | Obieg centralnego ogrzewania (CO) - temperatura kotła |
| Hot Water | Ciepła woda użytkowa (CWU) |
| Floor Heating | Ogrzewanie podłogowe (jeśli czujnik podłączony) |

### Sensory temperatur
| Encja | Opis |
|-------|------|
| Boiler temperature | Temperatura kotła (CO) |
| DHW temperature | Temperatura CWU |
| Return temperature | Temperatura powrotu |
| Feeder temperature | Temperatura podajnika |
| Exhaust temperature | Temperatura spalin |
| Indoor temperature | Temperatura wewnętrzna (jeśli czujnik podłączony) |
| Outdoor temperature | Temperatura zewnętrzna (jeśli czujnik podłączony) |
| Floor temperature | Temperatura podłogowa (jeśli czujnik podłączony) |

### Sensory nastawów i parametrów
| Encja | Opis |
|-------|------|
| Target boiler temperature | Temperatura zadana CO |
| Target DHW temperature | Temperatura zadana CWU |
| CO lowered amount | Obniżenie temperatury CO |
| CWU lowered amount | Obniżenie temperatury CWU |
| Blower power | Moc dmuchawy (%) |
| Feeder runtime | Czas pracy podajnika (minuty) |
| Fuel load | Zapas paliwa (%) |
| Fuel remaining | Pozostało węgla (kg) wyliczane z pojemności zasobnika |
| Feeding | Podawanie (%) |

### Przyciski (button)
| Encja | Opis |
|-------|------|
| Refill hopper (100%) | Zeruje czas pracy podajnika, ustawia zapas na 100% i zapisuje dzisiejszą datę zasypu |
| Acknowledge alarms | Kasuje aktywne alarmy sterownika |
| Synchronize clock | Synchronizuje zegar sterownika z czasem systemowym HA |

### Ustawienia numeryczne (number)
| Encja | Opis |
|-------|------|
| Hopper capacity | Pojemność zasobnika w kg (domyślnie 150 kg, zapamiętywana po restarcie) |
| Feeder max runtime | Czas pracy podajnika do opróżnienia zasobnika w minutach (PARAM 79 w sterowniku) |
| Blower power correction | Korekta mocy dmuchawy w % (-6% .. +6%, PARAM 94 w sterowniku) |

### Wybór trybu (select)
| Encja | Opis |
|-------|------|
| Feeder mode | Algorytm spalania podajnika (PARAM 119): Retortowy ręczny / Spalanie grupowe / Algorytm eCoal / Zasypowy |

### Przełączniki (switch)
| Encja | Opis |
|-------|------|
| Auto mode | Tryb automatyczny |
| DHW priority | Priorytet grzania CWU — wyłącza obieg CO na czas dogrzewania bojlera (PARAM 112) |
| Exhaust temp regulator | Regulator temperatury spalin — ogranicza nadmuch przy zbyt gorących spalinach (PARAM 98) |
| Blower | Dmuchawa (ręczne sterowanie) |
| Coal feeder | Podajnik (ręczne sterowanie) |
| CH pump | Pompa CO |
| DHW pump | Pompa CWU |
| Mixer pump | Pompa mieszająca (jeśli czujnik podłączony) |

### Sensory binarne
| Encja | Opis |
|-------|------|
| Alarm | Aktywny alarm pieca |
| CO lowered | Aktywne obniżenie CO |
| CWU lowered | Aktywne obniżenie CWU |
| Summer mode | Tryb letni |

### Sensory diagnostyczne
Heating state, Setpoint mode, CWU mode, Alarms code, Mixer valve, Day/Night, Controller clock, Fuel load date, Estimated empty date, Inputs.

## Instalacja

### HACS (zalecane)

1. Otwórz HACS w Home Assistant
2. Kliknij menu (trzy kropki) w prawym górnym rogu
3. Wybierz **Custom repositories**
4. Wpisz URL: `https://github.com/dkuku/ecoal-ha`
5. Kategoria: **Integration**
6. Kliknij **Add**, a następnie zainstaluj **eCoal**
7. Uruchom ponownie Home Assistant

### Instalacja ręczna

1. Skopiuj folder `custom_components/ecoal` do katalogu `custom_components/` w konfiguracji HA
2. Uruchom ponownie Home Assistant

## Konfiguracja

1. Przejdź do **Ustawienia** > **Urządzenia i usługi** > **Dodaj integrację**
2. Wyszukaj **eCoal**
3. Podaj:
   - **Adres IP** sterownika eCoal
   - **Użytkownik** (konto na panelu webowym sterownika)
   - **Hasło**

## Schemat sieci

Sterownik eCoal komunikuje się po HTTP na porcie 80 w sieci lokalnej. Jeśli piec jest w odizolowanej sieci (np. za SBC), potrzebny jest routing lub NAT.

```
Piec (sterownik eCoal, sieć lokalna)
    ↕ HTTP port 80 (Basic Auth)
Home Assistant
```

Integracja odpytuje sterownik co 30 sekund.

## Nowoczesny Panel WWW (SPA) & Schemat Hydrauliczny

W wersji **1.2.0** integracja zawiera nowoczesny, responsywny panel webowy (Single Page Application) dostępny bezpośrednio w **pasku bocznym Home Assistant** (ikona ognia 🔥 `mdi:fire`):

* **Wektorowy, animowany schemat hydrauliczny (SVG):**
  * Animowany płomień w kotle reagujący na moc dmuchawy i stan grzania.
  * Animowane przepływy wody w rurach CO (zasilanie / powrót) i CWU.
  * Obracające się wirniki pomp obiegowych (Pompa CO, Pompa CWU, Pompa Mieszająca).
  * Bieżące temperatury nałożone bezpośrednio na instalację.
* **Szybkie sterowanie nastawami:** Przyciski `+` / `-` dla zadanej kotła i bojlera, reset zasypu 100%, zmiana trybu spalania.
* **Pełne pokrycie 122 parametrów sterownika:** Podział na grupy (*Spalanie*, *Zaawansowane*, *Kalibracja*, *Harmonogramy*).
* **Likwidacja błędu producenta z 2011 r.:** Naprawiono problem *"Nie wszystkie parametry odczytano"*, wynikający ze statusu 21 (NAK) zwracanego przez firmware dla rejestrów $\ge 96$.
* **Edytor 7 programatorów tygodniowych:** Interaktywna siatka 48 slotów 30-minutowych dla każdego dnia tygodnia.

---

## Wirtualny Symulator Kotła (`tools/mock_furnace.py`)

Aby umożliwić bezpieczne testowanie automatyzacji i interfejsu przed sezonem zimowym bez ingerencji w pracujący kocioł, projekt zawiera pełny symulator eCoal w Pythonie:

```bash
# Uruchomienie lokalnego symulatora na porcie 8080:
python3 tools/mock_furnace.py --port 8080

# Uruchomienie z symulacją anomalii firmware NAK (status 21):
python3 tools/mock_furnace.py --port 8080 --quirk
```

Symulator emuluje wszystkie 122 rejestry, generuje autentyczne 86-bajtowe ramki statusu z pływającymi temperaturami oraz ubywanie węgla w zasobniku podczas pracy podajnika.

---

## Samodzielny Mostek ESP32 (`esp32/`)

Interfejs WWW został zaprojektowany w architekturze **Adapter Pattern** z zerową liczbą zależności (czysty HTML5/CSS/JS ES modules):
* Ten sam kod WWW działa w Home Assistant, na komputerze przez **Web Serial API** lub bezpośrednio z mikrokontrolera **ESP32-C3 / ESP32-S3**.
* Mikrokontroler serwuje interfejs z pamięci **LittleFS** i komunikuje się z płytą główną kotła przez sprzętowy port UART / RS-232 (19200 8N1).
* Szczegółowy schemat połączeń elektrycznych (konwerter MAX3232) oraz gotowy szkic Arduino / ESPHome znajdują się w katalogu [esp32/](esp32/README.md).

---

## Dokumentacja protokołu

Szczegółowa dokumentacja protokołu eCoal znajduje się w [docs/protocol.md](docs/protocol.md), a plan wdrożenia nowego interfejsu w [docs/modern_ui_plan.md](docs/modern_ui_plan.md).

## Testy Automatyczne

```bash
# Uruchomienie testów Pythona (Mock, Views, Coordinator):
pytest -v

# Uruchomienie testów JavaScript (Protokół, CRC8, 122/122 Coverage, E2E HTTP):
node --test tests/frontend/*.test.mjs
```

## Licencja

MIT License - patrz [LICENSE](LICENSE).
