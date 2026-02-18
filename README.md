# Ogniwo Furnace - integracja Home Assistant

Integracja [Home Assistant](https://www.home-assistant.io/) dla pieców firmy **Ogniwo Biecz** wyposażonych w sterownik **eCoal.pl** (producent: eSterownik.pl).

Komunikacja odbywa się bezpośrednio przez protokół HTTP sterownika eCoal - bez potrzeby korzystania z chmury eSterownik.pl.

## Wspierane urządzenia

- Piece Ogniwo Biecz ze sterownikiem eCoal.pl
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
| Feeding | Podawanie (%) |

### Przełączniki (switch)
| Encja | Opis |
|-------|------|
| Auto mode | Tryb automatyczny |
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
Heating state, Setpoint mode, CWU mode, Alarms code, Mixer valve, Day/Night, Controller clock, Fuel load date, Inputs.

## Instalacja

### HACS (zalecane)

1. Otwórz HACS w Home Assistant
2. Kliknij menu (trzy kropki) w prawym górnym rogu
3. Wybierz **Custom repositories**
4. Wpisz URL: `https://github.com/dkuku/ogniwo-furnace-ha`
5. Kategoria: **Integration**
6. Kliknij **Add**, a następnie zainstaluj **Ogniwo Furnace**
7. Uruchom ponownie Home Assistant

### Instalacja ręczna

1. Skopiuj folder `custom_components/ogniwo_furnace` do katalogu `custom_components/` w konfiguracji HA
2. Uruchom ponownie Home Assistant

## Konfiguracja

1. Przejdź do **Ustawienia** > **Urządzenia i usługi** > **Dodaj integrację**
2. Wyszukaj **Ogniwo Furnace**
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

## Dokumentacja protokołu

Szczegółowa dokumentacja protokołu eCoal znajduje się w [docs/protocol.md](docs/protocol.md).

## Istniejące biblioteki

- **ecoaliface** (v0.7.0) - obsługuje firmware v0.1 (Bruli) i v0.3 (Ecoal), **nie obsługuje** v0.2
- **HA ecoal_boiler** - oficjalna integracja HA, korzysta z ecoaliface

Ta integracja obsługuje firmware v0.2, który nie jest rozpoznawany przez powyższe biblioteki.

## Licencja

MIT License - patrz [LICENSE](LICENSE).
