<script>
  import { onMount } from 'svelte';
  import { ECOAL_PARAMETERS } from '@ecoal/params.js';

  let {
    title = '',
    groupFilter = [],
    client = null,
    paramsCache = $bindable({}),
    showToast = () => {},
  } = $props();

  let searchQuery = $state('');
  let viewMode = $state('table'); // 'table' or 'cards'
  let showAllHints = $state(false); // DEFAULT: false (hidden by default)
  let expandedHints = $state({});
  let isLoadingAll = $state(false);
  let progressText = $state('');

  // Filter parameters by group
  let groupParams = $derived(
    ECOAL_PARAMETERS.filter((p) => groupFilter.includes(p.group))
  );

  // Filter by search query (checks name, ID and hint text)
  let filteredParams = $derived(
    groupParams.filter((p) => {
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase().trim();
      return (
        p.name.toLowerCase().includes(q) ||
        String(p.id).includes(q) ||
        (p.hint && p.hint.toLowerCase().includes(q))
      );
    })
  );

  // Local edits map to track input changes before saving
  let localValues = $state({});

  function decodeParamRaw(p, raw) {
    if (!raw || raw.length === 0) return '';
    if (p.type === 'ip' || p.unit === 'ip') {
      if (raw.length >= 4) {
        return `${raw[0]}.${raw[1]}.${raw[2]}.${raw[3]}`;
      }
    }
    if (p.type === 'mac' || p.unit === 'mac') {
      if (raw.length >= 6) {
        return raw
          .slice(0, 6)
          .map((b) => b.toString(16).padStart(2, '0').toUpperCase())
          .join(':');
      }
    }
    if (p.type === 'text' || p.unit === 'text') {
      let str = '';
      for (let i = 0; i < raw.length && raw[i] !== 0; i++) {
        str += String.fromCharCode(raw[i]);
      }
      return str;
    }
    if (raw.length >= 2) {
      let val = raw[0] | (raw[1] << 8);
      if (val > 32767) val -= 65536;
      return p.div > 1 ? (val / p.div).toFixed(1) : String(val);
    }
    return String(raw[0]);
  }

  // When paramsCache updates or tab opens, ensure localValues has current value
  $effect(() => {
    for (const p of groupParams) {
      if (paramsCache[p.id] !== undefined && localValues[p.id] === undefined) {
        localValues[p.id] = paramsCache[p.id];
      }
    }
  });

  onMount(() => {
    loadGroupParams();
  });

  async function loadGroupParams() {
    if (!client) return;
    for (const p of groupParams) {
      if (paramsCache[p.id] === undefined) {
        try {
          const raw = await client.readParam(p.id);
          if (raw) {
            const displayVal = decodeParamRaw(p, raw);
            paramsCache[p.id] = displayVal;
            localValues[p.id] = displayVal;
          }
        } catch (err) {
          console.warn(`Error reading param #${p.id}:`, err);
        }
      }
    }
  }

  async function loadAll122Params() {
    if (!client || isLoadingAll) return;
    isLoadingAll = true;
    let count = 0;
    const total = ECOAL_PARAMETERS.length;

    for (const p of ECOAL_PARAMETERS) {
      try {
        const raw = await client.readParam(p.id);
        if (raw) {
          const displayVal = decodeParamRaw(p, raw);
          paramsCache[p.id] = displayVal;
          localValues[p.id] = displayVal;
          count++;
        }
      } catch (err) {
        console.warn(`Error reading param #${p.id}:`, err);
      }
      progressText = `Wczytano ${count}/${total}`;
    }

    isLoadingAll = false;
    showToast(`Wczytano ${count} z ${total} parametrów!`, 'success');
  }

  async function saveParam(p) {
    if (!client) return;
    let valToSend;

    if (p.type === 'ip' || p.unit === 'ip') {
      const parts = String(localValues[p.id] || '')
        .trim()
        .split('.')
        .map((x) => parseInt(x, 10));
      if (parts.length !== 4 || parts.some((x) => isNaN(x) || x < 0 || x > 255)) {
        showToast('Wprowadź prawidłowy adres IP (np. 192.168.2.111)', 'error');
        return;
      }
      valToSend = parts;
    } else if (p.type === 'mac' || p.unit === 'mac') {
      const parts = String(localValues[p.id] || '')
        .trim()
        .split(':')
        .map((x) => parseInt(x, 16));
      if (parts.length !== 6 || parts.some((x) => isNaN(x) || x < 0 || x > 255)) {
        showToast('Wprowadź prawidłowy adres MAC (np. 00:08:DC:11:22:33)', 'error');
        return;
      }
      valToSend = parts;
    } else if (p.type === 'text' || p.unit === 'text') {
      const str = String(localValues[p.id] || '');
      valToSend = Array.from(str).map((c) => c.charCodeAt(0));
    } else {
      const val = parseFloat(localValues[p.id]);
      if (isNaN(val)) {
        showToast('Wprowadź prawidłową wartość liczbową', 'error');
        return;
      }
      valToSend = Math.round(val * p.div);
    }

    try {
      const ok = await client.writeParam(p.id, valToSend);
      if (ok) {
        paramsCache[p.id] = localValues[p.id];
        showToast(`Zapisano ${p.name} (${localValues[p.id]} ${p.unit})`, 'success');
      } else {
        showToast(`Błąd zapisu ${p.name}`, 'error');
      }
    } catch (err) {
      showToast(`Wyjątek zapisu ${p.name}: ${err.message}`, 'error');
    }
  }

  function getLimitsLabel(p) {
    if (p.type === 'ip' || p.unit === 'ip') return 'IPv4 (A.B.C.D)';
    if (p.type === 'mac' || p.unit === 'mac') return 'MAC (XX:XX:XX:XX:XX:XX)';
    if (p.type === 'text' || p.unit === 'text') return 'Tekst';
    if (p.min !== null && p.max !== null) {
      return `${p.min / p.div} .. ${p.max / p.div} ${p.unit}`;
    }
    return p.unit || '-';
  }
