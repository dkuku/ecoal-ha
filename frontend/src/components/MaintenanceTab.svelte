<script>
  import ConfirmModal from './ConfirmModal.svelte';

  let {
    status = {},
    hopperCapacity = 100,
    client = null,
    showToast = () => {},
  } = $props();

  // Fuel data
  let fuelPct = $derived(status?.fuel_load_pct ?? 0);
  let fuelKg = $derived(
    status?.fuel_remaining_kg != null
      ? status.fuel_remaining_kg
      : Math.round((hopperCapacity * fuelPct) / 100)
  );

  let fuelKgDisplay = $derived.by(() => {
    if (fuelKg == null) return '--';
    const val = Number(fuelKg);
    return isNaN(val) ? String(fuelKg) : (Number.isInteger(val) ? val.toString() : val.toFixed(1));
  });

  let estimatedEmptyDisplay = $derived.by(() => {
    if (!status?.estimated_empty_date) return null;
    try {
      const d = new Date(status.estimated_empty_date);
      if (isNaN(d.getTime())) return null;
      const day = d.getDate().toString().padStart(2, '0');
      const month = (d.getMonth() + 1).toString().padStart(2, '0');
      const hour = d.getHours().toString().padStart(2, '0');
      const min = d.getMinutes().toString().padStart(2, '0');
      return `${day}.${month} ${hour}:${min}`;
    } catch {
      return null;
    }
  });

  let feederRuntimeDisplay = $derived.by(() => {
    const mins = status?.feeder_runtime_min ?? (status?.feeder_runtime ?? 0);
    const hours = Math.floor(mins / 60);
    const remMins = Math.round(mins % 60);
    return `${hours}h ${remMins}m`;
  });

  // Maintenance & Cleaning data
  let maintenance = $derived(status?.maintenance || {});
  let daysSinceCleaning = $derived(status?.days_since_cleaning ?? maintenance?.days_since_cleaning ?? 0);
  let coalBurnedSinceCleaning = $derived(status?.coal_burned_since_cleaning_kg ?? maintenance?.coal_burned_since_cleaning_kg ?? 0.0);
  let heatingRate = $derived(status?.heating_rate_c_per_min ?? maintenance?.heating_rate_c_per_min);
  let avgExhaustHeating = $derived(maintenance?.avg_exhaust_heating);
  let cleaningRequired = $derived(Boolean(status?.cleaning_required ?? maintenance?.cleaning_required));
  let cleaningWarningReason = $derived(status?.cleaning_warning_reason || maintenance?.cleaning_warning_reason);

  function formatCleaningDate(isoStr) {
    if (!isoStr) return 'Brak wpisu';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return 'Brak wpisu';
      const day = d.getDate().toString().padStart(2, '0');
      const mon = (d.getMonth() + 1).toString().padStart(2, '0');
      const h = d.getHours().toString().padStart(2, '0');
      const min = d.getMinutes().toString().padStart(2, '0');
      return `${day}.${mon}.${d.getFullYear()} ${h}:${min}`;
    } catch {
      return 'Brak wpisu';
    }
  }

  // Legionella data
  let legionella = $derived(status?.legionella || {});
  let isLegionellaActive = $derived(Boolean(legionella?.active));
  let legionellaPhase = $derived(legionella?.phase || 'idle');
  let legionellaSecondsLeft = $derived(legionella?.holding_seconds_left ?? 1800);

  let legionellaTimerDisplay = $derived.by(() => {
    const total = Math.max(0, legionellaSecondsLeft);
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  });

  function formatLegionellaDate(isoStr) {
    if (!isoStr) return 'Brak danych';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return 'Brak danych';
      const day = d.getDate().toString().padStart(2, '0');
      const mon = (d.getMonth() + 1).toString().padStart(2, '0');
      const h = d.getHours().toString().padStart(2, '0');
      const min = d.getMinutes().toString().padStart(2, '0');
      return `${day}.${mon} ${h}:${min}`;
    } catch {
      return 'Brak danych';
    }
  }

  // Confirmation Modal State
  let modalOpen = $state(false);
  let modalTitle = $state('');
  let modalMessage = $state('');
  let modalConfirmText = $state('Potwierdź');
  let modalIcon = $state('⚠️');
  let modalDanger = $state(true);
  let pendingAction = $state(null);
  let isExecuting = $state(false);

  function openConfirm(options, actionFn) {
    modalTitle = options.title || 'Potwierdzenie operacji';
    modalMessage = options.message || 'Czy na pewno chcesz wykonać tę akcję?';
    modalConfirmText = options.confirmText || 'Potwierdź';
    modalIcon = options.icon || '⚠️';
    modalDanger = options.danger !== false;
    pendingAction = actionFn;
    modalOpen = true;
  }

  function handleCancelModal() {
    modalOpen = false;
    pendingAction = null;
  }

  async function handleConfirmModal() {
    if (!pendingAction || isExecuting) return;
    isExecuting = true;
    try {
      await pendingAction();
    } catch (err) {
      showToast(`Błąd: ${err.message}`, 'error');
    } finally {
      isExecuting = false;
      modalOpen = false;
      pendingAction = null;
    }
  }

  // Action Handlers with Confirmation Modals

  function confirmRefillFull() {
    openConfirm(
      {
        title: 'Zasyp do pełna (100 kg)',
        message: 'Czy na pewno zasypano zasobnik do pełna (100 kg / 4 worki)? Spowoduje to wyzerowanie licznika czasu pracy podajnika od ostatniego zasypu i ustawi wskaźnik opału na 100%.',
        confirmText: 'Tak, zresetuj zasobnik',
        icon: '⛽',
        danger: true,
      },
      async () => {
        const ok = await client.refillHopper(hopperCapacity);
        if (ok) {
          showToast(`Zresetowano zasobnik do pełna (${hopperCapacity} kg)`, 'success');
        } else {
          showToast('Błąd resetowania licznika zasypu', 'error');
        }
      }
    );
  }

  function confirmRecordCleaning() {
    openConfirm(
      {
        title: 'Potwierdzenie czyszczenia kotła',
        message: 'Czy na pewno wyczyszczono wymiennik kotła? Spowoduje to zapisanie dzisiejszej daty jako daty czyszczenia oraz wyzerowanie licznika spalonego węgla od czyszczenia.',
        confirmText: 'Tak, oznacz jako wyczyszczony',
        icon: '🧹',
        danger: true,
      },
      async () => {
        const ok = await client.recordCleaning();
        if (ok) {
          showToast('Zapisano czyszczenie kotła i wyzerowano licznik spalonego węgla', 'success');
        } else {
          showToast('Błąd zapisu czyszczenia', 'error');
        }
      }
    );
  }

  // Edit Cleaning Modal State
  let editCleaningModalOpen = $state(false);
  let inputCleaningDate = $state('');
  let inputCleaningCoal = $state(0.0);

  function openEditCleaningModal() {
    let initialIso = maintenance?.last_cleaned_at;
    if (initialIso) {
      try {
        const d = new Date(initialIso);
        inputCleaningDate = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
      } catch {
        inputCleaningDate = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
      }
    } else {
      inputCleaningDate = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    }
    inputCleaningCoal = Number(coalBurnedSinceCleaning) || 0.0;
    editCleaningModalOpen = true;
  }

  async function handleSaveCleaningModal() {
    if (!inputCleaningDate) return;
    try {
      const iso = new Date(inputCleaningDate).toISOString();
      const ok = await client.setCleaningDate(iso, inputCleaningCoal);
      if (ok) {
        showToast('Zapisano datę czyszczenia i stan spalonego węgla na stałe', 'success');
        editCleaningModalOpen = false;
      } else {
        showToast('Błąd zapisu danych czyszczenia', 'error');
      }
    } catch (e) {
      showToast(`Błąd: ${e.message}`, 'error');
    }
  }

  // Edit Legionella Modal State
  let editLegionellaModalOpen = $state(false);
  let inputLegionellaDate = $state('');

  function openEditLegionellaModal() {
    let initialIso = legionella?.last_run;
    if (initialIso) {
      try {
        const d = new Date(initialIso);
        inputLegionellaDate = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
      } catch {
        inputLegionellaDate = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
      }
    } else {
      inputLegionellaDate = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    }
    editLegionellaModalOpen = true;
  }

  async function handleSaveLegionellaModal() {
    if (!inputLegionellaDate) return;
    try {
      const iso = new Date(inputLegionellaDate).toISOString();
      const ok = await client.setLegionellaDate(iso);
      if (ok) {
        showToast('Zapisano datę ostatniej dezynfekcji na stałe', 'success');
        editLegionellaModalOpen = false;
      } else {
        showToast('Błąd zapisu daty dezynfekcji', 'error');
      }
    } catch (e) {
      showToast(`Błąd: ${e.message}`, 'error');
    }
  }

  function confirmExtinguish() {
    openConfirm(
      {
        title: 'Bezpieczne wygaszenie kotła',
        message: 'Czy na pewno chcesz bezpiecznie wygasić kocioł? Wyłączy to tryb AUTO (zatrzyma podajnik i dmuchawę). Pompa CO pozostanie włączona, dopóki woda w kotle nie ostygnie poniżej 40°C, po czym wyłączy się automatycznie.',
        confirmText: 'Tak, wygaś kocioł',
        icon: '❄️',
        danger: true,
      },
      async () => {
        const ok = await client.extinguishFurnace();
        if (ok) {
          showToast('Rozpoczęto bezpieczne wygaszanie kotła (ochrona pompy aktywna)', 'info');
        } else {
          showToast('Błąd procedury wygaszania', 'error');
        }
      }
    );
  }

  function confirmResumeAuto() {
    openConfirm(
      {
        title: 'Wznowienie trybu automatycznego',
        message: 'Czy na pewno chcesz przywrócić tryb automatyczny (AUTO)? Kocioł podejmie automatyczną pracę wg wybranego algorytmu podawania i dmuchawy.',
        confirmText: 'Wznów tryb AUTO',
        icon: '🔥',
        danger: false,
      },
      async () => {
        const ok = await client.setAutoMode(true);
        if (ok) {
          showToast('Wznowiono automatyczną pracę kotła (Tryb AUTO aktywny)', 'success');
        } else {
          showToast('Błąd włączania trybu AUTO', 'error');
        }
      }
    );
  }

  function confirmStartLegionella() {
    openConfirm(
      {
        title: 'Dezynfekcja termiczna Legionella',
        message: 'Czy na pewno chcesz uruchomić termiczną dezynfekcję bojlera CWU? Kocioł podniesie temperaturę CWU do 60°C (CO do 65°C) i utrzyma ją przez 30 minut, po czym automatycznie powróci do poprzednich nastaw.',
        confirmText: 'Uruchom dezynfekcję (60°C)',
        icon: '🦠',
        danger: true,
      },
      async () => {
        const ok = await client.startLegionella(30);
        if (ok) {
          showToast('Uruchomiono dezynfekcję termiczną CWU', 'success');
        } else {
          showToast('Błąd uruchamiania dezynfekcji', 'error');
        }
      }
    );
  }

  function confirmStopLegionella() {
    openConfirm(
      {
        title: 'Przerwanie dezynfekcji termicznej',
        message: 'Czy chcesz natychmiast przerwać cykl dezynfekcji i przywrócić standardowe temperatury zadane?',
        confirmText: 'Przerwij dezynfekcję',
        icon: '⏹',
        danger: false,
      },
      async () => {
        const ok = await client.stopLegionella();
        if (ok) {
          showToast('Zatrzymano dezynfekcję i przywrócono nastawy', 'info');
        } else {
          showToast('Błąd zatrzymywania dezynfekcji', 'error');
        }
      }
    );
  }

  async function handleAckAlarms() {
    try {
      const ok = await client.ackAlarms();
      if (ok) {
        showToast('Skasowano aktywne alarmy sterownika', 'success');
      } else {
        showToast('Błąd kasowania alarmów', 'error');
      }
    } catch (err) {
      showToast(`Błąd: ${err.message}`, 'error');
    }
  }

  async function handleSyncClock() {
    try {
      const ok = await client.syncClock();
      if (ok) {
        showToast('Zsynchronizowano zegar sterownika z czasem Home Assistant', 'success');
      } else {
        showToast('Błąd synchronizacji zegara sterownika', 'error');
      }
    } catch (err) {
      showToast(`Błąd: ${err.message}`, 'error');
    }
  }

  async function handleForceCo(lowered, hours = 2) {
    try {
      const ok = await client.forceCoMode(lowered, hours);
      if (ok) {
        showToast(
          lowered
            ? `Wymuszono temperaturę obniżoną CO na ${hours}h`
            : `Wymuszono temperaturę komfortową CO na ${hours}h`,
          'success'
        );
      } else {
        showToast('Błąd wymuszenia harmonogramu', 'error');
      }
    } catch (err) {
      showToast(`Błąd: ${err.message}`, 'error');
    }
  }
