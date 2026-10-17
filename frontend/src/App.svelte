<script>
  import { onMount, onDestroy } from 'svelte';
  import Dashboard from './components/Dashboard.svelte';
  import ParamsTab from './components/ParamsTab.svelte';
  import SchedulesTab from './components/SchedulesTab.svelte';
  import {
    EcoalClient,
    HttpTransportAdapter,
    MockTransportAdapter,
    SerialTransportAdapter,
  } from '@ecoal/adapter.js';

  const ALARM_DESCRIPTIONS = {
    1: 'Błąd czujnika temperatury kotła (CO)',
    2: 'Przekroczona maksymalna temperatura kotła (>85°C)',
    4: 'Przekroczona temperatura podajnika (>65°C)',
    8: 'Brak opału w zasobniku / wygaszenie',
    16: 'Zacięcie podajnika / zerwana zawleczka ślimaka',
    32: 'Błąd czujnika temperatury podajnika',
    64: 'Błąd czujnika temperatury CWU',
    128: 'Błąd czujnika temperatury spalin',
    256: 'Błąd czujnika temperatury powrotu',
    512: 'Zewnętrzny styk alarmowy rozwarty',
  };

  let client = new EcoalClient();
  let status = $state(null);
  let connected = $state(false);
  let connLabel = $state('Łączenie...');
  let activeTab = $state('dashboard');
  let selectedTransport = $state('auto');
  let paramsCache = $state({});
  let toasts = $state([]);
  let pollTimer = null;

  let activeAlarmsText = $derived.by(() => {
    if (!status?.alarm_active || !status?.alarms_raw) return '';
    const messages = [];
    for (const [mask, desc] of Object.entries(ALARM_DESCRIPTIONS)) {
      if ((status.alarms_raw & parseInt(mask, 10)) !== 0) {
        messages.push(desc);
      }
    }
    return messages.length > 0 ? messages.join(' | ') : `Kod alarmu: 0x${status.alarms_raw.toString(16)}`;
  });

  onMount(() => {
    setupTransport();
    fetchStatus();
    pollTimer = setInterval(fetchStatus, 3000);
  });

  onDestroy(() => {
    if (pollTimer) clearInterval(pollTimer);
  });

  function setupTransport(type = null) {
    const urlParams = new URLSearchParams(window.location.search);
    const transportType = type || urlParams.get('transport') || localStorage.getItem('ecoal_transport') || 'auto';
    const customHost = urlParams.get('host') || localStorage.getItem('ecoal_host') || '';
    selectedTransport = transportType;

    if (transportType === 'mock' || urlParams.get('mock') === '1') {
      client.setAdapter(new MockTransportAdapter());
      connLabel = 'Symulator Mock';
    } else if (transportType === 'serial') {
      client.setAdapter(new SerialTransportAdapter());
      connLabel = 'Web Serial API';
    } else if (transportType === 'direct' && customHost) {
      client.setAdapter(new HttpTransportAdapter(customHost.startsWith('http') ? customHost : `http://${customHost}`));
      connLabel = `Bezpośredni: ${customHost}`;
    } else {
      // Auto-detect: if in Home Assistant or direct port
      if (
        window.location.pathname.includes('/ecoal') ||
        window.location.port === '8123' ||
        window.location.pathname.includes('/api/ecoal')
      ) {
        client.setAdapter(new HttpTransportAdapter('/api/ecoal'));
        connLabel = 'Home Assistant Proxy';
      } else {
        client.setAdapter(new HttpTransportAdapter(''));
        connLabel = 'Połączenie HTTP';
      }
    }
  }

  function handleTransportChange(e) {
    const newTransport = e.target.value;
    localStorage.setItem('ecoal_transport', newTransport);
    setupTransport(newTransport);
    fetchStatus();
  }

  async function fetchStatus() {
    try {
      const res = await client.getStatus();
      if (res && (res.boiler_temp !== undefined || res.heating !== undefined)) {
        status = res;
        connected = true;
      } else {
        connected = false;
      }
    } catch (err) {
      connected = false;
    }
  }

  async function handleStepSetpoint(type, delta) {
    if (!status) return;
    if (type === 'co') {
      const current = status.target_boiler_temp || 55;
      const next = Math.max(45, Math.min(80, current + delta));
      status.target_boiler_temp = next;
      const ok = await client.setTargetBoilerTemp(next);
      if (ok) showToast(`Zadana temperatura CO: ${next}°C`, 'success');
      else showToast('Błąd zapisu temperatury CO', 'error');
    } else if (type === 'cwu') {
      const current = status.target_dhw_temp || 50;
      const next = Math.max(35, Math.min(65, current + delta));
      status.target_dhw_temp = next;
      const ok = await client.setTargetDhwTemp(next);
      if (ok) showToast(`Zadana temperatura CWU: ${next}°C`, 'success');
      else showToast('Błąd zapisu temperatury CWU', 'error');
    }
  }

  async function handleRefillHopper() {
    if (!confirm('Czy na pewno chcesz zresetować licznik zasypu do 100%?')) return;
    try {
      const ok = await client.refillHopper(150);
      if (ok) {
        showToast('Zresetowano licznik zasypu do 100%', 'success');
        await fetchStatus();
      } else {
        showToast('Błąd zapisu resetowania zasypu', 'error');
      }
    } catch (err) {
      showToast(`Wyjątek: ${err.message}`, 'error');
    }
  }

  async function handleSetFeederMode(mode) {
    try {
      const ok = await client.setFeederMode(mode);
      if (ok) {
        if (status) status.feeder_mode = mode;
        showToast('Zmieniono tryb pracy podajnika', 'success');
      } else {
        showToast('Błąd zapisu trybu podajnika', 'error');
      }
    } catch (err) {
      showToast(`Wyjątek: ${err.message}`, 'error');
    }
  }

  async function handleAckAlarm() {
    try {
      const ok = await client.ackAlarms();
      if (ok) {
        showToast('Skasowano aktywne alarmy kotła', 'success');
        await fetchStatus();
      } else {
        showToast('Błąd kasowania alarmów', 'error');
      }
    } catch (err) {
      showToast(`Wyjątek: ${err.message}`, 'error');
    }
  }

  function showToast(message, type = 'info') {
    const id = Date.now() + Math.random();
    toasts = [...toasts, { id, message, type }];
    setTimeout(() => {
      toasts = toasts.filter((t) => t.id !== id);
    }, 3200);
  }
