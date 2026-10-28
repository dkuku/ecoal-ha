<script>
  import { onMount } from 'svelte';
  import Schematic from './Schematic.svelte';

  let {
    status = {},
    hopperCapacity = 150,
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

  let coSchedule = $state(null);
  let isForcingMode = $state(false);

  async function loadCoSchedule() {
    if (!client) return;
    try {
      const res = await client.getWeeklyProgram(24);
      if (res && res.length === 7) {
        coSchedule = res;
      }
    } catch (_) {}
  }

  onMount(() => {
    loadCoSchedule();
    const timer = setInterval(loadCoSchedule, 30000);
    return () => clearInterval(timer);
  });

  async function handleForceCoMode(lowered, hours = 2) {
    if (!client || isForcingMode) return;
    isForcingMode = true;
    try {
      const ok = await client.forceCoMode(lowered, hours);
      if (ok) {
        showToast(
          lowered
            ? `Wymuszono obniżenie temperatury CO na ${hours}h`
            : `Wymuszono temperaturę komfortową CO na ${hours}h`,
          'success'
        );
        await loadCoSchedule();
      } else {
        showToast('Nie udało się zapisać zmiany w sterowniku kotła', 'error');
      }
    } catch (err) {
      showToast(`Błąd: ${err.message}`, 'error');
    } finally {
      isForcingMode = false;
    }
  }

  // Calculate timeline slots for the next 24 half-hours (12 hours preview)
  let timelineSlots = $derived.by(() => {
    if (!coSchedule || coSchedule.length !== 7) return [];
    const now = new Date();
    const curHour = now.getHours();
    const curMin = now.getMinutes();
    const curSlot = curHour * 2 + (curMin >= 30 ? 1 : 0);
    const curDay = now.getDay();

    const slots = [];
    for (let i = 0; i < 24; i++) {
      const targetSlot = (curSlot + i) % 48;
      const targetDay = (curDay + Math.floor((curSlot + i) / 48)) % 7;
      const isComfort = (coSchedule[targetDay] || '')[targetSlot] === '1';

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
</script>

<div class="dashboard-grid">
  <!-- Left Column: Hydraulic Schematic & Schedule Timeline Blocks -->
  <div class="schematic-column">
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

    <!-- Card: Harmonogram CO & Oś Czasu (Klocki pod schematem) -->
    <div class="metric-card schedule-preview-card">
      <div class="card-top" style="margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;">
          <span class="card-title" style="font-size: 1.05rem;">
            {status?.co_lowered_active ? '🌙 Tryb Obniżony CO (Aktywny)' : '☀️ Temperatura Komfortowa CO'}
          </span>
          {#if status?.co_lowered_active}
            <span class="badge-lowered">
              Zadana: <strong>{status.target_boiler_temp}°C</strong> (-{status.co_lowered_amount || 10}°C z bazowej {(status.target_boiler_temp || 0) + (status.co_lowered_amount || 10)}°C)
            </span>
          {:else}
            <span class="badge-comfort">
              Zadana: <strong>{status?.target_boiler_temp ?? '--'}°C</strong>
            </span>
          {/if}
        </div>
        {#if modeRemainingInfo}
          <span class="mode-remaining-badge">
            {modeRemainingInfo.isComfort ? '☀️ Komfort' : '🌙 Obniżenie'} do <strong>{modeRemainingInfo.endTime}</strong> (pozostało ~{modeRemainingInfo.timeRemaining})
          </span>
        {/if}
      </div>

      <!-- Klocki osi czasu (Timeline Blocks) -->
      <div class="timeline-wrapper">
        <div class="timeline-header-meta">
          <span class="timeline-label">Najbliższe 12 godzin (klocki co 30 min):</span>
          <div class="timeline-legend">
            <span class="legend-item"><span class="legend-swatch comfort"></span> Komfort ({status?.co_lowered_active ? ((status?.target_boiler_temp || 0) + (status?.co_lowered_amount || 10)) : (status?.target_boiler_temp || 55)}°C)</span>
            <span class="legend-item"><span class="legend-swatch lowered"></span> Obniżona ({status?.co_lowered_active ? (status?.target_boiler_temp || 45) : ((status?.target_boiler_temp || 55) - (status?.co_lowered_amount || 10))}°C)</span>
          </div>
        </div>

        <div class="timeline-blocks">
          {#each timelineSlots as slot}
            <div
              class="t-block"
              class:comfort={slot.isComfort}
              class:lowered={!slot.isComfort}
              class:current={slot.isCurrent}
              title="{slot.time} — {slot.isComfort ? 'Komfortowa' : 'Obniżona'}{slot.isCurrent ? ' [TERAZ]' : ''}"
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
        <button
          class="btn-quick-mode night"
          onclick={() => handleForceCoMode(true, 2)}
          disabled={isForcingMode}
          title="Wymusza obniżenie temperatury CO w harmonogramie na najbliższe 2 godziny (4 klocki)"
        >
          {isForcingMode ? 'Zapisywanie...' : '🌙 Wymuś obniżenie (2h)'}
        </button>
        <button
          class="btn-quick-mode day"
          onclick={() => handleForceCoMode(false, 2)}
          disabled={isForcingMode}
          title="Wymusza temperaturę komfortową CO w harmonogramie na najbliższe 2 godziny (4 klocki)"
        >
          {isForcingMode ? 'Zapisywanie...' : '☀️ Wymuś komfort (2h)'}
        </button>
        <button
          class="btn-quick-mode neutral"
          onclick={() => onSelectTab('schedules')}
        >
          ⚙️ Harmonogram tygodniowy (7 dni)
        </button>
      </div>
    </div>
  </div>

  <!-- Right Column: Metrics Cards -->
  <div class="metrics-grid">
    <!-- Card 1: Kocioł CO -->
    <div class="metric-card">
      <div class="card-top">
        <span class="card-title">🔥 Kocioł CO</span>
        {#if status?.co_lowered_active}
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
    </div>

    <!-- Card 3: Zapas Opału -->
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

    <!-- Card 5: Temperatury Pomocnicze -->
    <div class="metric-card" style="grid-column: 1 / -1;">
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
</div>
