<script>
  import Schematic from './Schematic.svelte';

  let {
    status = {},
    hopperCapacity = 150,
    onStepSetpoint = () => {},
    onRefillHopper = () => {},
    onSetFeederMode = () => {},
  } = $props();

  let fuelPct = $derived(status?.fuel_load_pct ?? 0);
  let fuelKg = $derived(
    status?.fuel_remaining_kg != null
      ? status.fuel_remaining_kg
      : Math.round((hopperCapacity * fuelPct) / 100)
  );

  let feederRuntimeDisplay = $derived.by(() => {
    const mins = status?.feeder_runtime_min ?? (status?.feeder_runtime ?? 0);
    const hours = Math.floor(mins / 60);
    const remMins = Math.round(mins % 60);
    return `${hours}h ${remMins}m`;
  });

  function handleModeChange(e) {
    const val = parseInt(e.target.value, 10);
    onSetFeederMode(val);
  }
</script>

<div class="dashboard-grid">
  <!-- Left Column: Hydraulic Schematic -->
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
    blowerActive={!!status?.air_pump}
    blowerPower={status?.air_pump_power || 0}
    heatingState={status?.heating || 0}
  />

  <!-- Right Column: Metrics Cards -->
  <div class="metrics-grid">
    <!-- Card 1: Kocioł CO -->
    <div class="metric-card">
      <div class="card-top">
        <span class="card-title">🔥 Kocioł CO</span>
        <span class="card-target">Zadana: <strong>{status?.target_boiler_temp ?? '--'}</strong>°C</span>
      </div>
      <div class="card-value-row">
        <span class="card-value" style="color: var(--accent-hot);">
          {status?.boiler_temp != null ? status.boiler_temp.toFixed(1) : '--'}
        </span>
        <span class="card-unit">°C</span>
      </div>
      <div class="setpoint-controls">
        <button class="step-btn" onclick={() => onStepSetpoint('co', -1)} aria-label="Zmniejsz zadaną CO">-</button>
        <span class="step-target-display">Zmień nastawę</span>
        <button class="step-btn" onclick={() => onStepSetpoint('co', 1)} aria-label="Zwiększ zadaną CO">+</button>
      </div>
    </div>

    <!-- Card 2: Bojler CWU -->
    <div class="metric-card">
      <div class="card-top">
        <span class="card-title">💧 Bojler CWU</span>
        <span class="card-target">Zadana: <strong>{status?.target_dhw_temp ?? '--'}</strong>°C</span>
      </div>
      <div class="card-value-row">
        <span class="card-value" style="color: #38bdf8;">
          {status?.dhw_temp != null ? status.dhw_temp.toFixed(1) : '--'}
        </span>
        <span class="card-unit">°C</span>
      </div>
      <div class="setpoint-controls">
        <button class="step-btn" onclick={() => onStepSetpoint('cwu', -1)} aria-label="Zmniejsz zadaną CWU">-</button>
        <span class="step-target-display">Zmień nastawę</span>
        <button class="step-btn" onclick={() => onStepSetpoint('cwu', 1)} aria-label="Zwiększ zadaną CWU">+</button>
      </div>
    </div>

    <!-- Card 3: Zapas Opału -->
    <div class="metric-card">
      <div class="card-top">
        <span class="card-title">📦 Zapas Opału</span>
        <span class="card-target">ok. {fuelKg} kg</span>
      </div>
      <div class="card-value-row">
        <span class="card-value" style="color: var(--accent-flame);">{fuelPct}%</span>
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
      <div class="actuator-row">
        <span class="actuator-tag" class:on={!!status?.air_pump}>Dmuchawa</span>
        <span class="actuator-tag" class:on={!!status?.coal_feeder}>Podajnik</span>
        <span class="actuator-tag" class:on={!!status?.ch_pump}>Pompa CO</span>
        <span class="actuator-tag" class:on={!!status?.dhw_pump}>Pompa CWU</span>
        <span class="actuator-tag" class:on={!!status?.mixer_pump}>Mieszacz</span>
      </div>
    </div>

    <!-- Card 5: Temperatury Pomocnicze -->
    <div class="metric-card" style="grid-column: 1 / -1;">
      <div class="card-top">
        <span class="card-title">🌡️ Temperatury Pomocnicze & Warunki</span>
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 1rem; text-align: center;">
        <div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">Powrót CO</div>
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
      </div>
    </div>
  </div>
</div>