</script>

<!-- Header -->
<header class="app-header">
  <div class="brand">
    <span class="brand-icon">🔥</span>
    <h1>eCoal Control</h1>
    <span class="brand-badge">Svelte 5</span>
  </div>
  <div class="header-status">
    <div class="conn-pill" class:disconnected={!connected}>
      <span class="conn-dot"></span>
      <span>{connected ? connLabel : 'Brak połączenia'}</span>
    </div>
  </div>
</header>

<!-- Navigation Tabs -->
<nav class="nav-tabs">
  <button
    class="nav-btn"
    class:active={activeTab === 'dashboard'}
    onclick={() => (activeTab = 'dashboard')}
  >
    📊 Pulpit
  </button>
  <button
    class="nav-btn"
    class:active={activeTab === 'combustion'}
    onclick={() => (activeTab = 'combustion')}
  >
    🔥 Spalanie (34)
  </button>
  <button
    class="nav-btn"
    class:active={activeTab === 'advanced'}
    onclick={() => (activeTab = 'advanced')}
  >
    ⚙️ Zaawansowane (23)
  </button>
  <button
    class="nav-btn"
    class:active={activeTab === 'calibration'}
    onclick={() => (activeTab = 'calibration')}
  >
    🎯 Kalibracja & Sieć (10)
  </button>
  <button
    class="nav-btn"
    class:active={activeTab === 'schedules'}
    onclick={() => (activeTab = 'schedules')}
  >
    📅 Harmonogramy (7)
  </button>
</nav>

<!-- Main Content Area -->
<main class="main-content">
  <!-- Active Alarms Banner -->
  {#if activeAlarmsText}
    <div class="alert-banner">
      <div class="alert-info">
        <span style="font-size: 1.4rem;">⚠️</span>
        <div>
          <div class="alert-title">Aktywny Alarm Kotła!</div>
          <div class="alert-text">{activeAlarmsText}</div>
        </div>
      </div>
      <button class="btn-ack" onclick={handleAckAlarm}>Skasuj alarm</button>
    </div>
  {/if}

  {#if activeTab === 'dashboard'}
    <Dashboard
      {status}
      hopperCapacity={150}
      onStepSetpoint={handleStepSetpoint}
      onRefillHopper={handleRefillHopper}
      onSetFeederMode={handleSetFeederMode}
    />
  {:else if activeTab === 'combustion'}
    <ParamsTab
      title="Parametry Procesu Spalania i Podajnika"
      groupFilter={['gr_spalanie']}
      {client}
      bind:paramsCache
      {showToast}
    />
  {:else if activeTab === 'advanced'}
    <ParamsTab
      title="Ustawienia Zaawansowane Kotła & Obiegów"
      groupFilter={['gr_zaaw', 'extended']}
      {client}
      bind:paramsCache
      {showToast}
    />
  {:else if activeTab === 'calibration'}
    <ParamsTab
      title="Kalibracja Czujników & Krzywa Grzania"
      groupFilter={['gr_kalib', 'gr_krzywa', 'gr_user', 'gr_eth']}
      {client}
      bind:paramsCache
      {showToast}
    />
  {:else if activeTab === 'schedules'}
    <SchedulesTab
      {client}
      {showToast}
    />
  {/if}
</main>

<!-- Footer -->
<footer class="app-footer">
  <div class="footer-left">
    <span>Protokół: <strong>eCoal v0.2.9.16a</strong></span>
    <span>Pokrycie parametrów: <strong>122 / 122 (100%)</strong></span>
  </div>
  <div class="footer-right">
    <label for="transportSelect">Adapter:</label>
    <select
      id="transportSelect"
      class="transport-select"
      value={selectedTransport}
      onchange={handleTransportChange}
    >
      <option value="auto">Automatyczny (HA / Direct)</option>
      <option value="mock">Wirtualny Symulator (Mock)</option>
      <option value="serial">Web Serial API (USB-RS232)</option>
    </select>
  </div>
</footer>

<!-- Toast Notifications -->
<div class="toast-container">
  {#each toasts as t (t.id)}
    <div class="toast {t.type}">
      <span>{t.type === 'success' ? '✔' : t.type === 'error' ? '✖' : 'ℹ'}</span>
      <span>{t.message}</span>
    </div>
  {/each}
</div>