</script>

<div class="params-container">
  <div class="params-toolbar">
    <input
      type="text"
      class="search-input"
      placeholder="🔍 Szukaj parametru, numeru #ID lub w opisach..."
      bind:value={searchQuery}
    />
    <div style="display: flex; align-items: center; gap: 0.75rem;">
      <div class="view-switch">
        <button
          class="view-btn"
          class:active={viewMode === 'table'}
          onclick={() => (viewMode = 'table')}
          title="Widok tabeli"
        >
          📋 Tabela
        </button>
        <button
          class="view-btn"
          class:active={viewMode === 'cards'}
          onclick={() => (viewMode = 'cards')}
          title="Widok kart"
        >
          🗂️ Karty
        </button>
      </div>
      <button
        class="view-btn"
        class:active={showAllHints}
        onclick={() => (showAllHints = !showAllHints)}
        title="Włącz lub wyłącz pokazywanie wszystkich podpowiedzi"
      >
        💡 {showAllHints ? 'Ukryj podpowiedzi' : 'Pokaż podpowiedzi'}
      </button>
      {#if progressText}
        <span style="font-size: 0.85rem; color: var(--text-muted);">{progressText}</span>
      {/if}
      <button class="btn-primary" onclick={loadAll122Params} disabled={isLoadingAll}>
        {isLoadingAll ? 'Wczytywanie...' : '🔄 Wczytaj wszystkie (122)'}
      </button>
    </div>
  </div>

  {#if title}
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
      <h2 style="font-size: 1.1rem; color: var(--text-secondary); margin: 0;">{title}</h2>
      <span style="font-size: 0.85rem; color: var(--text-muted);">
        Znaleziono: {filteredParams.length} {filteredParams.length === 1 ? 'parametr' : 'parametrów'}
      </span>
    </div>
  {/if}

  {#if viewMode === 'table'}
    <div class="table-responsive">
      <table class="params-table">
        <thead>
          <tr>
            <th style="width: 50px;">#</th>
            <th>Parametr</th>
            <th style="width: 150px;">Zakres</th>
            <th style="width: 200px;">Wartość</th>
            <th style="width: 90px; text-align: center;">Akcja</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredParams as p (p.id)}
            <tr class="param-row">
              <td class="param-id-cell">#{p.id}</td>
              <td class="param-info-cell">
                <div style="display: flex; align-items: center; gap: 0.4rem;">
                  <span class="param-name-title">{p.name}</span>
                  {#if p.hint}
                    <button
                      class="hint-toggle-btn"
                      class:active={showAllHints || expandedHints[p.id]}
                      onclick={() => (expandedHints[p.id] = !expandedHints[p.id])}
                      title="Pokaż/ukryj podpowiedź"
                    >
                      💡
                    </button>
                  {/if}
                </div>
                {#if (showAllHints || expandedHints[p.id]) && p.hint}
                  <div class="param-hint-text">💡 {p.hint}</div>
                {/if}
              </td>
              <td class="param-limits-cell">
                {getLimitsLabel(p)}
              </td>
              <td class="param-value-cell">
                <div class="param-input-group">
                  {#if p.type === 'ip'}
                    <input
                      type="text"
                      class="param-table-input"
                      style="width: 140px; font-family: monospace; text-align: center;"
                      placeholder="192.168.1.1"
                      value={localValues[p.id] !== undefined ? localValues[p.id] : ''}
                      oninput={(e) => (localValues[p.id] = e.target.value)}
                    />
                  {:else if p.type === 'mac'}
                    <input
                      type="text"
                      class="param-table-input"
                      style="width: 160px; font-family: monospace; text-align: center;"
                      placeholder="00:08:DC:01:02:03"
                      value={localValues[p.id] !== undefined ? localValues[p.id] : ''}
                      oninput={(e) => (localValues[p.id] = e.target.value)}
                    />
                  {:else if p.type === 'text'}
                    <input
                      type="text"
                      class="param-table-input"
                      style="width: 140px;"
                      value={localValues[p.id] !== undefined ? localValues[p.id] : ''}
                      oninput={(e) => (localValues[p.id] = e.target.value)}
                    />
                  {:else}
                    <input
                      type="number"
                      class="param-table-input"
                      min={p.min / p.div}
                      max={p.max / p.div}
                      step={p.div === 10 ? '0.1' : '1'}
                      value={localValues[p.id] !== undefined ? localValues[p.id] : ''}
                      oninput={(e) => (localValues[p.id] = e.target.value)}
                    />
                    <span class="param-table-unit">{p.unit}</span>
                  {/if}
                </div>
              </td>
              <td class="param-action-cell" style="text-align: center;">
                <button class="btn-save-table" onclick={() => saveParam(p)}>Zapisz</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else}
    <div class="params-grid">
      {#each filteredParams as p (p.id)}
        <div class="param-card">
          <div class="param-header">
            <span class="param-name">{p.name}</span>
            <div style="display: flex; align-items: center; gap: 0.35rem;">
              {#if p.hint}
                <button
                  class="hint-toggle-btn"
                  class:active={showAllHints || expandedHints[p.id]}
                  onclick={() => (expandedHints[p.id] = !expandedHints[p.id])}
                  title="Pokaż/ukryj podpowiedź"
                >
                  💡
                </button>
              {/if}
              <span class="param-id">#{p.id}</span>
            </div>
          </div>
          {#if (showAllHints || expandedHints[p.id]) && p.hint}
            <div class="param-hint-text" style="margin-top: 0;">💡 {p.hint}</div>
          {/if}
          <div class="param-body">
            {#if p.type === 'ip'}
              <input
                type="text"
                class="param-input"
                style="width: 140px; font-family: monospace; text-align: center;"
                placeholder="192.168.1.1"
                value={localValues[p.id] !== undefined ? localValues[p.id] : ''}
                oninput={(e) => (localValues[p.id] = e.target.value)}
              />
            {:else if p.type === 'mac'}
              <input
                type="text"
                class="param-input"
                style="width: 160px; font-family: monospace; text-align: center;"
                placeholder="00:08:DC:01:02:03"
                value={localValues[p.id] !== undefined ? localValues[p.id] : ''}
                oninput={(e) => (localValues[p.id] = e.target.value)}
              />
            {:else if p.type === 'text'}
              <input
                type="text"
                class="param-input"
                style="width: 140px;"
                value={localValues[p.id] !== undefined ? localValues[p.id] : ''}
                oninput={(e) => (localValues[p.id] = e.target.value)}
              />
            {:else}
              <input
                type="number"
                class="param-input"
                min={p.min / p.div}
                max={p.max / p.div}
                step={p.div === 10 ? '0.1' : '1'}
                value={localValues[p.id] !== undefined ? localValues[p.id] : ''}
                oninput={(e) => (localValues[p.id] = e.target.value)}
              />
              <span class="param-unit">{p.unit}</span>
            {/if}
            <button class="btn-save-param" onclick={() => saveParam(p)}>Zapisz</button>
          </div>
          <div class="param-limits">
            Zakres: {getLimitsLabel(p)}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