</script>

<div class="maintenance-view">
  <div class="maintenance-header">
    <h2>🛠️ Panel Obsługi & Konserwacji Kotła</h2>
    <p class="section-desc">
      Zarządzanie paliwem, rejestracja czyszczenia wymiennika, bezpieczne wygaszanie oraz procedury serwisowe.
    </p>
  </div>

  <div class="maintenance-grid">
    <!-- Card 1: Fuel & Hopper Management -->
    <div class="maint-card">
      <div class="maint-card-header">
        <span class="maint-card-icon">⛽</span>
        <div>
          <h3 class="maint-card-title">Zasyp Opału & Zasobnik</h3>
          <span class="maint-card-subtitle">Pojemność robocza: {hopperCapacity} kg (4 worki)</span>
        </div>
      </div>

      <div class="fuel-level-box">
        <div class="fuel-gauge-row">
          <span class="fuel-val-large">{fuelKgDisplay} kg</span>
          <span class="fuel-pct-badge" class:low={fuelPct < 25} class:med={fuelPct >= 25 && fuelPct < 50}>
            {fuelPct}%
          </span>
        </div>
        <div class="fuel-progress-bar">
          <div
            class="fuel-progress-fill"
            class:low={fuelPct < 25}
            class:med={fuelPct >= 25 && fuelPct < 50}
            style="width: {Math.max(4, Math.min(100, fuelPct))}%;"
          ></div>
        </div>
        <div class="fuel-details-row">
          <span>Ślimak: <strong>{feederRuntimeDisplay}</strong></span>
          <span>
            Pusty za: <strong>{estimatedEmptyDisplay ? estimatedEmptyDisplay : '--'}</strong>
          </span>
        </div>
      </div>

      <div class="maint-actions-column">
        <button
          type="button"
          class="btn-maint btn-refill"
          onclick={confirmRefillFull}
          title="Wymaga potwierdzenia: zeruje licznik czasu ślimaka i ustawia poziom na 100%"
        >
          <span class="btn-icon">⛽</span>
          <span class="btn-title">Zasypano do pełna ({hopperCapacity} kg)</span>
        </button>
      </div>
    </div>

    <!-- Card 2: Heat Exchanger Cleaning -->
    <div class="maint-card">
      <div class="maint-card-header">
        <span class="maint-card-icon">🧹</span>
        <div>
          <h3 class="maint-card-title">Czyszczenie Wymiennika</h3>
          <span class="maint-card-subtitle">Monitoring sprawności i czystości kanałów spalinowych</span>
        </div>
      </div>

      <div class="clean-status-box">
        {#if cleaningRequired}
          <div class="clean-badge warn">
            ⚠️ Wymagane czyszczenie wymiennika!
          </div>
          {#if cleaningWarningReason}
            <div class="clean-reason">{cleaningWarningReason}</div>
          {/if}
        {:else}
          <div class="clean-badge ok">
            ✓ Wymiennik czysty
          </div>
        {/if}

        <div class="clean-metrics-grid">
          <div class="clean-stat">
            <span class="stat-lbl">Dni od czyszczenia</span>
            <span class="stat-val">{daysSinceCleaning} d</span>
          </div>
          <div class="clean-stat">
            <span class="stat-lbl">Spalony węgiel</span>
            <span class="stat-val">{coalBurnedSinceCleaning} kg</span>
          </div>
          <div class="clean-stat">
            <span class="stat-lbl">Śr. spaliny (grzanie)</span>
            <span class="stat-val">
              {avgExhaustHeating != null ? avgExhaustHeating.toFixed(1) + '°C' : '--'}
            </span>
          </div>
          <div class="clean-stat">
            <span class="stat-lbl">Tempo nagrzewania</span>
            <span class="stat-val">
              {heatingRate != null ? heatingRate.toFixed(2) : '--'}
              <small>°C/min</small>
            </span>
          </div>
        </div>

        <div class="clean-last-date">
          Ostatnie czyszczenie: <strong>{formatCleaningDate(maintenance.last_cleaned_at)}</strong>
        </div>
      </div>

      <div class="maint-actions-column">
        <button
          type="button"
          class="btn-maint btn-clean"
          onclick={confirmRecordCleaning}
          title="Wymaga potwierdzenia: zapisuje datę i resetuje licznik spalonego opału"
        >
          <span class="btn-icon">🧹</span>
          <span class="btn-title">Oznacz wyczyszczenie kotła</span>
        </button>
        <button
          type="button"
          class="btn-maint"
          style="background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.35); color: #60a5fa; margin-top: 0.5rem;"
          onclick={openEditCleaningModal}
          title="Ustaw ręcznie datę ostatniego czyszczenia lub skoryguj licznik spalonego węgla"
        >
          <span class="btn-icon">📅</span>
          <span class="btn-title">Koryguj datę / węgiel</span>
        </button>
      </div>
    </div>

    <!-- Card 3: Safe Extinguish & Auto Mode -->
    <div class="maint-card">
      <div class="maint-card-header">
        <span class="maint-card-icon">❄️</span>
        <div>
          <h3 class="maint-card-title">Bezpieczne Wygaszenie / Postój</h3>
          <span class="maint-card-subtitle">Zatrzymanie palnika z automatyczną ochroną pompy CO</span>
        </div>
      </div>

      <div class="extinguish-info-box">
        <div class="extinguish-state-row">
          <span>Stan pracy:</span>
          {#if status?.auto_mode}
            <span class="badge-status-auto">🔥 Tryb AUTO aktywny</span>
          {:else}
            <span class="badge-status-manual">❄️ Kocioł zatrzymany (Manual)</span>
          {/if}
        </div>
        <p class="extinguish-hint">
          Bezpieczne wygaszenie zatrzymuje podajnik i dmuchawę. Pompa CO pracuje do momentu schłodzenia kotła poniżej 40°C, po czym wyłącza się automatycznie.
        </p>
      </div>

      <div class="maint-actions-row">
        {#if status?.auto_mode}
          <button
            type="button"
            class="btn-maint btn-extinguish"
            onclick={confirmExtinguish}
            title="Wymaga potwierdzenia: zatrzymuje kocioł"
          >
            <span class="btn-icon">❄️</span>
            <span class="btn-title">Bezpiecznie wygaś kocioł</span>
          </button>
        {:else}
          <button
            type="button"
            class="btn-maint btn-resume-auto"
            onclick={confirmResumeAuto}
            title="Wymaga potwierdzenia: wznawia automatyczną pracę"
          >
            <span class="btn-icon">🔥</span>
            <span class="btn-title">Wznów tryb AUTO</span>
          </button>
        {/if}
      </div>
    </div>

    <!-- Card 4: Thermal Disinfection (Anti-Legionella) -->
    <div class="maint-card">
      <div class="maint-card-header">
        <span class="maint-card-icon">🛡️</span>
        <div>
          <h3 class="maint-card-title">Dezynfekcja Termiczna (CWU)</h3>
          <span class="maint-card-subtitle">30-minutowe wygrzanie bojlera do 60°C (CO do 65°C)</span>
        </div>
      </div>

      <div class="legionella-box">
        <div class="legionella-row">
          <span>Status cyklu:</span>
          {#if isLegionellaActive}
            <span class="badge-legionella-active">
              {legionellaPhase === 'heating' ? '⏳ Nagrzewanie do 60°C' : `Wygrzewanie: ${legionellaTimerDisplay}`}
            </span>
          {:else}
            <span class="badge-legionella-idle">Gotowy (Bezczynny)</span>
          {/if}
        </div>

        {#if isLegionellaActive && legionellaPhase === 'holding'}
          <div class="legionella-timer-banner">
            <span class="timer-digits">{legionellaTimerDisplay}</span>
            <span class="timer-sub">pozostało do zakończenia</span>
          </div>
        {/if}

        <div class="legionella-last-run" style="display: flex; justify-content: space-between; align-items: center;">
          <span>Ostatnia dezynfekcja: <strong>{formatLegionellaDate(legionella?.last_run)}</strong></span>
          <button
            type="button"
            onclick={openEditLegionellaModal}
            style="background: rgba(148, 163, 184, 0.12); border: 1px solid rgba(148, 163, 184, 0.3); border-radius: 4px; color: #cbd5e1; cursor: pointer; padding: 2px 7px; font-size: 0.75rem;"
            title="Ustaw datę ostatniej udanej dezynfekcji termicznej"
          >
            ✏️ Koryguj datę
          </button>
        </div>
      </div>

      <div class="maint-actions-row">
        {#if isLegionellaActive}
          <button
            type="button"
            class="btn-maint btn-stop-legionella"
            onclick={confirmStopLegionella}
          >
            <span class="btn-icon">⏹</span>
            <span class="btn-title">Przerwij dezynfekcję</span>
          </button>
        {:else}
          <button
            type="button"
            class="btn-maint btn-start-legionella"
            onclick={confirmStartLegionella}
            title="Wymaga potwierdzenia: uruchamia wygrzewanie 60°C"
          >
            <span class="btn-icon">🦠</span>
            <span class="btn-title">Uruchom dezynfekcję (60°C)</span>
          </button>
        {/if}
      </div>
    </div>

    <!-- Card 5: Quick Schedule Overrides -->
    <div class="maint-card">
      <div class="maint-card-header">
        <span class="maint-card-icon">🌙</span>
        <div>
          <h3 class="maint-card-title">Szybkie Wymuszenia Harmonogramu</h3>
          <span class="maint-card-subtitle">Tymczasowa zmiana temperatury CO na 2 godziny</span>
        </div>
      </div>

      <p class="override-desc">
        Wymusza temperaturę bez modyfikacji stałego harmonogramu tygodniowego. Po 2 godzinach kocioł wraca do normalnego programu.
      </p>

      <div class="maint-actions-row">
        <button
          type="button"
          class="btn-maint btn-force-low"
          onclick={() => handleForceCo(true, 2)}
        >
          <span class="btn-icon">🌙</span>
          <span class="btn-title">Wymuś obniżenie (2h)</span>
        </button>
        <button
          type="button"
          class="btn-maint btn-force-comf"
          onclick={() => handleForceCo(false, 2)}
        >
          <span class="btn-icon">☀️</span>
          <span class="btn-title">Wymuś komfort (2h)</span>
        </button>
      </div>
    </div>

    <!-- Card 6: Diagnostics & Controller Utilities -->
    <div class="maint-card">
      <div class="maint-card-header">
        <span class="maint-card-icon">🔔</span>
        <div>
          <h3 class="maint-card-title">Sterownik & Diagnostyka</h3>
          <span class="maint-card-subtitle">Kasowanie alarmów i synchronizacja zegara</span>
        </div>
      </div>

      <div class="diag-status-row">
        <span>Alarmy sterownika:</span>
        {#if status?.alarm_active}
          <span class="badge-alarm-on">⚠️ AKTYWNY ALARM</span>
        {:else}
          <span class="badge-alarm-off">✓ Brak alarmów</span>
        {/if}
      </div>

      <div class="maint-actions-row">
        <button
          type="button"
          class="btn-maint btn-ack-alarms"
          onclick={handleAckAlarms}
        >
          <span class="btn-icon">🔕</span>
          <span class="btn-title">Kasuj / Potwierdź alarmy</span>
        </button>
        <button
          type="button"
          class="btn-maint btn-sync-clock"
          onclick={handleSyncClock}
        >
          <span class="btn-icon">🕒</span>
          <span class="btn-title">Synchronizuj zegar</span>
        </button>
      </div>
    </div>
  </div>
</div>

<!-- Dedicated Confirmation Modal -->
<ConfirmModal
  open={modalOpen}
  title={modalTitle}
  message={modalMessage}
  confirmText={modalConfirmText}
  icon={modalIcon}
  danger={modalDanger}
  onConfirm={handleConfirmModal}
  onCancel={handleCancelModal}
/>

{#if editCleaningModalOpen}
  <div class="modal-backdrop" onclick={() => (editCleaningModalOpen = false)} role="presentation">
    <div class="modal-card" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()} role="dialog" aria-modal="true" tabindex="-1">
      <div class="modal-header">
        <span class="modal-icon">🧹</span>
        <h3 class="modal-title">Korekta Historii Czyszczenia Kotła</h3>
      </div>
      <div class="modal-body" style="display: flex; flex-direction: column; gap: 1rem;">
        <div>
          <label for="cleaningDateInput" style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.35rem;">
            Data i godzina ostatniego czyszczenia:
          </label>
          <input
            id="cleaningDateInput"
            type="datetime-local"
            bind:value={inputCleaningDate}
            style="width: 100%; padding: 0.55rem; background: rgba(15, 23, 42, 0.8); border: 1px solid var(--border-color); border-radius: 6px; color: #f8fafc;"
          />
        </div>
        <div>
          <label for="cleaningCoalInput" style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.35rem;">
            Spalony węgiel od czyszczenia [kg]:
          </label>
          <input
            id="cleaningCoalInput"
            type="number"
            step="0.1"
            min="0"
            bind:value={inputCleaningCoal}
            style="width: 100%; padding: 0.55rem; background: rgba(15, 23, 42, 0.8); border: 1px solid var(--border-color); border-radius: 6px; color: #f8fafc;"
          />
        </div>
        <p style="font-size: 0.78rem; color: var(--text-muted); margin: 0;">
          Wartości zostaną zapisane w trwałym magazynie Home Assistant (.storage) i przetrwają restarty oraz zaniki zasilania.
        </p>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn-modal-cancel" onclick={() => (editCleaningModalOpen = false)}>
          Anuluj
        </button>
        <button type="button" class="btn-modal-confirm" style="background: #3b82f6;" onclick={handleSaveCleaningModal}>
          💾 Zapisz na stałe
        </button>
      </div>
    </div>
  </div>
{/if}

{#if editLegionellaModalOpen}
  <div class="modal-backdrop" onclick={() => (editLegionellaModalOpen = false)} role="presentation">
    <div class="modal-card" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()} role="dialog" aria-modal="true" tabindex="-1">
      <div class="modal-header">
        <span class="modal-icon">🦠</span>
        <h3 class="modal-title">Data Ostatniej Dezynfekcji Legionella</h3>
      </div>
      <div class="modal-body" style="display: flex; flex-direction: column; gap: 1rem;">
        <div>
          <label for="legionellaDateInput" style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.35rem;">
            Data i godzina ostatniego wygrzania bojlera (60°C):
          </label>
          <input
            id="legionellaDateInput"
            type="datetime-local"
            bind:value={inputLegionellaDate}
            style="width: 100%; padding: 0.55rem; background: rgba(15, 23, 42, 0.8); border: 1px solid var(--border-color); border-radius: 6px; color: #f8fafc;"
          />
        </div>
        <p style="font-size: 0.78rem; color: var(--text-muted); margin: 0;">
          Zapisuje datę do trwałej pamięci (.storage). Nie uruchamia grzania bojlera.
        </p>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn-modal-cancel" onclick={() => (editLegionellaModalOpen = false)}>
          Anuluj
        </button>
        <button type="button" class="btn-modal-confirm" style="background: #0ea5e9;" onclick={handleSaveLegionellaModal}>
          💾 Zapisz na stałe
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .maintenance-view {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem 0;
  }

  .maintenance-header {
    margin-bottom: 1.5rem;
  }

  .maintenance-header h2 {
    font-size: 1.45rem;
    font-weight: 700;
    color: #f8fafc;
    margin: 0 0 0.35rem 0;
  }

  .section-desc {
    font-size: 0.88rem;
    color: var(--text-muted);
    margin: 0;
  }

  .maintenance-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
    gap: 1.25rem;
  }

  .maint-card {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: var(--shadow-sm);
    transition: var(--transition);
  }

  .maint-card:hover {
    border-color: rgba(255, 255, 255, 0.15);
  }

  .maint-card-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    padding-bottom: 0.75rem;
  }

  .maint-card-icon {
    font-size: 1.8rem;
    line-height: 1;
  }

  .maint-card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #f8fafc;
    margin: 0;
  }

  .maint-card-subtitle {
    font-size: 0.75rem;
    color: var(--text-muted);
    display: block;
  }

  /* Fuel level box */
  .fuel-level-box {
    background: rgba(15, 23, 42, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: var(--radius-sm);
    padding: 0.85rem;
    margin-bottom: 1rem;
  }

  .fuel-gauge-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .fuel-val-large {
    font-size: 1.5rem;
    font-weight: 700;
    color: #f8fafc;
  }

  .fuel-pct-badge {
    background: rgba(16, 185, 129, 0.2);
    color: #6ee7b7;
    border: 1px solid rgba(16, 185, 129, 0.4);
    border-radius: var(--radius-sm);
    padding: 0.2rem 0.5rem;
    font-weight: 700;
    font-size: 0.82rem;
  }

  .fuel-pct-badge.med {
    background: rgba(245, 158, 11, 0.2);
    color: #fcd34d;
    border-color: rgba(245, 158, 11, 0.4);
  }

  .fuel-pct-badge.low {
    background: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
    border-color: rgba(239, 68, 68, 0.4);
  }

  .fuel-progress-bar {
    height: 10px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 5px;
    overflow: hidden;
    margin-bottom: 0.65rem;
  }

  .fuel-progress-fill {
    height: 100%;
    background: #10b981;
    border-radius: 5px;
    transition: width 0.3s ease;
  }

  .fuel-progress-fill.med {
    background: #f59e0b;
  }

  .fuel-progress-fill.low {
    background: #ef4444;
  }

  .fuel-details-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.78rem;
    color: var(--text-muted);
  }

  .fuel-details-row strong {
    color: #e2e8f0;
  }

  /* Cleaning styles */
  .clean-status-box {
    background: rgba(15, 23, 42, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: var(--radius-sm);
    padding: 0.85rem;
    margin-bottom: 1rem;
  }

  .clean-badge {
    text-align: center;
    padding: 0.3rem 0.6rem;
    border-radius: var(--radius-sm);
    font-size: 0.82rem;
    font-weight: 700;
    margin-bottom: 0.65rem;
  }

  .clean-badge.ok {
    background: rgba(16, 185, 129, 0.15);
    color: #6ee7b7;
    border: 1px solid rgba(16, 185, 129, 0.35);
  }

  .clean-badge.warn {
    background: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.5);
    animation: pulse-glow 2s infinite ease-in-out;
  }

  .clean-reason {
    font-size: 0.74rem;
    color: #fca5a5;
    background: rgba(239, 68, 68, 0.1);
    padding: 0.3rem 0.5rem;
    border-radius: var(--radius-sm);
    margin-bottom: 0.65rem;
  }

  .clean-metrics-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.5rem;
    margin-bottom: 0.65rem;
  }

  .clean-stat {
    background: rgba(0, 0, 0, 0.25);
    padding: 0.45rem;
    border-radius: var(--radius-sm);
    text-align: center;
  }

  .stat-lbl {
    font-size: 0.68rem;
    color: var(--text-muted);
    display: block;
  }

  .stat-val {
    font-size: 1.05rem;
    font-weight: 700;
    color: #f8fafc;
  }

  .clean-last-date {
    font-size: 0.72rem;
    color: var(--text-muted);
    text-align: center;
  }

  .clean-last-date strong {
    color: #e2e8f0;
  }

  /* Extinguish styles */
  .extinguish-info-box {
    background: rgba(15, 23, 42, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: var(--radius-sm);
    padding: 0.85rem;
    margin-bottom: 1rem;
  }

  .extinguish-state-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.82rem;
    color: #cbd5e1;
    margin-bottom: 0.5rem;
  }

  .badge-status-auto {
    background: rgba(16, 185, 129, 0.15);
    color: #6ee7b7;
    border: 1px solid rgba(16, 185, 129, 0.35);
    padding: 0.2rem 0.55rem;
    border-radius: var(--radius-sm);
    font-size: 0.75rem;
    font-weight: 600;
  }

  .badge-status-manual {
    background: rgba(59, 130, 246, 0.15);
    color: #93c5fd;
    border: 1px solid rgba(59, 130, 246, 0.35);
    padding: 0.2rem 0.55rem;
    border-radius: var(--radius-sm);
    font-size: 0.75rem;
    font-weight: 600;
  }

  .extinguish-hint {
    font-size: 0.75rem;
    color: var(--text-muted);
    line-height: 1.45;
    margin: 0;
  }

  /* Legionella box */
  .legionella-box {
    background: rgba(15, 23, 42, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: var(--radius-sm);
    padding: 0.85rem;
    margin-bottom: 1rem;
  }

  .legionella-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.82rem;
    color: #cbd5e1;
    margin-bottom: 0.5rem;
  }

  .badge-legionella-active {
    background: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.4);
    padding: 0.2rem 0.55rem;
    border-radius: var(--radius-sm);
    font-size: 0.75rem;
    font-weight: 600;
    animation: pulse-glow 2s infinite ease-in-out;
  }

  .badge-legionella-idle {
    background: rgba(148, 163, 184, 0.15);
    color: #94a3b8;
    border: 1px solid rgba(148, 163, 184, 0.3);
    padding: 0.2rem 0.55rem;
    border-radius: var(--radius-sm);
    font-size: 0.75rem;
    font-weight: 600;
  }

  .legionella-timer-banner {
    text-align: center;
    background: rgba(220, 38, 38, 0.15);
    border: 1px solid rgba(220, 38, 38, 0.35);
    border-radius: var(--radius-sm);
    padding: 0.65rem;
    margin-bottom: 0.5rem;
  }

  .timer-digits {
    font-size: 1.6rem;
    font-weight: 800;
    font-family: monospace;
    color: #fca5a5;
    display: block;
  }

  .timer-sub {
    font-size: 0.68rem;
    color: var(--text-muted);
  }

  .legionella-last-run {
    font-size: 0.72rem;
    color: var(--text-muted);
    text-align: center;
  }

  .legionella-last-run strong {
    color: #e2e8f0;
  }

  /* Schedule Override */
  .override-desc {
    font-size: 0.78rem;
    color: var(--text-muted);
    line-height: 1.45;
    margin: 0 0 1rem 0;
  }

  /* Diagnostics */
  .diag-status-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.82rem;
    color: #cbd5e1;
    margin-bottom: 1rem;
    background: rgba(15, 23, 42, 0.4);
    padding: 0.65rem 0.85rem;
    border-radius: var(--radius-sm);
  }

  .badge-alarm-on {
    background: rgba(239, 68, 68, 0.25);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.5);
    padding: 0.2rem 0.55rem;
    border-radius: var(--radius-sm);
    font-size: 0.75rem;
    font-weight: 700;
    animation: pulse-glow 1.5s infinite ease-in-out;
  }

  .badge-alarm-off {
    background: rgba(16, 185, 129, 0.15);
    color: #6ee7b7;
    border: 1px solid rgba(16, 185, 129, 0.35);
    padding: 0.2rem 0.55rem;
    border-radius: var(--radius-sm);
    font-size: 0.75rem;
    font-weight: 600;
  }

  /* Buttons & Action Layouts */
  .maint-actions-column {
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
  }

  .maint-actions-row {
    display: flex;
    gap: 0.65rem;
  }

  .btn-maint {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.55rem;
    padding: 0.65rem 0.85rem;
    border-radius: var(--radius-sm);
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: var(--transition);
    border: 1px solid transparent;
  }

  .btn-maint .btn-icon {
    font-size: 1.15rem;
  }

  .btn-refill {
    background: rgba(16, 185, 129, 0.2);
    color: #6ee7b7;
    border-color: rgba(16, 185, 129, 0.4);
  }

  .btn-refill:hover {
    background: rgba(16, 185, 129, 0.32);
    color: #ffffff;
  }

  .btn-clean {
    background: rgba(59, 130, 246, 0.2);
    color: #93c5fd;
    border-color: rgba(59, 130, 246, 0.4);
  }

  .btn-clean:hover {
    background: rgba(59, 130, 246, 0.32);
    color: #ffffff;
  }

  .btn-extinguish {
    background: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
    border-color: rgba(239, 68, 68, 0.4);
  }

  .btn-extinguish:hover {
    background: rgba(239, 68, 68, 0.35);
    color: #ffffff;
  }

  .btn-resume-auto {
    background: rgba(16, 185, 129, 0.2);
    color: #6ee7b7;
    border-color: rgba(16, 185, 129, 0.4);
  }

  .btn-resume-auto:hover {
    background: rgba(16, 185, 129, 0.32);
    color: #ffffff;
  }

  .btn-start-legionella {
    background: rgba(220, 38, 38, 0.2);
    color: #fca5a5;
    border-color: rgba(220, 38, 38, 0.4);
  }

  .btn-start-legionella:hover {
    background: rgba(220, 38, 38, 0.35);
    color: #ffffff;
  }

  .btn-stop-legionella {
    background: rgba(148, 163, 184, 0.2);
    color: #cbd5e1;
    border-color: rgba(148, 163, 184, 0.4);
  }

  .btn-stop-legionella:hover {
    background: rgba(148, 163, 184, 0.32);
    color: #ffffff;
  }

  .btn-force-low {
    background: rgba(59, 130, 246, 0.18);
    color: #93c5fd;
    border-color: rgba(59, 130, 246, 0.35);
  }

  .btn-force-low:hover {
    background: rgba(59, 130, 246, 0.3);
    color: #ffffff;
  }

  .btn-force-comf {
    background: rgba(245, 158, 11, 0.18);
    color: #fcd34d;
    border-color: rgba(245, 158, 11, 0.35);
  }

  .btn-force-comf:hover {
    background: rgba(245, 158, 11, 0.3);
    color: #ffffff;
  }

  .btn-ack-alarms {
    background: rgba(255, 255, 255, 0.08);
    color: #e2e8f0;
    border-color: rgba(255, 255, 255, 0.15);
  }

  .btn-ack-alarms:hover {
    background: rgba(255, 255, 255, 0.16);
    color: #ffffff;
  }

  .btn-sync-clock {
    background: rgba(255, 255, 255, 0.08);
    color: #e2e8f0;
    border-color: rgba(255, 255, 255, 0.15);
  }

  .btn-sync-clock:hover {
    background: rgba(255, 255, 255, 0.16);
    color: #ffffff;
  }

  @keyframes pulse-glow {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.65; }
  }
</style>
