/**
 * eCoal Full Parameter Catalog (122 Parameters)
 *
 * 1:1 match with physical eCoal controller firmware registers (v0.2.9.16a).
 * Grouped to mirror controller UI:
 * - gr_user: Main setpoints, room temps, fuel counter (9 items)
 * - gr_spalanie: Combustion, blower & group combustion tuning (34 items)
 * - gr_zaaw: Advanced settings, safety, mixer, boiler limits (23 items)
 * - gr_kalib: Sensor calibration offsets (8 items)
 * - gr_krzywa: Heating curve endpoints (2 items)
 * - gr_eth: Network parameters & auth (7 items)
 * - gr_serwer: Remote esterownik cloud (4 items)
 * - schedules: 7-day weekly schedule tables (7 items)
 * - extended: Floor heating, circulation, service blower characteristics (28 items)
 */

export const ECOAL_PARAMETERS = [
  // --- gr_kalib: Kalibracja czujników (8) ---
  { id: 0, key: "PARAM_OFFSET_Z1", group: "gr_kalib", name: "Offset czujnika Z1", unit: "°C", div: 10, min: -100, max: 100 },
  { id: 1, key: "PARAM_OFFSET_WEW", group: "gr_kalib", name: "Offset czujnika wewnętrznego", unit: "°C", div: 10, min: -100, max: 100 },
  { id: 2, key: "PARAM_OFFSET_ZEW", group: "gr_kalib", name: "Offset czujnika zewnętrznego", unit: "°C", div: 10, min: -100, max: 100 },
  { id: 3, key: "PARAM_OFFSET_CWU", group: "gr_kalib", name: "Offset czujnika CWU", unit: "°C", div: 10, min: -100, max: 100 },
  { id: 4, key: "PARAM_OFFSET_POW", group: "gr_kalib", name: "Offset czujnika powrotu", unit: "°C", div: 10, min: -100, max: 100 },
  { id: 5, key: "PARAM_OFFSET_POD", group: "gr_kalib", name: "Offset czujnika podajnika", unit: "°C", div: 10, min: -100, max: 100 },
  { id: 6, key: "PARAM_OFFSET_CO", group: "gr_kalib", name: "Offset czujnika CO", unit: "°C", div: 10, min: -100, max: 100 },
  { id: 7, key: "PARAM_OFFSET_SPA", group: "gr_kalib", name: "Offset czujnika spalin", unit: "°C", div: 10, min: -100, max: 100 },

  // --- gr_spalanie: Spalanie, dmuchawa, podtrzymanie, spalanie grupowe (33) ---
  { id: 8, key: "PARAM_MOC_DMUCH", group: "gr_spalanie", name: "Moc dmuchawy podtrzymania", unit: "%", div: 1, min: 1, max: 100 },
  { id: 9, key: "PARAM_MOC_DMUCH_PODT", group: "gr_spalanie", name: "Moc dmuchawy podtrzymania 2", unit: "%", div: 1, min: 1, max: 100 },
  { id: 10, key: "PARAM_POD_CZASPRACY_PODT", group: "gr_spalanie", name: "Czas pracy podajnika w podtrzymaniu", unit: "s", div: 1, min: 1, max: 100 },
  { id: 11, key: "PARAM_POD_PRZERWA_PODT", group: "gr_spalanie", name: "Czas przerwy podawania w podtrzymaniu", unit: "s", div: 1, min: 1, max: 60 },
  { id: 12, key: "PARAM_POWT_PODT", group: "gr_spalanie", name: "Ilość powtórzeń w podtrzymaniu", unit: "ilość", div: 1, min: 1, max: 10 },
  { id: 13, key: "PARAM_POD_POST_PODT", group: "gr_spalanie", name: "Czas postoju podajnika w podtrzymaniu", unit: "min", div: 1, min: 1, max: 60 },
  { id: 34, key: "PARAM_POD_CZASPRACY_GRZ", group: "gr_spalanie", name: "Czas pracy podajnika w grzaniu", unit: "s", div: 1, min: 1, max: 60 },
  { id: 35, key: "PARAM_POD_POST_GRZ", group: "gr_spalanie", name: "Czas postoju podajnika w grzaniu", unit: "s", div: 1, min: 1, max: 60 },
  { id: 92, key: "PARAM_TYP_KOTLA", group: "gr_spalanie", name: "Typ kotła", unit: "", div: 1, min: 0, max: 5 },
  { id: 94, key: "PARAM_KOREKTA_DMUCHAWY_GRZANIE", group: "gr_spalanie", name: "Korekta dmuchawy grzanie", unit: "%", div: 1, min: -6, max: 6 },
  { id: 96, key: "PARAM_MAX_TEMP_SPALIN", group: "gr_spalanie", name: "Maksymalna temperatura spalin", unit: "°C", div: 1, min: 100, max: 350 },
  { id: 97, key: "PARAM_MOC_DMUCH_GRZ", group: "gr_spalanie", name: "Moc dmuchawy grzanie ręczne", unit: "%", div: 1, min: 1, max: 100 },
  { id: 98, key: "PARAM_REGULATOR_SPALIN", group: "gr_spalanie", name: "Regulator temperatury spalin", unit: "", div: 1, min: 0, max: 1 },
  { id: 99, key: "PARAM_MIN_MOC_DMUCH", group: "gr_spalanie", name: "Minimalna moc dmuchawy", unit: "%", div: 1, min: 1, max: 50 },
  { id: 100, key: "PARAM_ALG_MAXMOC", group: "gr_spalanie", name: "Maksymalna moc kotła w spalaniu grupowym", unit: "kW", div: 1, min: 8, max: 30 },
  { id: 101, key: "PARAM_ALG_MOCDMUCH8", group: "gr_spalanie", name: "Moc dmuchawy progu 8 kW", unit: "%", div: 1, min: 1, max: 100 },
  { id: 102, key: "PARAM_ALG_MOCDMUCH12", group: "gr_spalanie", name: "Moc dmuchawy progu 12 kW", unit: "%", div: 1, min: 1, max: 100 },
  { id: 103, key: "PARAM_ALG_MOCDMUCH16", group: "gr_spalanie", name: "Moc dmuchawy progu 16 kW", unit: "%", div: 1, min: 1, max: 100 },
  { id: 104, key: "PARAM_ALG_MOCDMUCH20", group: "gr_spalanie", name: "Moc dmuchawy progu 20 kW", unit: "%", div: 1, min: 1, max: 100 },
  { id: 105, key: "PARAM_ALG_MOCDMUCH25", group: "gr_spalanie", name: "Moc dmuchawy progu 25 kW", unit: "%", div: 1, min: 1, max: 100 },
  { id: 106, key: "PARAM_ALG_MINMOC", group: "gr_spalanie", name: "Minimalna moc kotła w spalaniu grupowym", unit: "kW", div: 1, min: 8, max: 30 },
  { id: 107, key: "PARAM_ZASYP_CZASPRZEDMUCHU", group: "gr_spalanie", name: "Czas przedmuchu zasypowego", unit: "s", div: 1, min: 1, max: 60 },
  { id: 108, key: "PARAM_ZASYP_ODSTEPPRZEDMUCH", group: "gr_spalanie", name: "Odstęp między przedmuchami zasypowymi", unit: "min", div: 1, min: 1, max: 60 },
  { id: 109, key: "PARAM_ZASYP_MOCDMUCH", group: "gr_spalanie", name: "Moc dmuchawy zasypowej", unit: "%", div: 1, min: 1, max: 100 },
  { id: 110, key: "PARAM_ZASYP_STREFAAUTO", group: "gr_spalanie", name: "Strefa autoregulacji zasypowej", unit: "°C", div: 1, min: 1, max: 20 },
  { id: 118, key: "PARAM_CZAS_POSTOJU_GRZANIE", group: "gr_spalanie", name: "Czas postoju podajnika 2 w grzaniu", unit: "s", div: 1, min: 1, max: 60 },
  { id: 120, key: "PARAM_HIST_TEMP_CO", group: "gr_spalanie", name: "Histereza temperatury kotła CO", unit: "°C", div: 1, min: 1, max: 10 },
  { id: 125, key: "PARAM_ALG_MOCDMUCH30", group: "gr_spalanie", name: "Moc dmuchawy progu 30 kW", unit: "%", div: 1, min: 1, max: 100 },
  { id: 126, key: "PARAM_ALG_ILGRUP8", group: "gr_spalanie", name: "Ilość podań paliwa progu 8 kW", unit: "ilość", div: 1, min: 1, max: 15 },
  { id: 127, key: "PARAM_ALG_ILGRUP12", group: "gr_spalanie", name: "Ilość podań paliwa progu 12 kW", unit: "ilość", div: 1, min: 1, max: 15 },
  { id: 128, key: "PARAM_ALG_ILGRUP16", group: "gr_spalanie", name: "Ilość podań paliwa progu 16 kW", unit: "ilość", div: 1, min: 1, max: 15 },
  { id: 129, key: "PARAM_ALG_ILGRUP20", group: "gr_spalanie", name: "Ilość podań paliwa progu 20 kW", unit: "ilość", div: 1, min: 1, max: 15 },
  { id: 130, key: "PARAM_ALG_ILGRUP25", group: "gr_spalanie", name: "Ilość podań paliwa progu 25 kW", unit: "ilość", div: 1, min: 1, max: 15 },
  { id: 131, key: "PARAM_ALG_ILGRUP30", group: "gr_spalanie", name: "Ilość podań paliwa progu 30 kW", unit: "ilość", div: 1, min: 1, max: 15 },

  // --- gr_zaaw: Ustawienia zaawansowane kotła, mieszacz, bezpieczeństwo (23) ---
  { id: 14, key: "PARAM_POD_MAX_TEMP", group: "gr_zaaw", name: "Maksymalna temperatura podajnika", unit: "°C", div: 1, min: 60, max: 110 },
  { id: 18, key: "PARAM_CWU_HIST", group: "gr_zaaw", name: "Histereza bojlera CWU", unit: "°C", div: 10, min: 2, max: 50 },
  { id: 19, key: "PARAM_MIESZ_AKTYWACJA", group: "gr_zaaw", name: "Aktywacja ochrony powrotu / mieszacza", unit: "", div: 1, min: 0, max: 2 },
  { id: 38, key: "PARAM_CO_MIN", group: "gr_zaaw", name: "Minimalna temperatura kotła CO", unit: "°C", div: 1, min: 42, max: 60 },
  { id: 39, key: "PARAM_CO_MAX", group: "gr_zaaw", name: "Maksymalna temperatura kotła CO", unit: "°C", div: 1, min: 65, max: 80 },
  { id: 69, key: "PARAM_POMPACO_TRYB", group: "gr_zaaw", name: "Praca cykliczna pompy CO", unit: "", div: 1, min: 0, max: 2 },
  { id: 70, key: "PARAM_POMPACO_PRACA", group: "gr_zaaw", name: "Czas pracy cyklicznej pompy CO", unit: "min", div: 1, min: 1, max: 60 },
  { id: 71, key: "PARAM_POMPACO_POSTOJ", group: "gr_zaaw", name: "Czas postoju cyklicznego pompy CO", unit: "min", div: 1, min: 1, max: 60 },
  { id: 77, key: "PARAM_AUTOLATO_TEMP", group: "gr_zaaw", name: "Temperatura progu Auto-Lato", unit: "°C", div: 1, min: 0, max: 25 },
  { id: 81, key: "PARAM_POMPA_CWU_HISTEREZA_AL", group: "gr_zaaw", name: "Histereza CWU w Auto-Lato", unit: "°C", div: 10, min: 5, max: 50 },
  { id: 88, key: "PARAM_POMPA_CWU_WYJSCIE", group: "gr_zaaw", name: "Wyjście pompy CWU", unit: "", div: 1, min: 0, max: 1 },
  { id: 89, key: "PARAM_ALARM_CZASOPOZNIENIA", group: "gr_zaaw", name: "Czas opóźnienia alarmu zewnętrznego", unit: "s", div: 1, min: 0, max: 600 },
  { id: 90, key: "PARAM_ALARM_INWERSJA", group: "gr_zaaw", name: "Inwersja wejścia alarmu zewnętrznego", unit: "", div: 1, min: 0, max: 1 },
  { id: 91, key: "PARAM_ALARM_ZATRZYMANIE", group: "gr_zaaw", name: "Zatrzymanie kotła przy alarmie zewnętrznym", unit: "", div: 1, min: 0, max: 1 },
  { id: 93, key: "PARAM_AKTYWACJA_MIESZAJACA_LATO", group: "gr_zaaw", name: "Praca pompy mieszającej w lecie", unit: "", div: 1, min: 0, max: 1 },
  { id: 95, key: "PARAM_OKRES_REJESTRACJI", group: "gr_zaaw", name: "Okres rejestracji historii", unit: "", div: 1, min: 0, max: 3 },
  { id: 111, key: "PARAM_ALG_WYGASZENIA", group: "gr_zaaw", name: "Automatyczne wygaszanie kotła", unit: "", div: 1, min: 0, max: 1 },
  { id: 115, key: "PARAM_TEMP_ZAL_MIESZ", group: "gr_zaaw", name: "Temperatura załączenia pompy mieszającej", unit: "°C", div: 1, min: 35, max: 70 },
  { id: 119, key: "PARAM_TYP_PODAJNIKA", group: "gr_zaaw", name: "Typ podajnika / Algorytm spalania", unit: "", div: 1, min: 0, max: 3 },
  { id: 121, key: "PARAM_PODBICIE_TEMP", group: "gr_zaaw", name: "Podbicie temperatury CO przy grzaniu CWU", unit: "°C", div: 1, min: 0, max: 20 },
  { id: 122, key: "PARAM_PODAJNIK_CZASWYRZUTU", group: "gr_zaaw", name: "Czas awaryjnego wyrzutu paliwa ze ślimaka", unit: "s", div: 1, min: 10, max: 300 },
  { id: 132, key: "PARAM_CZUJNIK_ZAMZAS", group: "gr_zaaw", name: "Czujnik otwarcia klapy zasobnika", unit: "styk", div: 1, min: 0, max: 1 },
  { id: 133, key: "PARAM_CZUJNIK_ZERZAW", group: "gr_zaaw", name: "Czujnik obrotu / zerwania zawleczki ślimaka", unit: "styk", div: 1, min: 0, max: 1 },

  // --- gr_user: Pulpit użytkownika, zadane, zapas opału (9) ---
  { id: 16, key: "PARAM_CWU_TRYB", group: "gr_user", name: "Tryb pracy pompy CWU", unit: "", div: 1, min: 0, max: 4 },
  { id: 17, key: "PARAM_CWU_ZADANA", group: "gr_user", name: "Zadana temperatura CWU", unit: "°C", div: 1, min: 35, max: 65 },
  { id: 29, key: "PARAM_CWU_OBNIZONA", group: "gr_user", name: "Obniżenie temperatury CWU", unit: "°C", div: 1, min: 0, max: 20 },
  { id: 40, key: "PARAM_CO_ZADANA", group: "gr_user", name: "Zadana temperatura kotła CO", unit: "°C", div: 1, min: 45, max: 80 },
  { id: 41, key: "PARAM_CO_OBNIZONA", group: "gr_user", name: "Obniżenie temperatury CO", unit: "°C", div: 1, min: 0, max: 20 },
  { id: 50, key: "PARAM_ZADAWANIE", group: "gr_user", name: "Sposób zadawania temperatury CO", unit: "", div: 1, min: 0, max: 3 },
  { id: 51, key: "PARAM_TRYB_PRACY", group: "gr_user", name: "Tryb pracy kotła (Auto/Manual)", unit: "", div: 1, min: 0, max: 1 },
  { id: 79, key: "PARAM_PODAJNIK_CZASALARM", group: "gr_user", name: "Czas pracy ślimaka dla pełnego zasobnika", unit: "min", div: 1, min: 0, max: 1000 },
  { id: 112, key: "PARAM_PRIORYTET_CWU", group: "gr_user", name: "Priorytet bojlera CWU", unit: "", div: 1, min: 0, max: 1 },

  // --- gr_krzywa: Krzywa grzania (2) ---
  { id: 30, key: "PARAM_PROG_CO_M10", group: "gr_krzywa", name: "Temperatura krzywej dla -10°C", unit: "°C", div: 1, min: 45, max: 80 },
  { id: 31, key: "PARAM_PROG_CO_P10", group: "gr_krzywa", name: "Temperatura krzywej dla +10°C", unit: "°C", div: 1, min: 40, max: 70 },

  // --- gr_eth: Sieć Ethernet i logowanie (8) ---
  { id: 21, key: "PARAM_LANGUAGE", group: "gr_eth", name: "Język menu sterownika", unit: "", div: 1, min: 0, max: 3 },
  { id: 45, key: "PARAM_IP", group: "gr_eth", name: "Adres IP sterownika", unit: "ip", div: 1, min: 0, max: 255 },
  { id: 46, key: "PARAM_MASKA", group: "gr_eth", name: "Maska podsieci", unit: "ip", div: 1, min: 0, max: 255 },
  { id: 47, key: "PARAM_BRAMA", group: "gr_eth", name: "Brama domyślna", unit: "ip", div: 1, min: 0, max: 255 },
  { id: 66, key: "PARAM_MAC", group: "gr_eth", name: "Adres fizyczny MAC", unit: "mac", div: 1, min: 0, max: 255 },
  { id: 67, key: "PARAM_AUTH_USER", group: "gr_eth", name: "Autoryzacja użytkownika", unit: "auth", div: 1, min: 0, max: 255 },
  { id: 68, key: "PARAM_AUTH_ADMIN", group: "gr_eth", name: "Autoryzacja administratora", unit: "auth", div: 1, min: 0, max: 255 },

  // --- gr_serwer: Zdalne połączenie eSterownik.pl (4) ---
  { id: 72, key: "PARAM_SERWER_PORT", group: "gr_serwer", name: "Port serwera eSterownik.pl", unit: "", div: 1, min: 1, max: 65535 },
  { id: 73, key: "PARAM_SERWER_ID", group: "gr_serwer", name: "ID urządzenia na serwerze", unit: "", div: 1, min: 0, max: 65535 },
  { id: 74, key: "PARAM_SERWER_AKTYWACJA", group: "gr_serwer", name: "Aktywacja zdalnego dostępu", unit: "", div: 1, min: 0, max: 1 },
  { id: 75, key: "PARAM_SERWER_IP", group: "gr_serwer", name: "Adres IP serwera eSterownik", unit: "ip", div: 1, min: 0, max: 255 },

  // --- schedules: Harmonogramy tygodniowe tablice 42B (7) ---
  { id: 24, key: "PARAM_PROG_CO_TAB", group: "schedules", name: "Harmonogram tygodniowy CO", unit: "bytes", div: 1, min: 0, max: 255 },
  { id: 25, key: "PARAM_PROG_CWU_TAB", group: "schedules", name: "Harmonogram tygodniowy CWU", unit: "bytes", div: 1, min: 0, max: 255 },
  { id: 26, key: "PARAM_PROG_POGODOWY_TAB", group: "schedules", name: "Harmonogram pogodowy", unit: "bytes", div: 1, min: 0, max: 255 },
  { id: 27, key: "PARAM_PROG_POKOJOWY_TAB", group: "schedules", name: "Harmonogram pokojowy", unit: "bytes", div: 1, min: 0, max: 255 },
  { id: 28, key: "PARAM_PROG_OBIEG_TAB", group: "schedules", name: "Harmonogram cyrkulacji CWU", unit: "bytes", div: 1, min: 0, max: 255 },
  { id: 83, key: "PARAM_PROG_AUTOLATO", group: "schedules", name: "Harmonogram Auto-Lato", unit: "bytes", div: 1, min: 0, max: 255 },
  { id: 87, key: "PARAM_PROG_PODLOGOWA", group: "schedules", name: "Harmonogram podłogówki", unit: "bytes", div: 1, min: 0, max: 255 },

  // --- extended: Obwód podłogowy, cyrkulacja, charakterystyka dmuchawy (28) ---
  { id: 15, key: "PARAM_POD_CZAS_OBR", group: "extended", name: "Czas jednego obrotu ślimaka", unit: "s", div: 1, min: 1, max: 100 },
  { id: 22, key: "PARAM_OBIEG_CZASPRACY", group: "extended", name: "Czas pracy pompy cyrkulacyjnej", unit: "min", div: 1, min: 1, max: 60 },
  { id: 23, key: "PARAM_OBIEG_POSTOJ", group: "extended", name: "Czas postoju pompy cyrkulacyjnej", unit: "min", div: 1, min: 1, max: 60 },
  { id: 32, key: "PARAM_POKOJ_DZIENNA", group: "extended", name: "Temperatura pokojowa dzienna", unit: "°C", div: 10, min: 100, max: 350 },
  { id: 33, key: "PARAM_POKOJ_NOCNA", group: "extended", name: "Temperatura pokojowa nocna", unit: "°C", div: 10, min: 100, max: 350 },
  { id: 52, key: "PARAM_CHARAKTER_DMUCHAWY", group: "extended", name: "Charakterystyka dmuchawy", unit: "", div: 1, min: 0, max: 10 },
  { id: 53, key: "PARAM_MIN_MOC_DMUCH_SERWIS", group: "extended", name: "Minimalna moc dmuchawy serwis", unit: "%", div: 1, min: 1, max: 50 },
  { id: 54, key: "PARAM_MAX_MOC_DMUCH_SERWIS", group: "extended", name: "Maksymalna moc dmuchawy serwis", unit: "%", div: 1, min: 50, max: 100 },
  { id: 55, key: "PARAM_MOC_DMUCH_MIN1", group: "extended", name: "Moc dmuchawy min 1", unit: "%", div: 1, min: 1, max: 50 },
  { id: 56, key: "PARAM_MOC_DMUCH_START", group: "extended", name: "Moc dmuchawy start", unit: "%", div: 1, min: 1, max: 100 },
  { id: 57, key: "PARAM_MOC_DMUCH_DOPAL", group: "extended", name: "Moc dmuchawy dopalanie", unit: "%", div: 1, min: 1, max: 100 },
  { id: 58, key: "PARAM_PODAWANIE_POD_START", group: "extended", name: "Podawanie podajnika start", unit: "s", div: 1, min: 1, max: 60 },
  { id: 59, key: "PARAM_PODAWANIE_POD_2", group: "extended", name: "Podawanie podajnika 2", unit: "s", div: 1, min: 1, max: 60 },
  { id: 60, key: "PARAM_MIN_PODAWANIE_POD", group: "extended", name: "Minimalne podawanie podajnika", unit: "s", div: 1, min: 1, max: 60 },
  { id: 61, key: "PARAM_MAX_PODAWANIE_POD", group: "extended", name: "Maksymalne podawanie podajnika", unit: "s", div: 1, min: 1, max: 60 },
  { id: 76, key: "PARAM_AUTOLATO", group: "extended", name: "Funkcja Auto-Lato", unit: "", div: 1, min: 0, max: 1 },
  { id: 78, key: "PARAM_WEW_ZADAWANIE", group: "extended", name: "Zadawanie temperatury wewnętrznej", unit: "", div: 1, min: 0, max: 2 },
  { id: 80, key: "PARAM_REG_POK_HISTEREZA", group: "extended", name: "Histereza regulatora pokojowego", unit: "°C", div: 10, min: 1, max: 20 },
  { id: 82, key: "PARAM_CZASPRACY_GRZANIE", group: "extended", name: "Czas pracy podajnika w grzaniu 2", unit: "s", div: 1, min: 1, max: 60 },
  { id: 84, key: "PARAM_PODL_DZIENNA", group: "extended", name: "Temperatura dzienna podłogówki", unit: "°C", div: 10, min: 150, max: 500 },
  { id: 85, key: "PARAM_PODL_NOCNA", group: "extended", name: "Temperatura nocna podłogówki", unit: "°C", div: 10, min: 150, max: 500 },
  { id: 86, key: "PARAM_PODL_HISTEREZA", group: "extended", name: "Histereza podłogówki", unit: "°C", div: 10, min: 1, max: 50 },
  { id: 113, key: "PARAM_TEMP_ZAL_CYRK", group: "extended", name: "Temperatura załączenia cyrkulacji CWU", unit: "°C", div: 1, min: 30, max: 60 },
  { id: 114, key: "PARAM_PRACA_AUTO_CYRK", group: "extended", name: "Praca automatyczna cyrkulacji CWU", unit: "", div: 1, min: 0, max: 1 },
  { id: 116, key: "PARAM_PODLOGOWA_CZASPRACY", group: "extended", name: "Czas pracy pompy podłogowej", unit: "s", div: 1, min: 1, max: 60 },
  { id: 117, key: "PARAM_PODLOGOWA_POSTOJ", group: "extended", name: "Czas postoju pompy podłogowej", unit: "min", div: 1, min: 1, max: 60 },
  { id: 123, key: "PARAM_PRACA_POMPCOPODL", group: "extended", name: "Czas pracy pompy CO przy pracy podłogówki", unit: "s", div: 1, min: 1, max: 60 },
  { id: 124, key: "PARAM_POSTOJ_POMPCOPODL", group: "extended", name: "Czas postoju pompy CO przy pracy podłogówki", unit: "min", div: 1, min: 1, max: 60 },
];
