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
    floorTemp = null,
    mixerCircuit = null,
    hasMixer = undefined,
    fuelPct = 0,
    fuelKg = null,
    chPump = false,
    dhwPump = false,
    mixerPump = false,
    circulationPump = false,
    blowerActive = false,
    blowerPower = 0,
    feederActive = false,
    heatingState = 0,
  } = $props();

  let isMixerConfigured = $derived(
    hasMixer !== undefined
      ? !!hasMixer
      : (mixerCircuit !== null && mixerCircuit !== undefined ? mixerCircuit > 0 : mixerPump)
  );

  let isFloorMode = $derived(
    mixerCircuit === 2 || (mixerCircuit === null && !mixerPump)
  );
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
    <svg class="schematic-svg" viewBox="0 0 820 540" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <!-- Gradients -->
        <linearGradient id="boilerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#334155" />
          <stop offset="100%" stop-color="#1e293b" />
        </linearGradient>
        <linearGradient id="cwuGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#1e293b" />
          <stop offset="50%" stop-color="#0284c7" stop-opacity="0.3" />
          <stop offset="100%" stop-color="#1e293b" />
        </linearGradient>
        <linearGradient id="flameGrad" x1="0%" y1="100%" x2="0%" y2="0%">
          <stop offset="0%" stop-color="#dc2626" />
          <stop offset="60%" stop-color="#f97316" />
          <stop offset="100%" stop-color="#fef08a" />
        </linearGradient>

        <!-- Clip path for feeder screw auger tube -->
        <clipPath id="feederTubeClip">
          <rect x="36" y="283" width="94" height="22" rx="2" />
        </clipPath>
      </defs>

      <!-- ============================================== -->
      <!-- PIPES: Static Background Lines (NO CROSSINGS)  -->
      <!-- ============================================== -->

      <!-- Main Boiler Hot Supply Header: Boiler -> Vertical Riser (330) -->
      <path d="M 255 165 L 330 165" class="pipe-hot" />

      <!-- Vertical Supply Riser: connects CWU (80) -> Radiators (230) -->
      <path d="M 330 80 L 330 230" class="pipe-hot" />

      <!-- Hot Supply Branch 1 (TOP): to Bojler CWU -->
      <path d="M 330 80 L 480 80" class="pipe-hot" />

      <!-- Hot Supply Branch 2 (MIDDLE): to Grzejniki CO -->
      <path d="M 330 230 L 520 230" class="pipe-hot" />

      {#if isMixerConfigured}
        <!-- Extended Supply Riser to Bottom Circuit (Floor / Mixer) -->
        <path d="M 330 230 L 330 390" stroke="#818cf8" stroke-width="4.5" fill="none" stroke-linecap="round" />
        <!-- Hot Supply Branch 3 (BOTTOM): to Podłogówka / Mieszacz -->
        <path d="M 330 390 L 520 390" stroke="#818cf8" stroke-width="4.5" fill="none" stroke-linecap="round" />
        <!-- Floor / Mixer Return Branch into CO Riser (775) -->
        <path d="M 720 420 L 775 420" stroke="#3b82f6" stroke-width="4.5" fill="none" stroke-linecap="round" />
      {/if}

      <!-- ============================================== -->
      <!-- RETURN PIPES: MERGED RETURN COLLECTOR          -->
      <!-- ============================================== -->

      <!-- Return Circuit 1: Bojler CWU Riser down to collector (745, 475) -->
      <path d="M 610 130 L 745 130 L 745 475" class="pipe-cold" stroke="#0284c7" />

      <!-- Return Circuit 2: Grzejniki CO Riser down to collector (775, 475) -->
      <path d="M 720 255 L 775 255 L 775 475" class="pipe-cold" />

      <!-- Common Return Collector: Merges CWU & CO into Boiler Return Stub (255, 345) -->
      <path d="M 775 475 L 275 475 L 275 345 L 255 345" class="pipe-cold" stroke-width="5" />

      <!-- Pipe Labels for Returns -->
      <text x="675" y="122" fill="#38bdf8" font-size="9" font-weight="700" text-anchor="middle">Powrót CWU</text>
      <text x="750" y="247" fill="#93c5fd" font-size="9" font-weight="700" text-anchor="middle">Powrót CO</text>
      <text x="510" y="492" fill="#64748b" font-size="8.5" font-weight="600" text-anchor="middle">Wspólny kolektor powrotny do kotła</text>

      <!-- ============================================== -->
      <!-- ANIMATED PIPE FLOW OVERLAYS                    -->
      <!-- ============================================== -->

      <!-- Supply Flow 1: Boiler -> Pompa CWU -> Bojler CWU -->
      <path
        d="M 255 165 L 330 165 L 330 80 L 480 80"
        stroke="#fca5a5"
        stroke-width="3"
        fill="none"
        class:pipe-flow={dhwPump}
      />

      <!-- Supply Flow 2: Boiler -> Pompa CO -> Grzejniki -->
      <path
        d="M 255 165 L 330 165 L 330 230 L 520 230"
        stroke="#fca5a5"
        stroke-width="3"
        fill="none"
        class:pipe-flow={chPump || heatingState > 0}
      />

      {#if isMixerConfigured}
        <!-- Supply Flow 3: Boiler -> Pompa Podłogowa -> Podłogówka / Mieszacz -->
        <path
          d="M 255 165 L 330 165 L 330 390 L 520 390"
          stroke="#c7d2fe"
          stroke-width="2.5"
          fill="none"
          class:pipe-flow={mixerPump}
        />

        <!-- Return Flow 3: Podłogówka / Mieszacz -> Collector -> Boiler -->
        <path
          d="M 720 420 L 775 420 L 775 475 L 275 475 L 275 345 L 255 345"
          stroke="#818cf8"
          stroke-width="2.5"
          fill="none"
          class:pipe-flow={mixerPump}
        />
      {/if}

      <!-- Return Flow 1: CWU Tank -> Collector -> Boiler -->
      <path
        d="M 610 130 L 745 130 L 745 475 L 275 475 L 275 345 L 255 345"
        stroke="#38bdf8"
        stroke-width="3"
        fill="none"
        class:pipe-flow={dhwPump}
      />

      <!-- Return Flow 2: Grzejniki -> Collector -> Boiler -->
      <path
        d="M 720 255 L 775 255 L 775 475 L 275 475 L 275 345 L 255 345"
        stroke="#93c5fd"
        stroke-width="3"
        fill="none"
        class:pipe-flow={chPump}
      />

      <!-- ============================================== -->
      <!-- FUEL HOPPER & AUGER SCREW (Zasobnik i Ślimak)  -->
      <!-- ============================================== -->

      <!-- Zasobnik Opału (Fuel Hopper) -->
      <rect x="18" y="145" width="56" height="10" rx="2" fill="#334155" stroke="#64748b" stroke-width="1.5" />
      <polygon points="20,155 72,155 68,255 54,282 38,282 24,255" fill="#1e293b" stroke="#475569" stroke-width="1.5" />
      <polygon points="23,195 69,195 67,254 53,280 39,280 25,254" fill="#090d16" opacity="0.85" />
      <text x="46" y="172" fill="#94a3b8" font-size="8.5" font-weight="700" text-anchor="middle">ZASOBNIK</text>
      <text x="46" y="187" fill="var(--accent-flame)" font-size="11.5" font-weight="800" text-anchor="middle">
        {fuelKg != null ? `${fuelKg} kg` : `${fuelPct}%`}
      </text>
      <text x="46" y="200" fill="#cbd5e1" font-size="9" font-weight="700" text-anchor="middle">
        {fuelPct}%
      </text>

      <!-- Feeder Tube (Rura podajnika ślimakowego) -->
      <rect x="35" y="282" width="105" height="24" rx="3" fill="#090d16" stroke="#475569" stroke-width="1.5" />

      <!-- Auger Screw (Ślimak) inside clipped tube -->
      <g clip-path="url(#feederTubeClip)">
        <line x1="30" y1="294" x2="140" y2="294" stroke="#64748b" stroke-width="3" stroke-linecap="round" />
        <g class:auger-active={feederActive}>
          <path
            d="M 20 285 Q 23 294 18 303 M 33 285 Q 36 294 31 303 M 46 285 Q 49 294 44 303 M 59 285 Q 62 294 57 303 M 72 285 Q 75 294 70 303 M 85 285 Q 88 294 83 303 M 98 285 Q 101 294 96 303 M 111 285 Q 114 294 109 303 M 124 285 Q 127 294 122 303 M 137 285 Q 140 294 135 303"
            stroke="#cbd5e1"
            stroke-width="2.5"
            fill="none"
            stroke-linecap="round"
          />
        </g>
      </g>

      <!-- Feeder Motor / Gearbox (Motoreduktor) -->
      <rect x="10" y="280" width="25" height="28" rx="4" fill="#334155" stroke={feederActive ? '#22c55e' : '#64748b'} stroke-width="1.5" />
      <line x1="16" y1="284" x2="16" y2="304" stroke="#475569" stroke-width="1.5" />
      <line x1="22" y1="284" x2="22" y2="304" stroke="#475569" stroke-width="1.5" />
      <circle cx="28" cy="294" r="3" fill={feederActive ? '#22c55e' : '#64748b'} />

      <!-- Sensor probe line & badge on feeder tube -->
      <line x1="60" y1="244" x2="60" y2="282" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="2 2" />
      <circle cx="60" cy="282" r="3.5" fill="#f59e0b" stroke="#0f172a" stroke-width="1" />
      <rect x="29" y="222" width="62" height="22" rx="4" fill="#0f172a" stroke="#f59e0b" stroke-width="1.5" />
      <text x="60" y="218" fill="#94a3b8" font-size="9" font-weight="700" text-anchor="middle">Podajnik</text>
      <text x="60" y="237" fill="#f59e0b" font-size="11" font-weight="800" text-anchor="middle">
        {feederTemp !== null && feederTemp !== undefined ? `${feederTemp.toFixed(1)}°C` : '--°C'}
      </text>

      <!-- ============================================== -->
      <!-- BLOWER FAN (Dmuchawa nadmuchowa WPA)           -->
      <!-- ============================================== -->
      <rect x="36" y="326" width="36" height="36" rx="8" fill="#1e293b" stroke={blowerActive ? '#06b6d4' : '#64748b'} stroke-width="1.8" />
      <polygon points="68,332 95,336 95,346 68,350" fill="#334155" stroke={blowerActive ? '#06b6d4' : '#475569'} stroke-width="1.2" />
      
      <circle cx="54" cy="344" r="12" fill="#0f172a" stroke={blowerActive ? '#06b6d4' : '#64748b'} stroke-width="1.5" />
      <g>
        {#if blowerActive}
          <animateTransform
            attributeName="transform"
            type="rotate"
            from="0 54 344"
            to="360 54 344"
            dur="0.9s"
            repeatCount="indefinite"
          />
        {/if}
        <circle cx="54" cy="344" r="2.5" fill={blowerActive ? '#06b6d4' : '#94a3b8'} />
        <path
          d="M 54 335 Q 57 339.5 54 344 Q 51 348.5 54 353 M 45 344 Q 49.5 341 54 344 Q 58.5 347 63 344"
          stroke={blowerActive ? '#06b6d4' : '#94a3b8'}
          stroke-width="1.8"
          fill="none"
          stroke-linecap="round"
        />
      </g>

      {#if blowerActive}
        <path d="M 95 341 L 130 341 L 140 322" stroke="#67e8f9" stroke-width="2" stroke-dasharray="3 3" fill="none" class="pipe-flow" />
      {/if}

      <text x="54" y="376" fill="#94a3b8" font-size="9" font-weight="600" text-anchor="middle">Dmuchawa</text>
      <rect x="36" y="381" width="36" height="18" rx="4" fill="#0f172a" stroke={blowerActive ? '#06b6d4' : '#475569'} stroke-width="1.2" />
      <text x="54" y="394" fill={blowerActive ? '#06b6d4' : '#94a3b8'} font-size="10" font-weight="800" text-anchor="middle">
        {blowerPower}%
      </text>

      <!-- ============================================== -->
      <!-- BOILER (Kocioł eCoal)                          -->
      <!-- ============================================== -->
      <rect x="95" y="110" width="160" height="270" rx="14" fill="url(#boilerGrad)" stroke="#475569" stroke-width="2" />
      <text x="175" y="138" fill="#94a3b8" font-size="13" font-weight="700" text-anchor="middle">KOCIOŁ eCoal</text>

      <!-- Flue Gas Pipe & Sensor -->
      <path d="M 135 110 L 135 55 L 75 55" stroke="#64748b" stroke-width="12" stroke-linecap="round" fill="none" />
      <circle cx="135" cy="70" r="14" fill="#1e293b" stroke="#f97316" stroke-width="2" />
      <text x="135" y="74" fill="#f8fafc" font-size="10" font-weight="700" text-anchor="middle">
        {exhaustTemp !== null && exhaustTemp !== undefined ? `${exhaustTemp.toFixed(1)}°C` : '--°C'}
      </text>
      <text x="135" y="40" fill="#94a3b8" font-size="10" text-anchor="middle">Spaliny</text>

      <!-- Combustion Chamber & Flame -->
      <rect x="120" y="220" width="110" height="120" rx="8" fill="#090d16" stroke="#f97316" stroke-width="1.5" />
      <path d="M 150 310 L 160 324 L 190 324 L 200 310 Z" fill="#334155" stroke="#94a3b8" stroke-width="1.5" />
      <ellipse cx="175" cy="310" rx="22" ry="4" fill="#f97316" opacity={isFlameActive ? '0.9' : '0.3'} />

      <!-- Animated Flame -->
      <g class="flame-anim" class:flame-inactive={!isFlameActive}>
        <path d="M 175 240 C 155 265 140 292 150 315 C 160 330 190 330 200 315 C 210 292 195 265 175 240 Z" fill="url(#flameGrad)" />
        <path d="M 175 260 C 165 275 155 295 163 312 C 170 322 180 322 187 312 C 195 295 185 275 175 260 Z" fill="#fef08a" />
      </g>

      <!-- Boiler Temp Badge -->
      <rect x="120" y="148" width="110" height="48" rx="8" fill="#0f172a" stroke="#ef4444" stroke-width="1.8" />
      <text x="175" y="167" fill="#f8fafc" font-size="13" font-weight="800" text-anchor="middle">
        {boilerTemp !== null && boilerTemp !== undefined ? `${boilerTemp.toFixed(1)}°C` : '--°C'}
      </text>
      <text x="175" y="187" fill="#fb923c" font-size="13" font-weight="800" text-anchor="middle">
        {targetBoilerTemp ? `Zad: ${targetBoilerTemp}°C` : 'Zasilanie CO'}
      </text>

      <!-- ============================================== -->
      <!-- TOP RECEIVER: BOJLER CWU (Zasobnik Ciepłej Wody) -->
      <!-- ============================================== -->
      <!-- Pompa CWU na gałęzi zasilania (405, 80) -->
      <g class="pump-group" class:pump-active={dhwPump}>
        <circle cx="405" cy="80" r="14" fill="#0f172a" stroke="#0284c7" stroke-width="2" />
        <g>
          {#if dhwPump}
            <animateTransform
              attributeName="transform"
              type="rotate"
              from="0 405 80"
              to="360 405 80"
              dur="1.2s"
              repeatCount="indefinite"
            />
          {/if}
          <circle cx="405" cy="80" r="2.5" fill="#0284c7" />
          <path d="M 405 73 Q 408 76.5 405 80 Q 402 83.5 405 87 M 398 80 Q 401.5 76.5 405 80 Q 408.5 83.5 412 80" stroke="#0284c7" stroke-width="1.6" fill="none" stroke-linecap="round" />
        </g>
      </g>
      <text x="405" y="58" fill="#94a3b8" font-size="10" font-weight="600" text-anchor="middle">Pompa CWU</text>

      <!-- Bojler CWU Tank -->
      <rect x="480" y="40" width="130" height="110" rx="18" fill="url(#cwuGrad)" stroke="#0284c7" stroke-width="2" />
      <text x="545" y="62" fill="#94a3b8" font-size="11" font-weight="700" text-anchor="middle">BOJLER CWU</text>

      <!-- Internal Continuous Heating Coil (Wężownica grzewcza ładowania CWU) -->
      <path
        d="M 480 80 Q 525 80 525 93 Q 495 104 525 115 Q 560 120 570 130 L 610 130"
        stroke="#f97316"
        stroke-width="2.8"
        fill="none"
        stroke-linecap="round"
      />
      <text x="535" y="142" fill="#64748b" font-size="8" text-anchor="middle">wężownica grzewcza</text>

      <!-- CWU Temp Badge inside Tank -->
      <rect x="490" y="66" width="110" height="46" rx="8" fill="#0f172a" stroke="#0284c7" stroke-width="1.8" />
      <text x="545" y="84" fill="#38bdf8" font-size="13" font-weight="800" text-anchor="middle">
        {dhwTemp !== null && dhwTemp !== undefined ? `${dhwTemp.toFixed(1)}°C` : '--°C'}
      </text>
      <text x="545" y="103" fill="#93c5fd" font-size="13" font-weight="800" text-anchor="middle">
        {targetDhwTemp ? `Zad: ${targetDhwTemp}°C` : 'Woda w bojlerze'}
      </text>

      <!-- Label on the return pipe from CWU heating to boiler -->
      <text x="675" y="122" fill="#38bdf8" font-size="9" font-weight="700" text-anchor="middle">Powrót CWU</text>

      <!-- Domestic Water Tap & Circulation Loop (Upper zone: y = 18..65) -->
      <path d="M 560 40 L 560 18 L 638 18" stroke="#f59e0b" stroke-width="3" fill="none" stroke-linecap="round" />
      <text x="640" y="15" font-size="12" text-anchor="middle">🚰</text>

      <!-- Circulation Return Pipe: Tap -> Pump -> CWU Tank (enters tank at y = 65) -->
      <path
        d="M 648 18 L 668 18 L 668 65 L 610 65"
        stroke="#d97706"
        stroke-width="2"
        stroke-dasharray="3 3"
        fill="none"
        stroke-linecap="round"
      />

      {#if circulationPump}
        <path
          d="M 560 40 L 560 18 L 668 18 L 668 65 L 610 65"
          stroke="#fde68a"
          stroke-width="1.8"
          fill="none"
          stroke-linecap="round"
          class="pipe-flow"
        />
      {/if}

      <!-- Circulation Pump (Z1) -->
      <g class="pump-group" class:pump-active={circulationPump}>
        <circle cx="668" cy="42" r="10" fill="#0f172a" stroke="#f59e0b" stroke-width="1.6" />
        <g>
          {#if circulationPump}
            <animateTransform
              attributeName="transform"
              type="rotate"
              from="0 668 42"
              to="360 668 42"
              dur="1.2s"
              repeatCount="indefinite"
            />
          {/if}
          <circle cx="668" cy="42" r="2" fill="#f59e0b" />
          <path d="M 668 36 Q 670 39 668 42 Q 666 45 668 48 M 662 42 Q 665 40 668 42 Q 671 44 674 42" stroke="#f59e0b" stroke-width="1.3" fill="none" stroke-linecap="round" />
        </g>
      </g>
      <text x="668" y="58" fill="#94a3b8" font-size="8" font-weight="600" text-anchor="middle">Cyrkulacja</text>

      <!-- ============================================== -->
      <!-- MIDDLE RECEIVER: GRZEJNIKI CO (Kaloryfery)     -->
      <!-- ============================================== -->
      <!-- Pompa CO na gałęzi zasilania (425, 230) -->
      <g class="pump-group" class:pump-active={chPump}>
        <circle cx="425" cy="230" r="15" fill="#0f172a" stroke="#ef4444" stroke-width="2" />
        <g>
          {#if chPump}
            <animateTransform
              attributeName="transform"
              type="rotate"
              from="0 425 230"
              to="360 425 230"
              dur="1.2s"
              repeatCount="indefinite"
            />
          {/if}
          <circle cx="425" cy="230" r="2.8" fill="#ef4444" />
          <path d="M 425 222 Q 429 226 425 230 Q 421 234 425 238 M 417 230 Q 421 226 425 230 Q 429 234 433 230" stroke="#ef4444" stroke-width="1.8" fill="none" stroke-linecap="round" />
        </g>
      </g>
      <text x="425" y="206" fill="#94a3b8" font-size="10" font-weight="600" text-anchor="middle">Pompa CO</text>

      <!-- Grzejniki Panelowe -->
      <rect x="520" y="185" width="200" height="95" rx="8" fill="#1e293b" stroke="#cbd5e1" stroke-width="1.5" />
      <text x="535" y="205" fill="#cbd5e1" font-size="11" font-weight="700">🛋️ GRZEJNIKI CO</text>
      <line x1="535" y1="215" x2="705" y2="215" stroke="#475569" stroke-width="2" />
      <line x1="535" y1="265" x2="705" y2="265" stroke="#475569" stroke-width="2" />
      
      <!-- Convector ribs -->
      <line x1="550" y1="215" x2="550" y2="265" stroke="#64748b" stroke-width="3" stroke-linecap="round" />
      <line x1="570" y1="215" x2="570" y2="265" stroke="#64748b" stroke-width="3" stroke-linecap="round" />
      <line x1="590" y1="215" x2="590" y2="265" stroke="#64748b" stroke-width="3" stroke-linecap="round" />
      <line x1="610" y1="215" x2="610" y2="265" stroke="#64748b" stroke-width="3" stroke-linecap="round" />
      <line x1="630" y1="215" x2="630" y2="265" stroke="#64748b" stroke-width="3" stroke-linecap="round" />
      <line x1="650" y1="215" x2="650" y2="265" stroke="#64748b" stroke-width="3" stroke-linecap="round" />
      <line x1="670" y1="215" x2="670" y2="265" stroke="#64748b" stroke-width="3" stroke-linecap="round" />
      <line x1="690" y1="215" x2="690" y2="265" stroke="#64748b" stroke-width="3" stroke-linecap="round" />

      <!-- ============================================== -->
      <!-- BOTTOM RECEIVER: PODŁOGÓWKA LUB MIESZACZ 3D    -->
      <!-- ============================================== -->
      {#if isMixerConfigured}
        <!-- Pompa Podłogowa / Mieszacza na gałęzi dolnej (425, 390) -->
        <g class="pump-group" class:pump-active={mixerPump}>
          <circle cx="425" cy="390" r="15" fill="#0f172a" stroke={isFloorMode ? '#6366f1' : '#3b82f6'} stroke-width="2" />
          <g>
            {#if mixerPump}
              <animateTransform
                attributeName="transform"
                type="rotate"
                from="0 425 390"
                to="360 425 390"
                dur="1.2s"
                repeatCount="indefinite"
              />
            {/if}
            <circle cx="425" cy="390" r="2.8" fill={isFloorMode ? '#6366f1' : '#3b82f6'} />
            <path
              d="M 425 382 Q 429 386 425 390 Q 421 394 425 398 M 417 390 Q 421 386 425 390 Q 429 394 433 390"
              stroke={isFloorMode ? '#6366f1' : '#3b82f6'}
              stroke-width="1.8"
              fill="none"
              stroke-linecap="round"
            />
          </g>
        </g>
        <text x="425" y="366" fill="#94a3b8" font-size="10" font-weight="600" text-anchor="middle">
          {isFloorMode ? 'Pompa Podłogi' : 'Pompa Mieszacza'}
        </text>

        {#if isFloorMode}
          <!-- WARIANT A: OGRZEWANIE PODŁOGOWE (Pętle PEX w wylewce) -->
          <rect x="520" y="335" width="200" height="120" rx="8" fill="#1e293b" stroke="#6366f1" stroke-width="1.8" />
          
          <!-- Top Header Strip -->
          <rect x="520" y="335" width="200" height="26" rx="8 8 0 0" fill="#0f172a" />
          <text x="532" y="353" fill="#818cf8" font-size="12">♨️</text>
          <text x="552" y="353" fill="#cbd5e1" font-size="10.5" font-weight="700">PODŁOGÓWKA</text>

          <!-- Floor Temperature Sensor Badge -->
          <rect x="630" y="339" width="85" height="18" rx="4" fill="#0f172a" stroke="#818cf8" stroke-width="1.5" />
          <text x="672" y="352" fill="#c7d2fe" font-size={floorTemp != null ? '10.5' : '8.5'} font-weight="800" text-anchor="middle">
            {floorTemp !== null && floorTemp !== undefined ? `${floorTemp.toFixed(1)}°C` : 'Brak czujnika'}
          </text>

          <!-- Floor Screed & Tile Grid Texture -->
          <line x1="535" y1="392" x2="705" y2="392" stroke="#334155" stroke-dasharray="2 5" stroke-width="1" />
          <line x1="535" y1="422" x2="705" y2="422" stroke="#334155" stroke-dasharray="2 5" stroke-width="1" />
          <line x1="590" y1="365" x2="590" y2="450" stroke="#334155" stroke-dasharray="2 5" stroke-width="1" />
          <line x1="650" y1="365" x2="650" y2="450" stroke="#334155" stroke-dasharray="2 5" stroke-width="1" />

          <!-- Realistic PEX Serpentine Loops (Wężownica grzewcza) -->
          <path
            d="M 525 380 L 695 380 Q 705 380 705 395 Q 705 410 695 410 L 545 410 Q 535 410 535 425 Q 535 440 545 440 L 705 440 L 720 420"
            stroke="#818cf8"
            stroke-width="3"
            fill="none"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <!-- Animated PEX Water Flow overlay -->
          <path
            d="M 525 380 L 695 380 Q 705 380 705 395 Q 705 410 695 410 L 545 410 Q 535 410 535 425 Q 535 440 545 440 L 705 440 L 720 420"
            stroke="#c7d2fe"
            stroke-width="2.2"
            fill="none"
            stroke-linecap="round"
            stroke-linejoin="round"
            class:pipe-flow={mixerPump}
          />
        {:else}
          <!-- WARIANT B: MIESZACZ 3D / OCHRONA POWROTU -->
          <rect x="520" y="335" width="200" height="120" rx="8" fill="#1e293b" stroke="#3b82f6" stroke-width="1.8" />
          
          <!-- Top Header Strip -->
          <rect x="520" y="335" width="200" height="26" rx="8 8 0 0" fill="#0f172a" />
          <text x="532" y="353" fill="#60a5fa" font-size="12">🔀</text>
          <text x="552" y="353" fill="#cbd5e1" font-size="10.5" font-weight="700">MIESZACZ 3D / CO</text>

          <!-- Temperature Badge -->
          <rect x="630" y="339" width="85" height="18" rx="4" fill="#0f172a" stroke="#3b82f6" stroke-width="1.5" />
          <text x="672" y="352" fill="#93c5fd" font-size={floorTemp != null ? '10.5' : '8.5'} font-weight="800" text-anchor="middle">
            {floorTemp !== null && floorTemp !== undefined ? `${floorTemp.toFixed(1)}°C` : 'Brak czujnika'}
          </text>

          <!-- 3-Way Valve Bow-Tie Geometry -->
          <path d="M 585 400 L 610 388 L 610 412 Z M 635 400 L 610 388 L 610 412 Z" fill="#334155" stroke="#60a5fa" stroke-width="1.5" />
          <circle cx="610" cy="400" r="3.5" fill="#60a5fa" />
          <!-- Actuator Motor -->
          <rect x="602" y="373" width="16" height="12" rx="2" fill="#0f172a" stroke="#60a5fa" stroke-width="1.2" />
          <text x="610" y="382" fill="#60a5fa" font-size="8.5" font-weight="800" text-anchor="middle">M</text>
          
          <!-- Mixing Line into Output -->
          <path d="M 520 390 L 585 400" stroke="#818cf8" stroke-width="2.5" fill="none" stroke-linecap="round" />
          <path d="M 635 400 L 720 420" stroke="#60a5fa" stroke-width="2.5" fill="none" stroke-linecap="round" />

          <!-- Return Bypass Line -->
          <path d="M 610 412 L 610 442 L 720 442 L 720 420" stroke="#38bdf8" stroke-width="2.5" stroke-dasharray="3 3" fill="none" stroke-linecap="round" />
          <text x="635" y="427" fill="#94a3b8" font-size="9" font-weight="600">Zawór trójdrogowy 3D</text>
          <text x="635" y="439" fill="#64748b" font-size="8">Ochrona powrotu kotła</text>
        {/if}
      {/if}

      <!-- ============================================== -->
      <!-- RETURN TEMPERATURE SENSOR & OUTDOOR SENSOR     -->
      <!-- ============================================== -->
      <!-- Return Temperature Sensor Badge (Boiler Common Return Stub 275, 345) -->
      <line x1="315" y1="450" x2="275" y2="345" stroke="#3b82f6" stroke-dasharray="2 2" stroke-width="1.2" />
      <circle cx="275" cy="345" r="3.5" fill="#3b82f6" />
      <rect x="305" y="440" width="130" height="34" rx="6" fill="#0f172a" stroke="#3b82f6" stroke-width="1.5" />
      <text x="370" y="453" fill="#94a3b8" font-size="7.5" font-weight="700" text-anchor="middle">TEMPERATURA POWROTU</text>
      <text x="370" y="466" fill="#93c5fd" font-size="12" font-weight="800" text-anchor="middle">
        {returnTemp !== null && returnTemp !== undefined ? `${returnTemp.toFixed(1)}°C` : '--°C'}
      </text>
      <text x="370" y="478" fill="#64748b" font-size="7" font-weight="600" text-anchor="middle">Wspólny powrót kotła</text>

      <!-- Outdoor Temperature Sensor Badge (Top Right) -->
      <rect x="695" y="15" width="110" height="30" rx="6" fill="#0f172a" stroke="#38bdf8" stroke-width="1.5" />
      <text x="708" y="35" fill="#38bdf8" font-size="13">🌡️</text>
      <text x="758" y="35" fill="#f8fafc" font-size="12.5" font-weight="700" text-anchor="middle">
        {outdoorTemp !== null && outdoorTemp !== undefined ? `${outdoorTemp.toFixed(1)}°C` : '--°C'}
      </text>
    </svg>
  </div>
</div>
