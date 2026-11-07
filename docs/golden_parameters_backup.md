# eCoal & Ogniwo Eko Plus – Złoty Profil Konfiguracyjny (Golden Backup)

Niniejszy dokument stanowi pełną specyfikację nastaw i punkt bazowy konfiguracji sterownika **eCoal v0.2.9.16** w kotłowni na wypadek awarii, wymiany elektroniki lub resetu do ustawień fabrycznych (*Factory Reset*).

- **Plik zrzutu binarnego / JSON:** [`docs/golden_config.json`](file:///home/kuku/Projects/ogniwo-furnace-ha/docs/golden_config.json)
- **Narzędzie CLI do kopii i przywracania:** [`tools/backup_restore.py`](file:///home/kuku/Projects/ogniwo-furnace-ha/tools/backup_restore.py)

---

## 1. Tabela Kluczowych Wartości Złotego Profilu

Poniższa tabela zawiera wszystkie zmodyfikowane parametry w stosunku do nastaw fabrycznych oraz uzasadnienie inżynieryjne:

| ID | Rejestr eCoal | Nastawa Złota | Domyślna fabryczna | Cel i uzasadnienie modyfikacji |
| :---: | :--- | :---: | :---: | :--- |
| **13** | `PARAM_POD_POST_PODT` | **120 min** | 40 min | **Ochrona przed marnowaniem opału w podtrzymaniu**. W retorcie Ogniwa żar tli się bezpiecznie przez >5h (spaliny ~60°C). 120 min zmniejsza liczbę niepotrzebnych przedmuchów i wydłuża żywotność przekaźnika. |
| **16** | `PARAM_CWU_TRYB` | **0 (Wył)** / **1 (Zima)** | 1 (Zima) | Tryb pracy pompy CWU. |
| **17** | `PARAM_CWU_ZADANA` | **45°C** (lub 50°C) | 50°C | **Likwidacja pułapki termicznej CWU**. Musi być zawsze o minimum 3–5°C niższa niż zadana CO (50°C), inaczej pompa CWU chodzi w pętli 24/7. |
| **18** | `PARAM_CWU_HIST` | **2.0°C** (`20`) | 1.0°C (`10`) | Histereza bojlera CWU. |
| **19** | `PARAM_MIESZ_AKTYWACJA` | **2 (Podłogówka)** | 0 (Wył) | Wyjście OUT 4/6/7 steruje obwodem podłogowym z pompą mieszającą. |
| **29** | `PARAM_CWU_OBNIZONA` | **10°C** | 10°C | Obniżenie zadanej CWU w harmonogramie. |
| **32** | `PARAM_POKOJ_DZIENNA` | **19.0°C** (`190`) | 21.0°C (`210`) | Zadana temperatura dzienna w domu. |
| **33** | `PARAM_POKOJ_NOCNA` | **17.0°C** (`170`) | 17.0°C (`170`) | Zadana temperatura nocna w domu. |
| **40** | `PARAM_CO_ZADANA` | **50°C** | 55°C | **Zadana temperatura kotła CO**. Obniżona z 56°C do 50°C na okres przejściowy (jesień/wiosna) – eliminuje przegrzewanie i redukuje spalanie. |
| **41** | `PARAM_CO_OBNIZONA` | **5°C** | 10°C | **Nocna temperatura kotła CO = 45°C** (50°C - 5°C). Kocioł płynnie przechodzi w 45°C bez ryzyka wygaszenia. |
| **50** | `PARAM_ZADAWANIE` | **0 (Ręczne)** | 0 (Ręczne) | Zadawanie z programatorem tygodniowym (nie pogodówka). |
| **51** | `PARAM_TRYB_PRACY` | **1 (Auto)** | 1 (Auto) | Tryb pracy automatycznej algorytmu podajnika. |
| **69** | `PARAM_POMPACO_TRYB` | **1 (Cykliczna)** | 0 (Ciągła) | **Eliminacja wysysania ciepła w podtrzymaniu**. Włącza przerwy w pracy pompy CO, gdy pokoje osiągną zadaną temperaturę. |
| **70** | `PARAM_POMPACO_PRACA` | **4 min** | 5 min | Czas pracy pompy CO w cyklu podtrzymania (przetoczenie wody). |
| **71** | `PARAM_POMPACO_POSTOJ` | **20 min** | 30 min | Czas pełnego postoju pompy CO w cyklu podtrzymania (utrzymuje ciepło w kotle). |
| **78** | `PARAM_WEW_ZADAWANIE` | **1 (Programator)** | 0 (Wyłączony) | **Kluczowy aktywator przerw pompy CO**. Pozwala sterownikowi czytać czujnik wewnętrzny (22.3°C) i zarządzać cyklem 4m/20m. |
| **79** | `PARAM_PODAJNIK_CZASALARM` | **600 min** | 0 min | Czas do opróżnienia zasobnika w sterowniku. |
| **80** | `PARAM_REG_POK_HISTEREZA` | **0.3°C** (`3`) | 0.3°C (`3`) | Histereza regulatora pokojowego. |
| **88** | `PARAM_POMPA_CWU_WYJSCIE` | **0** | 0 | Fizyczne wyjście przekaźnika pompy CWU. |
| **92** | `PARAM_TYP_KOTLA` | **2** | 2 | Typ kotła w algorytmie (Ogniwo Eko Plus). |
| **94** | `PARAM_KOREKTA_DMUCHAWY_GRZANIE` | **0%** | 0% | Neutralna korekta ciągu kominowego. |
| **119**| `PARAM_TYP_PODAJNIKA` | **1 (Grupowe)** | 1 | Algorytm spalania: retortowy grupowe. |

---

## 2. Parametry Kalibracji Home Assistant (Zasobnik & Podajnik)

Parametry przechowywane w Home Assistant (`.storage` oraz rejestry integracji):
- **Pojemność zasobnika:** **`100 kg`** (`number.garaz_ecoal_pojemnosc_zasobnika`) – optymalna na 4 worki po 25 kg.
- **Wydatek podajnika:** **`0.3666 kg/min`** (**`22.0 kg/h`**) – zmierzone z 136.4 min pracy ślimaka = 50.0 kg.
- **Formuła spalania:** $\text{Opał [kg]} = \text{czas pracy [min]} \times 0.3666$.

---

## 3. Szybkie Przywracanie z Linii Komend (1 Komenda)

Wszystkie parametry sterownika można w każdej chwili zweryfikować lub przywrócić za pomocą dołączonego skryptu:

### Sprawdzenie rozbieżności (Diff):
```bash
python3 tools/backup_restore.py diff
```
*Wyjście wskaże dokładnie, które parametry różnią się od profilu wzorcowego.*

### Pełne przywrócenie profilu (Restore):
```bash
python3 tools/backup_restore.py restore
```
*Skrypt sekwencyjnie zapisze z powrotem wszystkie 96 rejestrów oraz 7 harmonogramów tygodniowych.*

### Utworzenie nowej kopii zapasowej:
```bash
python3 tools/backup_restore.py backup
```

---

## 4. Ręczna Ściągawka Klawiaturowa (Gdy brak sieci w kotłowni)

W przypadku wymiany płyty głównej bez podłączenia do sieci Ethernet, wystarczy na panelu kotła wprowadzić te 6 krytycznych ustawień:
1. **Menu Kocioł -> Temperatura zadana CO:** `50°C`
2. **Menu Kocioł -> Obniżenie temperatury CO:** `5°C`
3. **Menu CWU -> Temperatura zadana CWU:** `45°C`
4. **Menu Podajnik -> Czas postoju w podtrzymaniu:** `120 min`
5. **Menu Zaawansowane -> Regulator pokojowy:** `Programator wewnętrzny` (lub `Włączony`)
6. **Menu Zaawansowane -> Praca pompy CO:** `Cykliczna` -> Praca: `4 min`, Postój: `20 min`
