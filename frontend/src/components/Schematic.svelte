<script>
  let {
    boilerTemp = null,
    targetBoilerTemp = null,
    dhwTemp = null,
    targetDhwTemp = null,
    returnTemp = null,
    exhaustTemp = null,
    outdoorTemp = null,
    feederTemp = null,
    fuelPct = 0,
    chPump = false,
    dhwPump = false,
    mixerPump = false,
    blowerActive = false,
    blowerPower = 0,
    feederActive = false,
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

        <!-- Clip path for feeder screw auger tube -->
        <clipPath id="feederTubeClip">
          <rect x="36" y="303" width="94" height="22" rx="2" />
        </clipPath>
      </defs>

      <!-- PIPES: Static Background Lines (with full vertical continuity) -->
      <!-- Hot Supply Pipe: Boiler -> Radiators (with vertical drop into radiator) -->
      <path d="M 230 180 L 400 180 L 400 110 L 720 110 L 720 180" class="pipe-hot" />
      <!-- Hot Supply Branch: CWU (with vertical drop into boiler) -->
      <path d="M 400 180 L 520 180 L 520 200" class="pipe-hot" />
      <!-- Vertical Mixer Bypass: connecting supply down to return -->
      <path d="M 340 180 L 340 330" class="pipe-hot" />

      <!-- Cold Return Pipe: Radiators bottom (vertical drop) -> Mixer -> Boiler -->
      <path d="M 720 310 L 720 380 L 340 380 L 340 330 L 230 330" class="pipe-cold" />
      <!-- Cold Return Branch: CWU bottom (vertical drop into return) -->
      <path d="M 520 360 L 520 380" class="pipe-cold" />

      <!-- ANIMATED PIPE FLOW OVERLAYS -->
      <!-- Flow to Radiators: full route including vertical connection -->
      <path
        d="M 230 180 L 400 180 L 400 110 L 720 110 L 720 180"
        stroke="#fca5a5"
        stroke-width="3"
        fill="none"
        class:pipe-flow={chPump || heatingState > 0}
      />
      <!-- Flow to CWU Tank -->
      <path
        d="M 400 180 L 520 180 L 520 200"
        stroke="#fca5a5"
        stroke-width="3"
        fill="none"
        class:pipe-flow={dhwPump}
      />
      <!-- Flow through Vertical Mixer Bypass -->
      <path
        d="M 340 180 L 340 330"
        stroke="#a5b4fc"
        stroke-width="3"
        fill="none"
        class:pipe-flow={mixerPump}
      />
      <!-- Return Flow from Radiators (flows from radiators back into boiler) -->
      <path
        d="M 720 310 L 720 380 L 340 380 L 340 330 L 230 330"
        stroke="#93c5fd"
        stroke-width="3"
        fill="none"
        class:pipe-flow={chPump || mixerPump}
      />
      <!-- Return Flow from CWU (flows from CWU down into return) -->
      <path
        d="M 520 360 L 520 380"
        stroke="#93c5fd"
        stroke-width="3"
        fill="none"
        class:pipe-flow={dhwPump}
      />

      <!-- ============================================== -->
      <!-- FUEL HOPPER & AUGER SCREW (Zasobnik i Ślimak)  -->
      <!-- ============================================== -->

      <!-- Zasobnik Opału (Fuel Hopper) -->
      <rect x="12" y="165" width="56" height="10" rx="2" fill="#334155" stroke="#64748b" stroke-width="1.5" />
      <polygon points="14,175 66,175 62,275 48,302 32,302 18,275" fill="#1e293b" stroke="#475569" stroke-width="1.5" />
      <polygon points="17,215 63,215 61,274 47,300 33,300 19,274" fill="#090d16" opacity="0.85" />
      <text x="40" y="195" fill="#94a3b8" font-size="9" font-weight="700" text-anchor="middle">ZASOBNIK</text>
      <text x="40" y="210" fill="var(--accent-flame)" font-size="11" font-weight="800" text-anchor="middle">{fuelPct}%</text>

      <!-- Feeder Tube (Rura podajnika ślimakowego) -->
      <rect x="35" y="302" width="105" height="24" rx="3" fill="#090d16" stroke="#475569" stroke-width="1.5" />

      <!-- Auger Screw (Ślimak) inside clipped tube -->
      <g clip-path="url(#feederTubeClip)">
        <!-- Shaft -->
        <line x1="30" y1="314" x2="140" y2="314" stroke="#64748b" stroke-width="3" stroke-linecap="round" />
        <!-- Helical screw coils (animates towards retort when feederActive) -->
        <g class:auger-active={feederActive}>
          <path
            d="M 20 305 Q 23 314 18 323 M 33 305 Q 36 314 31 323 M 46 305 Q 49 314 44 323 M 59 305 Q 62 314 57 323 M 72 305 Q 75 314 70 323 M 85 305 Q 88 314 83 323 M 98 305 Q 101 314 96 323 M 111 305 Q 114 314 109 323 M 124 305 Q 127 314 122 323 M 137 305 Q 140 314 135 323"
            stroke="#cbd5e1"
            stroke-width="2.5"
            fill="none"
            stroke-linecap="round"
          />
        </g>
      </g>

      <!-- Feeder Motor / Gearbox (Motoreduktor) -->
      <rect x="10" y="300" width="25" height="28" rx="4" fill="#334155" stroke={feederActive ? '#22c55e' : '#64748b'} stroke-width="1.5" />
      <line x1="16" y1="304" x2="16" y2="324" stroke="#475569" stroke-width="1.5" />
      <line x1="22" y1="304" x2="22" y2="324" stroke="#475569" stroke-width="1.5" />
      <circle cx="28" cy="314" r="3" fill={feederActive ? '#22c55e' : '#64748b'} />

      <!-- Feeder Temperature Sensor & Badge -->
      <rect x="90" y="296" width="4" height="7" fill="#f59e0b" />
      <rect x="68" y="266" width="56" height="20" rx="4" fill="#0f172a" stroke="#cbd5e1" stroke-width="1" />
      <text x="96" y="280" fill="#cbd5e1" font-size="10" font-weight="700" text-anchor="middle">
        {feederTemp !== null && feederTemp !== undefined ? `${feederTemp.toFixed(1)}°C` : '--°C'}
      </text>
      <text x="96" y="260" fill="#94a3b8" font-size="9" text-anchor="middle">Podajnik</text>

      <!-- BOILER (Kocioł eCoal) -->
      <rect x="70" y="140" width="160" height="230" rx="12" fill="url(#boilerGrad)" stroke="#475569" stroke-width="2" />
      <text x="150" y="170" fill="#94a3b8" font-size="14" font-weight="700" text-anchor="middle">KOCIOŁ eCoal</text>

      <!-- Combustion Chamber & Flame -->
      <rect x="95" y="240" width="110" height="110" rx="8" fill="#090d16" stroke="#f97316" stroke-width="1.5" />
      
      <!-- Cast Iron Burner Retort (Retorta podajnika) -->
      <path d="M 125 324 L 135 338 L 165 338 L 175 324 Z" fill="#334155" stroke="#94a3b8" stroke-width="1.5" />
      <ellipse cx="150" cy="324" rx="20" ry="4" fill="#f97316" opacity={isFlameActive ? '0.9' : '0.3'} />

      <!-- Animated Flame -->
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

      <!-- CWU PUMP (Pompa CWU na zasilaniu boilera przy x=450, y=180) -->
      <g class="pump-group" class:pump-active={dhwPump}>
        <circle cx="450" cy="180" r="15" fill="#0f172a" stroke="#0284c7" stroke-width="2" />
        <g>
          {#if dhwPump}
            <animateTransform
              attributeName="transform"
              type="rotate"
              from="0 450 180"
              to="360 450 180"
              dur="1.2s"
              repeatCount="indefinite"
            />
          {/if}
          <circle cx="450" cy="180" r="2.8" fill="#0284c7" />
          <path d="M 450 173 Q 453.5 176.5 450 180 Q 446.5 183.5 450 187 M 443 180 Q 446.5 176.5 450 180 Q 453.5 183.5 457 180" stroke="#0284c7" stroke-width="1.8" fill="none" stroke-linecap="round" />
        </g>
      </g>
      <text x="450" y="155" fill="#94a3b8" font-size="11" font-weight="600" text-anchor="middle">Pompa CWU</text>

      <!-- CO CIRCULATION PUMP (Pompa CO na zasilaniu grzejników przy x=580, y=110) -->
      <g class="pump-group" class:pump-active={chPump}>
        <circle cx="580" cy="110" r="16" fill="#0f172a" stroke="#ef4444" stroke-width="2" />
        <g>
          {#if chPump}
            <animateTransform
              attributeName="transform"
              type="rotate"
              from="0 580 110"
              to="360 580 110"
              dur="1.2s"
              repeatCount="indefinite"
            />
          {/if}
          <circle cx="580" cy="110" r="3" fill="#ef4444" />
          <path d="M 580 102 Q 584 106 580 110 Q 576 114 580 118 M 572 110 Q 576 106 580 110 Q 584 114 588 110" stroke="#ef4444" stroke-width="2" fill="none" stroke-linecap="round" />
        </g>
      </g>
      <text x="580" y="85" fill="#94a3b8" font-size="11" font-weight="600" text-anchor="middle">Pompa CO</text>

      <!-- RADIATORS (Grzejniki) -->
      <rect x="680" y="180" width="80" height="130" rx="6" fill="#1e293b" stroke="#cbd5e1" stroke-width="1.5" />
      <line x1="700" y1="195" x2="700" y2="295" stroke="#475569" stroke-width="2" />
      <line x1="720" y1="195" x2="720" y2="295" stroke="#475569" stroke-width="2" />
      <line x1="740" y1="195" x2="740" y2="295" stroke="#475569" stroke-width="2" />
      <text x="720" y="245" fill="#e2e8f0" font-size="12" font-weight="600" text-anchor="middle">GRZEJNIKI</text>

      <!-- VERTICAL MIXER PUMP (Pompa Mieszacza na pionowym bypassie przy x=340, y=255) -->
      <g class="pump-group" class:pump-active={mixerPump}>
        <circle cx="340" cy="255" r="15" fill="#0f172a" stroke="#6366f1" stroke-width="2" />
        <g>
          {#if mixerPump}
            <animateTransform
              attributeName="transform"
              type="rotate"
              from="0 340 255"
              to="360 340 255"
              dur="1.2s"
              repeatCount="indefinite"
            />
          {/if}
          <circle cx="340" cy="255" r="2.8" fill="#6366f1" />
          <path d="M 340 248 Q 343.5 251.5 340 255 Q 336.5 258.5 340 262 M 333 255 Q 336.5 251.5 340 255 Q 343.5 258.5 347 255" stroke="#6366f1" stroke-width="1.8" fill="none" stroke-linecap="round" />
        </g>
      </g>
      <text x="365" y="260" fill="#94a3b8" font-size="11" font-weight="600" text-anchor="start">Mieszacz</text>

      <!-- RETURN TEMPERATURE SENSOR BADGE (Powrót CO przed kotłem) -->
      <rect x="245" y="365" width="80" height="28" rx="6" fill="#1e293b" stroke="#3b82f6" stroke-width="1.5" />
      <text x="285" y="384" fill="#93c5fd" font-size="12" font-weight="700" text-anchor="middle">
        {returnTemp !== null && returnTemp !== undefined ? `${returnTemp.toFixed(1)}°C` : '--°C'}
      </text>
      <text x="285" y="410" fill="#94a3b8" font-size="11" text-anchor="middle">Powrót CO</text>

      <!-- OUTDOOR SENSOR BADGE -->
      <rect x="670" y="20" width="110" height="32" rx="6" fill="#0f172a" stroke="#38bdf8" stroke-width="1.5" />
      <text x="680" y="41" fill="#38bdf8" font-size="13">🌡️</text>
      <text x="735" y="41" fill="#f8fafc" font-size="13" font-weight="700" text-anchor="middle">
        {outdoorTemp !== null && outdoorTemp !== undefined ? `${outdoorTemp.toFixed(1)}°C` : '--°C'}
      </text>
    </svg>
  </div>
</div>
