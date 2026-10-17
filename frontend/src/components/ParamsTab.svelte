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
  let isLoadingAll = $state(false);
  let progressText = $state('');

  // Filter parameters by group
  let groupParams = $derived(
    ECOAL_PARAMETERS.filter((p) => groupFilter.includes(p.group))
  );

  // Filter by search query
  let filteredParams = $derived(
    groupParams.filter((p) => {
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase().trim();
      return p.name.toLowerCase().includes(q) || String(p.id).includes(q);
    })
  );

  // Local edits map to track input changes before saving
  let localValues = $state({});

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
          if (raw && raw.length >= 2) {
            let val = raw[0] | (raw[1] << 8);
            if (val > 32767) val -= 65536;
            const displayVal = val / p.div;
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
        if (raw && raw.length >= 2) {
          let val = raw[0] | (raw[1] << 8);
          if (val > 32767) val -= 65536;
          const displayVal = val / p.div;
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
    const val = parseFloat(localValues[p.id]);
    if (isNaN(val)) {
      showToast('Wprowadź prawidłową wartość liczbową', 'error');
      return;
    }
    const valToSend = Math.round(val * p.div);
    try {
      const ok = await client.writeParam(p.id, valToSend);
      if (ok) {
        paramsCache[p.id] = val;
        showToast(`Zapisano ${p.name} (${val} ${p.unit})`, 'success');
      } else {
        showToast(`Błąd zapisu ${p.name}`, 'error');
      }
    } catch (err) {
      showToast(`Wyjątek zapisu ${p.name}: ${err.message}`, 'error');
    }
  }
</script>

<div class="params-container">
  <div class="params-toolbar">
    <input
      type="text"
      class="search-input"
      placeholder="🔍 Szukaj parametru..."
      bind:value={searchQuery}
    />
    <div style="display: flex; align-items: center; gap: 1rem;">
      {#if progressText}
        <span style="font-size: 0.85rem; color: var(--text-muted);">{progressText}</span>
      {/if}
      <button class="btn-primary" onclick={loadAll122Params} disabled={isLoadingAll}>
        {isLoadingAll ? 'Wczytywanie...' : '🔄 Wczytaj wszystkie (122)'}
      </button>
    </div>
  </div>

  {#if title}
    <h2 style="font-size: 1.1rem; margin-bottom: 1rem; color: var(--text-secondary);">{title}</h2>
  {/if}

  <div class="params-grid">
    {#each filteredParams as p (p.id)}
      <div class="param-card">
        <div class="param-header">
          <span class="param-name">{p.name}</span>
          <span class="param-id">#{p.id}</span>
        </div>
        <div class="param-body">
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
          <button class="btn-save-param" onclick={() => saveParam(p)}>Zapisz</button>
        </div>
        <div class="param-limits">
          Zakres: {p.min / p.div} .. {p.max / p.div} {p.unit}
        </div>
      </div>
    {/each}
  </div>
</div>
