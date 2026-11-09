<script>
  import { onMount } from 'svelte';
  import Schematic from './Schematic.svelte';

  let {
    status = {},
    hopperCapacity = 100,
    client = null,
    showToast = () => {},
    onSelectTab = () => {},
    onStepSetpoint = () => {},
    onRefillHopper = () => {},
    onSetFeederMode = () => {},
    onSetMixerMode = () => {},
  } = $props();

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

  // Determine active control mode: Room regulation (PARAM 78 > 0) vs CO boiler regulation (PARAM 78 == 0)
  let isRoomControlActive = $derived(Boolean((status?.internal_setpoint ?? 0) > 0));

  let userSelectedScheduleId = $state(null);
  let activeScheduleId = $derived(
    userSelectedScheduleId !== null
      ? userSelectedScheduleId
      : (isRoomControlActive ? 27 : 24)
  );

  let currentSchedule = $state(null);
  let isScheduleLoading = $state(false);
  let isForcingMode = $state(false);

  async function loadActiveSchedule() {
    if (!client) return;
    const id = activeScheduleId;
    isScheduleLoading = true;
    try {
      const res = await client.getWeeklyProgram(id);
      if (res && res.length === 7) {
        currentSchedule = res;
      }
    } catch (_) {}
    finally {
      isScheduleLoading = false;
    }
  }

  $effect(() => {
    // Reload whenever active schedule ID changes
    const _id = activeScheduleId;
    loadActiveSchedule();
  });

  onMount(() => {
    loadActiveSchedule();
    const timer = setInterval(loadActiveSchedule, 30000);
    return () => clearInterval(timer);
  });

  async function handleForceMode(lowered, hours = 2) {
    if (!client || isForcingMode) return;
    isForcingMode = true;
    try {
      const ok = await client.forceScheduleMode(activeScheduleId, lowered, hours);
      if (ok) {
        if (activeScheduleId === 27) {
          showToast(
            lowered
              ? `Wymuszono temperaturę nocną w pokoju na ${hours}h`
              : `Wymuszono temperaturę dzienną w pokoju na ${hours}h`,
            'success'
          );
        } else {
          showToast(
            lowered
              ? `Wymuszono obniżenie temperatury CO na ${hours}h`
              : `Wymuszono temperaturę komfortową CO na ${hours}h`,
            'success'
          );
        }
        await loadActiveSchedule();
      } else {
        showToast('Nie udało się zapisać zmiany w sterowniku kotła', 'error');
      }
    } catch (err) {
      showToast(`Błąd: ${err.message}`, 'error');
    } finally {
      isForcingMode = false;
    }
  }

  let isTriggeringLegionella = $state(false);
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
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return '';
      const day = d.getDate().toString().padStart(2, '0');
      const mon = (d.getMonth() + 1).toString().padStart(2, '0');
      const h = d.getHours().toString().padStart(2, '0');
      const min = d.getMinutes().toString().padStart(2, '0');
      return `${day}.${mon} ${h}:${min}`;
    } catch {
      return '';
    }
  }

  async function handleStartLegionella() {
    if (!client || isTriggeringLegionella) return;
    if (!confirm('Czy na pewno chcesz uruchomić dezynfekcję termiczną CWU do 60°C (czas wygrzewania: 30 min)?')) return;
    isTriggeringLegionella = true;
    try {
      const ok = await client.startLegionella(30);
      if (ok) {
        showToast('Uruchomiono dezynfekcję Legionelli (zadana CWU: 60°C, CO: 65°C)', 'success');
      } else {
        showToast('Błąd uruchamiania dezynfekcji termicznej', 'error');
      }
    } catch (err) {
      showToast(`Wyjątek: ${err.message}`, 'error');
    } finally {
      isTriggeringLegionella = false;
    }
  }

  async function handleStopLegionella() {
    if (!client || isTriggeringLegionella) return;
    isTriggeringLegionella = true;
    try {
      const ok = await client.stopLegionella();
      if (ok) {
        showToast('Zatrzymano dezynfekcję termiczną i przywrócono nastawy', 'info');
      } else {
        showToast('Błąd zatrzymywania dezynfekcji', 'error');
      }
    } catch (err) {
      showToast(`Wyjątek: ${err.message}`, 'error');
    } finally {
      isTriggeringLegionella = false;
    }
  }

  // Calculate timeline slots for the next 24 half-hours (12 hours preview)
  let timelineSlots = $derived.by(() => {
    if (!currentSchedule || currentSchedule.length !== 7) return [];
    const now = new Date();
    const curHour = now.getHours();
    const curMin = now.getMinutes();
    const curSlot = curHour * 2 + (curMin >= 30 ? 1 : 0);
    const curDay = now.getDay();

    const slots = [];
    for (let i = 0; i < 24; i++) {
      const targetSlot = (curSlot + i) % 48;
      const targetDay = (curDay + Math.floor((curSlot + i) / 48)) % 7;
      const isComfort = (currentSchedule[targetDay] || '')[targetSlot] === '1';

      const slotHour = Math.floor(targetSlot / 2).toString().padStart(2, '0');
      const slotMin = targetSlot % 2 === 0 ? '00' : '30';

      slots.push({
        index: i,
        time: `${slotHour}:${slotMin}`,
        hour: slotHour,
        minute: slotMin,
        isComfort,
        isCurrent: i === 0,
      });
    }
    return slots;
  });

  let modeRemainingInfo = $derived.by(() => {
    if (!timelineSlots || timelineSlots.length === 0) return null;
    const currentIsComfort = timelineSlots[0].isComfort;
    let consecutiveSlots = 0;
    for (const s of timelineSlots) {
      if (s.isComfort === currentIsComfort) {
        consecutiveSlots++;
      } else {
        break;
      }
    }
    const endSlot = timelineSlots[Math.min(consecutiveSlots, timelineSlots.length - 1)];
    const minsLeft = consecutiveSlots * 30;
    const hoursLeft = Math.floor(minsLeft / 60);
    const remMins = minsLeft % 60;
    const timeStr = `${hoursLeft > 0 ? hoursLeft + 'h ' : ''}${remMins > 0 ? remMins + 'm' : ''}`.trim() || '30m';
    return {
      isComfort: currentIsComfort,
      endTime: endSlot.time,
      timeRemaining: timeStr,
      totalSlots: consecutiveSlots,
    };
  });

  function handleModeChange(e) {
    const val = parseInt(e.target.value, 10);
    onSetFeederMode(val);
  }

  function handleMixerModeChange(e) {
    const val = parseInt(e.target.value, 10);
    onSetMixerMode(val);
  }

  // Maintenance & Cleaning tracker
  let maintenance = $derived(status?.maintenance || {});
  let daysSinceCleaning = $derived(status?.days_since_cleaning ?? maintenance?.days_since_cleaning ?? 0);
  let coalBurnedSinceCleaning = $derived(status?.coal_burned_since_cleaning_kg ?? maintenance?.coal_burned_since_cleaning_kg ?? 0.0);
  let heatingRate = $derived(status?.heating_rate_c_per_min ?? maintenance?.heating_rate_c_per_min);
  let avgExhaustHeating = $derived(maintenance?.avg_exhaust_heating);
  let cleaningRequired = $derived(Boolean(status?.cleaning_required ?? maintenance?.cleaning_required));
  let cleaningWarningReason = $derived(status?.cleaning_warning_reason || maintenance?.cleaning_warning_reason);
  let isRecordingCleaning = $state(false);
  let isExtinguishing = $state(false);

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

  async function handleRecordCleaning() {
    if (!client || isRecordingCleaning) return;
    if (!confirm('Czy na pewno chcesz oznaczyć kocioł jako wyczyszczony? Spowoduje to wyzerowanie licznika spalonego węgla od czyszczenia.')) return;
    isRecordingCleaning = true;
    try {
      const ok = await client.recordCleaning();
      if (ok) {
        showToast('Zapisano czyszczenie kotła i zresetowano licznik spalonego węgla', 'success');
      } else {
        showToast('Błąd zapisu czyszczenia kotła', 'error');
      }
    } catch (err) {
      showToast(`Błąd: ${err.message}`, 'error');
    } finally {
      isRecordingCleaning = false;
    }
  }

  async function handleExtinguish() {
    if (!client || isExtinguishing) return;
    if (!confirm('Czy na pewno chcesz bezpiecznie wygasić kocioł? Wyłączy to tryb AUTO (zatrzyma podajnik i dmuchawę), a pompa CO wyłączy się automatycznie po schłodzeniu do 40°C.')) return;
    isExtinguishing = true;
    try {
      const ok = await client.extinguishFurnace();
      if (ok) {
        showToast('Rozpoczęto bezpieczne wygaszanie kotła (pompa CO stop poniżej 40°C)', 'info');
      } else {
        showToast('Błąd procedury wygaszania', 'error');
      }
    } catch (err) {
      showToast(`Błąd: ${err.message}`, 'error');
    } finally {
      isExtinguishing = false;
    }
  }
