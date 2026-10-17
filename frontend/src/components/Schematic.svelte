<script>
  let {
    boilerTemp = null,
    targetBoilerTemp = null,
    dhwTemp = null,
    targetDhwTemp = null,
    returnTemp = null,
    exhaustTemp = null,
    outdoorTemp = null,
    chPump = false,
    dhwPump = false,
    mixerPump = false,
    blowerActive = false,
    blowerPower = 0,
    heatingState = 0,
  } = $props();

  let isFlameActive = $derived(heatingState > 0 || blowerActive);
  let heatingLabel = $derived(
    heatingState === 1 ? 'Grzanie' : heatingState === 2 ? 'Podtrzymanie' : 'Postój'
  );
</script>

<div class="schematic-card">
  <div class="schematic-header">
    <h2>Schemat Hydrauliczny Kotłowni</h2>
    <span class="card-status-pill" class:active={heatingState === 1}>
      {heatingLabel}
    </span>
  </div>

  <div class="schematic-wrapper">
    <svg class="schematic-svg" viewBox="0 0 800 500" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <!-- Gradients -->
        <linearGradient id="boilerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#334155" />
          <stop offset="100%" stop-color="#1e293b" />
        </linearGradient>
        <linearGradient id="cwuGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#1e293b" />
          <stop offset="50%" stop-color="#0284c7" stop-opacity="0.2" />
          <stop offset="100%" stop-color="#1e293b" />
        </linearGradient>
        <linearGradient id="flameGrad" x1="0%" y1="100%" x2="0%" y2="0%">
          <stop offset="0%" stop-color="#dc2626" />
          <stop offset="60%" stop-color="#f97316" />
          <stop offset="100%" stop-color="#fef08a" />
        </linearGradient>
      </defs>

      <!-- Pipes Background (Static Lines) -->
      <!-- Hot Supply Pipe (Boiler -> Radiators -> CWU) -->
      <path d="M 230 180 L 400 180 L 400 100 L 720 100" class="pipe-hot" />
      <path d="M 400 180 L 520 180 L 520 220" class="pipe-hot" />

      <!-- Return Pipe (Radiators & CWU -> Mixer -> Boiler) -->
      <path d="M 720 380 L 340 380 L 340 330 L 230 330" class="pipe-cold" />
      <path d="M 520 330 L 520 380" class="pipe-cold" />

      <!-- Animated Pipe Flow Overlays -->
      <path
        d="M 230 180 L 400 180 L 400 100 L 720 100"
        stroke="#fca5a5"
        stroke-width="3"
        fill="none"
        class:pipe-flow={chPump || heatingState > 0}
      />
      <path
        d="M 400 180 L 520 180 L 520 220"
        stroke="#fca5a5"
        stroke-width="3"
        fill="none"
        class:pipe-flow={dhwPump}
      />
      <path
        d="M 720 380 L 340 380 L 340 330 L 230 330"
        stroke="#93c5fd"
        stroke-width="3"
        fill="none"
        class:pipe-flow-reverse={chPump || mixerPump}
      />

      <!-- BOILER (Kocioł) -->
      <rect x="70" y="140" width="160" height="230" rx="12" fill="url(#boilerGrad)" stroke="#475569" stroke-width="2" />
      <text x="150" y="170" fill="#94a3b8" font-size="14" font-weight="700" text-anchor="middle">KOCIOŁ eCoal</text>

      <!-- Combustion Chamber & Flame -->
      <rect x="95" y="240" width="110" height="110" rx="8" fill="#090d16" stroke="#f97316" stroke-width="1.5" />
      <g class="flame-anim" class:flame-inactive={!isFlameActive}>
        <path d="M 150 260 C 130 285 115 310 125 335 C 135 350 165 350 175 335 C 185 310 170 285 150 260 Z" fill="url(#flameGrad)" />
        <path d="M 150 280 C 140 295 130 315 138 332 C 145 342 155 342 162 332 C 170 315 160 295 150 280 Z" fill="#fef08a" />
      </g>

      <!-- Flue Gas Pipe & Sensor -->
      <path d="M 110 140 L 110 70 L 40 70" stroke="#64748b" stroke-width="12" stroke-linecap="round" fill="none" />
      <circle cx="110" cy="90" r="14" fill="#1e293b" stroke="#f97316" stroke-width="2" />
      <text x="110" y="95" fill="#f8fafc" font-size="10" font-weight="700" text-anchor="middle">
        {exhaustTemp !== null && exhaustTemp !== undefined ? `${exhaustTemp.toFixed(1)}°C` : '--°C'}
      </text>
      <text x="110" y="55" fill="#94a3b8" font-size="11" text-anchor="middle">Spaliny</text>

      <!-- Boiler Temp Badge -->
      <rect x="180" y="160" width="85" height="32" rx="6" fill="#1e293b" stroke="#ef4444" stroke-width="1.5" />
      <text x="222" y="181" fill="#f8fafc" font-size="13" font-weight="800" text-anchor="middle">
        {boilerTemp !== null && boilerTemp !== undefined ? `${boilerTemp.toFixed(1)}°C` : '--°C'}
      </text>

      <!-- CWU BOILER (Zasobnik Bojler) -->
      <rect x="470" y="200" width="100" height="160" rx="20" fill="url(#cwuGrad)" stroke="#0284c7" stroke-width="2" />
      <text x="520" y="235" fill="#94a3b8" font-size="13" font-weight="700" text-anchor="middle">BOJLER CWU</text>
      <!-- CWU Temp Badge -->
      <rect x="478" y="255" width="84" height="30" rx="6" fill="#1e293b" stroke="#0284c7" stroke-width="1.5" />
      <text x="520" y="275" fill="#f8fafc" font-size="13" font-weight="800" text-anchor="middle">
        {dhwTemp !== null && dhwTemp !== undefined ? `${dhwTemp.toFixed(1)}°C` : '--°C'}
      </text>

      <!-- CWU Pump -->
      <g class="pump-rotor" class:pump-active={dhwPump} transform="translate(435, 180)">
        <circle cx="0" cy="0" r="14" fill="#0f172a" stroke="#0284c7" stroke-width="2" />
        <path class="pump-rotor" d="M -8 -8 L 8 8 M -8 8 L 8 -8" stroke="#0284c7" stroke-width="2.5" />
      </g>
      <text x="435" y="155" fill="#94a3b8" font-size="11" text-anchor="middle">Pompa CWU</text>

      <!-- CO CIRCULATION PUMP (Pompa CO) -->
      <g class="pump-rotor" class:pump-active={chPump} transform="translate(620, 100)">
        <circle cx="0" cy="0" r="15" fill="#0f172a" stroke="#ef4444" stroke-width="2" />
        <path class="pump-rotor" d="M -8 -8 L 8 8 M -8 8 L 8 -8" stroke="#ef4444" stroke-width="2.5" />
      </g>
      <text x="620" y="75" fill="#94a3b8" font-size="11" text-anchor="middle">Pompa CO</text>

      <!-- RADIATORS (Grzejniki) -->
      <rect x="680" y="180" width="80" height="130" rx="6" fill="#1e293b" stroke="#cbd5e1" stroke-width="1.5" />
      <line x1="700" y1="195" x2="700" y2="295" stroke="#475569" stroke-width="2" />
      <line x1="720" y1="195" x2="720" y2="295" stroke="#475569" stroke-width="2" />
      <line x1="740" y1="195" x2="740" y2="295" stroke="#475569" stroke-width="2" />
      <text x="720" y="245" fill="#e2e8f0" font-size="12" font-weight="600" text-anchor="middle">GRZEJNIKI</text>

      <!-- RETURN PUMP & SENSOR (Pompa Mieszacza / Powrót) -->
      <g class="pump-rotor" class:pump-active={mixerPump} transform="translate(285, 330)">
        <circle cx="0" cy="0" r="13" fill="#0f172a" stroke="#6366f1" stroke-width="2" />
        <path class="pump-rotor" d="M -7 -7 L 7 7 M -7 7 L 7 -7" stroke="#6366f1" stroke-width="2" />
      </g>
      <text x="285" y="360" fill="#94a3b8" font-size="11" text-anchor="middle">Mieszacz</text>

      <rect x="330" y="390" width="80" height="28" rx="6" fill="#1e293b" stroke="#3b82f6" stroke-width="1.5" />
      <text x="370" y="409" fill="#93c5fd" font-size="12" font-weight="700" text-anchor="middle">
        {returnTemp !== null && returnTemp !== undefined ? `${returnTemp.toFixed(1)}°C` : '--°C'}
      </text>
      <text x="370" y="435" fill="#94a3b8" font-size="11" text-anchor="middle">Powrót CO</text>

      <!-- OUTDOOR SENSOR BADGE -->
      <rect x="670" y="20" width="110" height="32" rx="6" fill="#0f172a" stroke="#38bdf8" stroke-width="1.5" />
      <text x="680" y="41" fill="#38bdf8" font-size="13">🌡️</text>
      <text x="735" y="41" fill="#f8fafc" font-size="13" font-weight="700" text-anchor="middle">
        {outdoorTemp !== null && outdoorTemp !== undefined ? `${outdoorTemp.toFixed(1)}°C` : '--°C'}
      </text>
    </svg>
  </div>
</div>