</script>

<div class="dashboard-layout">
  <!-- 1. Top Section: Furnace Schematic (Rysunek Pieca) -->
  <section class="schematic-section">
    <Schematic
      boilerTemp={status?.boiler_temp}
      targetBoilerTemp={status?.target_boiler_temp}
      dhwTemp={status?.dhw_temp}
      targetDhwTemp={status?.target_dhw_temp}
      returnTemp={status?.return_temp}
      exhaustTemp={status?.exhaust_temp}
      outdoorTemp={status?.outdoor_temp}
      chPump={!!status?.ch_pump}
      dhwPump={!!status?.dhw_pump}
      mixerPump={!!status?.mixer_pump}
      circulationPump={!!status?.z1_pump}
      mixerCircuit={status?.mixer_circuit}
      blowerActive={!!status?.air_pump}
      blowerPower={status?.air_pump_power || 0}
      feederActive={!!status?.coal_feeder}
      feederTemp={status?.feeder_temp}
      floorTemp={status?.floor_temp}
      fuelPct={status?.fuel_load_pct ?? 0}
      fuelKg={fuelKgDisplay}
      heatingState={status?.heating || 0}
    />
  </section>

  <!-- 2. Middle Section: Harmonogram odpowiadający wybranemu sterownikowi -->
  <section class="schedule-section">
    <div class="metric-card schedule-preview-card">
      <div class="card-top" style="margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
          <!-- Przełącznik wyboru harmonogramu (domyślnie aktywny regulator) -->
          <div class="schedule-selector-tabs">
            <button
              class="schedule-tab-btn"
              class:active={activeScheduleId === 27}
              onclick={() => userSelectedScheduleId = 27}
              title="Harmonogram stref dzień/noc regulatora pokojowego"
            >
              🏠 Pokojowy (Dzień/Noc)
              {#if isRoomControlActive}
                <span class="active-dot" title="Aktywne sterowanie temperaturą wewnętrzną">●</span>
              {/if}
            </button>
            <button
              class="schedule-tab-btn"
              class:active={activeScheduleId === 24}
              onclick={() => userSelectedScheduleId = 24}
              title="Harmonogram obniżenia temperatury kotła CO"
            >
              🔥 Kocioł CO
              {#if !isRoomControlActive}
                <span class="active-dot" title="Aktywne sterowanie temperaturą kotła CO">●</span>
              {/if}
            </button>
          </div>

          {#if activeScheduleId === 27}
            <span class="card-title" style="font-size: 1.05rem;">
              {status?.day_night === 1 ? '🌙 Tryb Nocny Pokoju' : '☀️ Tryb Dzienny Pokoju'}
            </span>
            {#if status?.day_night === 1}
              <span class="badge-lowered">
                Zadana: <strong>{status?.room_night_temp != null ? status.room_night_temp.toFixed(1) : '--'}°C</strong>
              </span>
            {:else}
              <span class="badge-comfort">
                Zadana: <strong>{status?.room_day_temp != null ? status.room_day_temp.toFixed(1) : '--'}°C</strong>
              </span>
            {/if}
          {:else}
            <span class="card-title" style="font-size: 1.05rem;">
              {status?.co_lowered_active ? '🌙 Tryb Obniżony CO' : '☀️ Temperatura Komfortowa CO'}
            </span>
            {#if status?.co_lowered_active}
              <span class="badge-lowered">
                Zadana: <strong>{status?.target_boiler_temp ?? '--'}°C</strong> (-{status?.co_lowered_amount || 10}°C z bazowej {(status?.target_boiler_temp || 0) + (status?.co_lowered_amount || 10)}°C)
              </span>
            {:else}
              <span class="badge-comfort">
                Zadana: <strong>{status?.target_boiler_temp ?? '--'}°C</strong>
              </span>
            {/if}
          {/if}
        </div>

        {#if modeRemainingInfo}
          <span class="mode-remaining-badge">
            {activeScheduleId === 27
              ? (modeRemainingInfo.isComfort ? '☀️ Dzień' : '🌙 Noc')
              : (modeRemainingInfo.isComfort ? '☀️ Komfort' : '🌙 Obniżenie')} do <strong>{modeRemainingInfo.endTime}</strong> (pozostało ~{modeRemainingInfo.timeRemaining})
          </span>
        {/if}
      </div>

      <!-- Klocki osi czasu (Timeline Blocks) -->
      <div class="timeline-wrapper">
        <div class="timeline-header-meta">
          <span class="timeline-label">
            Najbliższe 12 godzin ({activeScheduleId === 27 ? 'Harmonogram pokojowy #27' : 'Harmonogram CO #24'}, klocki co 30 min):
          </span>
          <div class="timeline-legend">
            {#if activeScheduleId === 27}
              <span class="legend-item"><span class="legend-swatch comfort"></span> Dzień ({status?.room_day_temp != null ? status.room_day_temp.toFixed(1) : '21.0'}°C)</span>
              <span class="legend-item"><span class="legend-swatch lowered"></span> Noc ({status?.room_night_temp != null ? status.room_night_temp.toFixed(1) : '19.0'}°C)</span>
            {:else}
              <span class="legend-item"><span class="legend-swatch comfort"></span> Komfort ({status?.co_lowered_active ? ((status?.target_boiler_temp || 0) + (status?.co_lowered_amount || 10)) : (status?.target_boiler_temp || 50)}°C)</span>
              <span class="legend-item"><span class="legend-swatch lowered"></span> Obniżona ({status?.co_lowered_active ? (status?.target_boiler_temp || 45) : ((status?.target_boiler_temp || 50) - (status?.co_lowered_amount || 10))}°C)</span>
            {/if}
          </div>
        </div>

        <div class="timeline-blocks">
          {#each timelineSlots as slot}
            <div
              class="t-block"
              class:comfort={slot.isComfort}
              class:lowered={!slot.isComfort}
              class:current={slot.isCurrent}
              title="{slot.time} — {activeScheduleId === 27 ? (slot.isComfort ? 'Dzień / Komfort' : 'Noc / Obniżenie') : (slot.isComfort ? 'Komfortowa CO' : 'Obniżona CO')}{slot.isCurrent ? ' [TERAZ]' : ''}"
            >
              {#if slot.isCurrent}
                <div class="current-indicator">TERAZ</div>
              {/if}
              {#if slot.minute === '00'}
                <span class="block-hour">{slot.hour}</span>
              {/if}
            </div>
          {/each}
        </div>
      </div>

      <!-- Quick Action Buttons -->
      <div class="schedule-actions-row">
        {#if activeScheduleId === 27}
          <button
            class="btn-quick-mode night"
            onclick={() => handleForceMode(true, 2)}
            disabled={isForcingMode}
            title="Wymusza strefę nocną regulatora pokojowego na najbliższe 2 godziny (4 klocki)"
          >
            {isForcingMode ? 'Zapisywanie...' : '🌙 Wymuś noc (2h)'}
          </button>
          <button
            class="btn-quick-mode day"
            onclick={() => handleForceMode(false, 2)}
            disabled={isForcingMode}
            title="Wymusza strefę dzienną regulatora pokojowego na najbliższe 2 godziny (4 klocki)"
          >
            {isForcingMode ? 'Zapisywanie...' : '☀️ Wymuś dzień (2h)'}
          </button>
        {:else}
          <button
            class="btn-quick-mode night"
            onclick={() => handleForceMode(true, 2)}
            disabled={isForcingMode}
            title="Wymusza obniżenie temperatury CO w harmonogramie na najbliższe 2 godziny (4 klocki)"
          >
            {isForcingMode ? 'Zapisywanie...' : '🌙 Wymuś obniżenie (2h)'}
          </button>
          <button
            class="btn-quick-mode day"
            onclick={() => handleForceMode(false, 2)}
            disabled={isForcingMode}
            title="Wymusza temperaturę komfortową CO w harmonogramie na najbliższe 2 godziny (4 klocki)"
          >
            {isForcingMode ? 'Zapisywanie...' : '☀️ Wymuś komfort (2h)'}
          </button>
        {/if}
        <button
          class="btn-quick-mode neutral"
          onclick={() => onSelectTab('schedules')}
        >
          ⚙️ Harmonogram tygodniowy (7 dni)
        </button>
      </div>
    </div>
  </section>

  <!-- 3. Bottom Section: 2 kolumny z kartami na desktopie, 1 kolumna na telefonie -->
  <section class="metrics-section">
    <div class="metrics-grid-2col">
      <!-- Card 1: Kocioł CO -->
      <div class="metric-card">
        <div class="card-top">
          <span class="card-title">🔥 Kocioł CO</span>
          {#if status?.auto_mode === false}
            <span class="badge-extinguished" title="Kocioł w trybie ręcznym / wygaszania. Pompa CO wyłączy się automatycznie przy <40°C">
            ❄️ Wygaszanie / Manual
          </span>
        {:else if status?.co_lowered_active}
          <span class="badge-lowered" title="Aktywne obniżenie temperatury CO: -{status?.co_lowered_amount || 10}°C (bazowa: {(status?.target_boiler_temp || 0) + (status?.co_lowered_amount || 10)}°C)">
            🌙 Obniżona (-{status?.co_lowered_amount || 10}°C)
          </span>
        {:else if status?.co_lowered_active === false}
          <span class="badge-comfort" title="Temperatura komfortowa (standardowa)">
            ☀️ Komfort
          </span>
        {/if}
      </div>

      <div class="temp-readings-grid">
        <div class="temp-col">
          <span class="temp-col-label">ZMIERZONA</span>
          <div class="temp-col-value">
            <span class="card-value" style="color: var(--accent-hot);">
              {status?.boiler_temp != null ? status.boiler_temp.toFixed(1) : '--'}
            </span>
            <span class="card-unit">°C</span>
          </div>
        </div>

        <div class="temp-col-divider"></div>

        <div class="temp-col">
          <span class="temp-col-label">ZADANA</span>
          <div class="temp-col-value">
            <span class="card-value" style="color: var(--accent-flame);">
              {status?.target_boiler_temp ?? '--'}
            </span>
            <span class="card-unit">°C</span>
          </div>
        </div>
      </div>

      <div class="setpoint-controls">
        <button class="step-btn" onclick={() => onStepSetpoint('co', -1)} aria-label="Zmniejsz zadaną CO">-</button>
        <span class="step-target-display">Zmień zadaną</span>
        <button class="step-btn" onclick={() => onStepSetpoint('co', 1)} aria-label="Zwiększ zadaną CO">+</button>
      </div>

      <div style="margin-top: 0.75rem; border-top: 1px solid var(--border-color); padding-top: 0.65rem; display: flex; justify-content: flex-end;">
        <button
          class="btn-extinguish"
          onclick={handleExtinguish}
          disabled={isExtinguishing || status?.auto_mode === false}
          title="Bezpieczne wygaszenie: wyłącza tryb AUTO (zatrzymuje podajnik i dmuchawę), pompa CO wyłączy się automatycznie poniżej 40°C"
        >
          {status?.auto_mode === false ? '❄️ Kocioł wygaszany' : (isExtinguishing ? 'Wygaszanie...' : '❄️ Bezpiecznie wygaś')}
        </button>
      </div>
    </div>

    <!-- Card 2: Bojler CWU -->
    <div class="metric-card">
      <div class="card-top">
        <span class="card-title">💧 Bojler CWU</span>
        {#if status?.cwu_lowered_active}
          <span class="badge-lowered" title="Aktywne obniżenie temperatury CWU: -{status?.cwu_lowered_amount || 5}°C">
            🌙 Obniżona (-{status?.cwu_lowered_amount || 5}°C)
          </span>
        {/if}
      </div>

      <div class="temp-readings-grid">
        <div class="temp-col">
          <span class="temp-col-label">ZMIERZONA</span>
          <div class="temp-col-value">
            <span class="card-value" style="color: #38bdf8;">
              {status?.dhw_temp != null ? status.dhw_temp.toFixed(1) : '--'}
            </span>
            <span class="card-unit">°C</span>
          </div>
        </div>

        <div class="temp-col-divider"></div>

        <div class="temp-col">
          <span class="temp-col-label">ZADANA</span>
          <div class="temp-col-value">
            <span class="card-value" style="color: #93c5fd;">
              {status?.target_dhw_temp ?? '--'}
            </span>
            <span class="card-unit">°C</span>
          </div>
        </div>
      </div>

      <div class="setpoint-controls">
        <button class="step-btn" onclick={() => onStepSetpoint('cwu', -1)} aria-label="Zmniejsz zadaną CWU">-</button>
        <span class="step-target-display">Zmień zadaną</span>
        <button class="step-btn" onclick={() => onStepSetpoint('cwu', 1)} aria-label="Zwiększ zadaną CWU">+</button>
      </div>

      <!-- Sekcja Dezynfekcji Legionelli -->
      <div class="legionella-section">
        {#if isLegionellaActive}
          <div class="legionella-banner active">
            <div class="legionella-status-row">
              <span class="legionella-icon">🛡</span>
              <div class="legionella-info">
                <span class="legionella-title">
                  {#if legionellaPhase === 'heating'}
                    Rozgrzewanie do 60°C...
                  {:else if legionellaPhase === 'holding'}
                    Wygrzewanie Legionelli (60°C)
                  {:else}
                    Dezynfekcja aktywna
                  {/if}
                </span>
                <span class="legionella-timer">
                  {#if legionellaPhase === 'heating'}
                    CWU: {status?.dhw_temp != null ? status.dhw_temp.toFixed(1) : '--'}°C / 60°C
                  {:else}
                    Pozostało: <strong>{legionellaTimerDisplay}</strong>
                  {/if}
                </span>
              </div>
            </div>
            <button
              class="btn-legionella-cancel"
              onclick={handleStopLegionella}
              disabled={isTriggeringLegionella}
              title="Przerwij dezynfekcję termiczną i przywróć poprzednie temperatury"
            >
              ⏹ Zatrzymaj
            </button>
          </div>
        {:else}
          <div class="legionella-banner idle">
            <button
              class="btn-legionella-start"
              onclick={handleStartLegionella}
              disabled={isTriggeringLegionella}
              title="Wygrzej bojler do 60°C przez 30 minut, aby wyeliminować bakterie Legionella"
            >
              <span class="btn-icon">🦠</span>
              <span class="btn-text">Dezynfekcja Legionelli (60°C)</span>
            </button>
            {#if legionella?.last_run}
              <span class="legionella-last-run" title="Data ostatniej udanej dezynfekcji">
                Ostatnio: {formatLegionellaDate(legionella.last_run)}
              </span>
            {/if}
          </div>
        {/if}
      </div>
    </div>

    <!-- Card 3: Temperatura Pokojowa / Regulator -->
    <div class="metric-card">
      <div class="card-top">
        <span class="card-title">🏠 Pokój & Regulator</span>
        {#if status?.day_night === 1}
          <span class="badge-lowered" title="Aktywna strefa nocna regulatora pokojowego">
            🌙 Noc
          </span>
        {:else}
          <span
            style="background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); font-size: 0.72rem; padding: 0.2rem 0.5rem; border-radius: 999px; font-weight: 600;"
            title="Aktywna strefa dzienna regulatora pokojowego"
          >
            ☀️ Dzień
          </span>
        {/if}
      </div>

      <div class="temp-readings-grid">
        <div class="temp-col">
          <span class="temp-col-label">ZMIERZONA</span>
          <div class="temp-col-value">
            <span class="card-value" style="color: #4ade80;">
              {status?.indoor_temp != null ? status.indoor_temp.toFixed(1) : '--'}
            </span>
            <span class="card-unit">°C</span>
          </div>
        </div>

        <div class="temp-col-divider"></div>

        <div class="temp-col">
          <span class="temp-col-label">ZADANA ({status?.day_night === 1 ? 'NOC' : 'DZIEŃ'})</span>
          <div class="temp-col-value">
            <span class="card-value" style="color: #a7f3d0;">
              {status?.day_night === 1
                ? (status?.room_night_temp != null ? status.room_night_temp.toFixed(1) : '--')
                : (status?.room_day_temp != null ? status.room_day_temp.toFixed(1) : '--')}
            </span>
            <span class="card-unit">°C</span>
          </div>
        </div>
      </div>

      <!-- Szybkie nastawy temperatury: Dzień i Noc -->
      <div style="display: flex; flex-direction: column; gap: 0.45rem; margin-top: 0.5rem;">
        <div class="setpoint-controls" style="margin-top: 0;">
          <button class="step-btn" onclick={() => onStepSetpoint('room_day', -0.5)} aria-label="Zmniejsz temp. dzienną">-</button>
          <span class="step-target-display" title="Zadana temperatura dzienna">
            ☀️ Dzień: <strong>{status?.room_day_temp != null ? status.room_day_temp.toFixed(1) : '--'}°C</strong>
          </span>
          <button class="step-btn" onclick={() => onStepSetpoint('room_day', 0.5)} aria-label="Zwiększ temp. dzienną">+</button>
        </div>

        <div class="setpoint-controls" style="margin-top: 0;">
          <button class="step-btn" onclick={() => onStepSetpoint('room_night', -0.5)} aria-label="Zmniejsz temp. nocną">-</button>
          <span class="step-target-display" title="Zadana temperatura nocna">
            🌙 Noc: <strong>{status?.room_night_temp != null ? status.room_night_temp.toFixed(1) : '--'}°C</strong>
          </span>
          <button class="step-btn" onclick={() => onStepSetpoint('room_night', 0.5)} aria-label="Zwiększ temp. nocną">+</button>
        </div>
      </div>

      <div style="margin-top: 0.75rem; border-top: 1px solid var(--border-color); padding-top: 0.55rem; display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem;">
        <span style="color: var(--text-muted);">
          {#if status?.room_heating}
            🔥 <strong style="color: #f97316;">Dogrzewanie pokoju</strong>
          {:else}
            ✅ <strong style="color: #22c55e;">Pokój dogrzany</strong> (cykl pompy CO)
          {/if}
        </span>
        <button
          onclick={() => onSelectTab('schedules')}
          style="background: none; border: none; color: var(--accent-flame); cursor: pointer; text-decoration: underline; font-size: 0.75rem; padding: 0;"
          title="Przejdź do edycji godzinowego harmonogramu regulatora pokojowego"
        >
          📅 Harmonogram
        </button>
      </div>
    </div>

    <!-- Card 4: Zapas Opału -->
    <div class="metric-card">
      <div class="card-top">
        <span class="card-title">📦 Zapas Opału</span>
        {#if estimatedEmptyDisplay}
          <span class="card-target" title="Szacowany termin wyczerpania opału">
            Koniec: <strong>{estimatedEmptyDisplay}</strong>
          </span>
        {:else}
          <span class="card-target">Pojemność: {hopperCapacity} kg</span>
        {/if}
      </div>

      <div class="temp-readings-grid">
        <div class="temp-col">
          <span class="temp-col-label">POZOSTAŁO</span>
          <div class="temp-col-value">
            <span class="card-value" style="color: var(--accent-flame);">
              {fuelKgDisplay}
            </span>
            <span class="card-unit">kg</span>
          </div>
        </div>

        <div class="temp-col-divider"></div>

        <div class="temp-col">
          <span class="temp-col-label">POZIOM</span>
          <div class="temp-col-value">
            <span class="card-value" style="color: {fuelPct <= 15 ? 'var(--accent-danger)' : 'var(--accent-flame)'};">
              {fuelPct}
            </span>
            <span class="card-unit">%</span>
          </div>
        </div>
      </div>

      <div class="fuel-progress-wrapper">
        <div class="fuel-bar-bg">
          <div
            class="fuel-bar-fill"
            class:low={fuelPct <= 15}
            style="width: {Math.max(0, Math.min(100, fuelPct))}%;"
          ></div>
        </div>
        <div class="fuel-meta">
          <span>Czas pracy ślimaka: <strong>{feederRuntimeDisplay}</strong></span>
        </div>
      </div>
      <button class="btn-refill" onclick={onRefillHopper}>⛽ Zasypano do pełna (100%)</button>
    </div>

    <!-- Card 4: Dmuchawa & Algorytm -->
    <div class="metric-card">
      <div class="card-top">
        <span class="card-title">💨 Nadmuch & Algorytm</span>
        <span class="card-target" style="font-weight: 700; color: var(--accent-flame);">
          {status?.air_pump_power || 0}%
        </span>
      </div>
      <div style="margin-bottom: 0.75rem;">
        <label for="feederModeSelect" style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">
          Tryb spalania podajnika:
        </label>
        <select
          id="feederModeSelect"
          class="transport-select"
          style="width: 100%; padding: 0.45rem;"
          value={status?.feeder_mode != null ? String(status.feeder_mode) : '1'}
          onchange={handleModeChange}
        >
          <option value="1">Spalanie grupowe</option>
          <option value="2">Algorytm eCoal</option>
          <option value="0">Tryb ręczny (dwustanowy)</option>
          <option value="3">Tryb zasypowy</option>
        </select>
      </div>
      <div style="margin-bottom: 0.75rem;">
        <label for="mixerModeSelect" style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.3rem;">
          Obieg mieszacza (wyjście OUT 4/6/7):
        </label>
        <select
          id="mixerModeSelect"
          class="transport-select"
          style="width: 100%; padding: 0.45rem;"
          value={status?.mixer_circuit != null ? String(status.mixer_circuit) : '2'}
          onchange={handleMixerModeChange}
        >
          <option value="2">Ogrzewanie podłogowe (Podłogówka)</option>
          <option value="1">Mieszacz / Zawór 3D (Ochrona powrotu)</option>
          <option value="0">Wyłączony</option>
        </select>
      </div>
      <div class="actuator-row">
        <span class="actuator-tag" class:on={!!status?.air_pump}>Dmuchawa</span>
        <span class="actuator-tag" class:on={!!status?.coal_feeder}>Podajnik</span>
        <span class="actuator-tag" class:on={!!status?.ch_pump}>Pompa CO</span>
        <span class="actuator-tag" class:on={!!status?.dhw_pump}>Pompa CWU</span>
        <span class="actuator-tag" class:on={!!status?.mixer_pump}>
          {status?.mixer_circuit === 1 ? 'Mieszacz' : 'Podłogówka'}
        </span>
        <span class="actuator-tag" class:on={!!status?.z1_pump}>Cyrkulacja</span>
      </div>
    </div>

    <!-- Card: Czystość Wymiennika & Sprawność -->
    <div class="metric-card">
      <div class="card-top">
        <span class="card-title">🧹 Czystość & Sprawność</span>
        {#if cleaningRequired}
          <span class="badge-clean-warn" title={cleaningWarningReason || 'Wymagane czyszczenie wymiennika'}>
            ⚠️ Wyczyść kocioł
          </span>
        {:else}
          <span class="badge-clean-ok">
            ✓ Wymiennik czysty
          </span>
        {/if}
      </div>

      {#if cleaningRequired && cleaningWarningReason}
        <div style="font-size: 0.76rem; color: #fca5a5; background: rgba(239, 68, 68, 0.12); padding: 0.35rem 0.55rem; border-radius: var(--radius-sm); margin-bottom: 0.5rem; border-left: 3px solid #ef4444;">
          {cleaningWarningReason}
        </div>
      {/if}

      <div class="cleaning-metrics-grid">
        <div class="cleaning-stat-item">
          <span class="cleaning-stat-label">Dni od czyszczenia</span>
          <span class="cleaning-stat-value">{daysSinceCleaning} d</span>
        </div>
        <div class="cleaning-stat-item">
          <span class="cleaning-stat-label">Spalony opał</span>
          <span class="cleaning-stat-value">{coalBurnedSinceCleaning} kg</span>
        </div>
        <div class="cleaning-stat-item">
          <span class="cleaning-stat-label">Śr. spaliny (grzanie)</span>
          <span class="cleaning-stat-value">
            {avgExhaustHeating != null ? avgExhaustHeating.toFixed(1) + '°C' : '--'}
          </span>
        </div>
        <div class="cleaning-stat-item">
          <span class="cleaning-stat-label">Tempo grzania</span>
          <span class="cleaning-stat-value">
            {heatingRate != null ? heatingRate.toFixed(2) : '--'}
            <small style="font-size: 0.65rem; color: var(--text-muted);">°C/min</small>
          </span>
        </div>
      </div>

      <button
        class="btn-record-cleaning"
        onclick={handleRecordCleaning}
        disabled={isRecordingCleaning}
        title="Zapisuje dzisiejszą datę jako datę czyszczenia i resetuje licznik spalonego węgla"
      >
        <span class="btn-icon">🧹</span>
        <span class="btn-text">{isRecordingCleaning ? 'Zapisywanie...' : 'Oznacz wyczyszczenie kotła'}</span>
      </button>

      {#if maintenance?.last_cleaned_at}
        <div style="font-size: 0.7rem; color: var(--text-muted); text-align: center; margin-top: 0.45rem;">
          Ostatnio: {formatCleaningDate(maintenance.last_cleaned_at)}
        </div>
      {/if}
    </div>

    <!-- Card 5: Temperatury Pomocnicze -->
    <div class="metric-card card-span-2">
      <div class="card-top">
        <span class="card-title">🌡️ Temperatury Pomocnicze & Warunki</span>
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 1rem; text-align: center;">
        <div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">Temperatura Powrotu</div>
          <div style="font-size: 1.4rem; font-weight: 700; color: #93c5fd;">
            {status?.return_temp != null ? status.return_temp.toFixed(1) : '--'}°C
          </div>
        </div>
        <div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">Temperatura Spalin</div>
          <div style="font-size: 1.4rem; font-weight: 700; color: #f97316;">
            {status?.exhaust_temp != null ? status.exhaust_temp.toFixed(1) : '--'}°C
          </div>
        </div>
        <div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">Temperatura Podajnika</div>
          <div style="font-size: 1.4rem; font-weight: 700; color: #cbd5e1;">
            {status?.feeder_temp != null ? status.feeder_temp.toFixed(1) : '--'}°C
          </div>
        </div>
        <div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">Zewnętrzna</div>
          <div style="font-size: 1.4rem; font-weight: 700; color: #38bdf8;">
            {status?.outdoor_temp != null ? status.outdoor_temp.toFixed(1) : '--'}°C
          </div>
        </div>
        <div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">Wewnętrzna (Pokojowa)</div>
          <div style="font-size: 1.4rem; font-weight: 700; color: #34d399;">
            {status?.indoor_temp != null ? status.indoor_temp.toFixed(1) : '--'}°C
          </div>
        </div>
        {#if status?.floor_temp != null}
          <div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">
              {status?.mixer_circuit === 1 ? 'Za mieszaczem' : 'Podłogowa'}
            </div>
            <div style="font-size: 1.4rem; font-weight: 700; color: {status?.mixer_circuit === 1 ? '#60a5fa' : '#818cf8'};">
              {status.floor_temp.toFixed(1)}°C
            </div>
          </div>
        {:else if status?.mixer_circuit && status.mixer_circuit > 0}
          <div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">
              {status?.mixer_circuit === 1 ? 'Za mieszaczem' : 'Podłogowa'}
            </div>
            <div style="font-size: 1.05rem; font-weight: 600; color: var(--text-muted); margin-top: 0.25rem;">
              Brak czujnika
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>
  </section>
</div>
