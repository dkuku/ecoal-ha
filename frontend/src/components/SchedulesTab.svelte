<script>
  import { onMount } from 'svelte';

  const SCHEDULES = [
    { id: 24, name: 'Harmonogram tygodniowy CO' },
    { id: 25, name: 'Harmonogram tygodniowy CWU' },
    { id: 26, name: 'Harmonogram pogodowy CO' },
    { id: 27, name: 'Harmonogram regulatora pokojowego' },
    { id: 28, name: 'Harmonogram cyrkulacji CWU' },
    { id: 83, name: 'Harmonogram Auto-Lato' },
    { id: 87, name: 'Harmonogram ogrzewania podłogowego' },
  ];

  const DAY_NAMES = [
    'Niedziela',
    'Poniedziałek',
    'Wtorek',
    'Środa',
    'Czwartek',
    'Piątek',
    'Sobota',
  ];

  let {
    client = null,
    showToast = () => {},
  } = $props();

  let selectedScheduleId = $state(24);
  let days = $state(Array(7).fill('1'.repeat(48)));
  let isSaving = $state(false);
  let isLoading = $state(false);
  let isDragging = $state(false);
  let dragTargetBit = $state('1');

  onMount(() => {
    loadSchedule(selectedScheduleId);
  });

  async function loadSchedule(id) {
    if (!client) return;
    isLoading = true;
    try {
      const result = await client.getWeeklyProgram(id);
      if (result && Array.isArray(result) && result.length === 7) {
        days = result;
      } else {
        showToast(`Nie udało się odczytać harmonogramu #${id}`, 'error');
      }
    } catch (err) {
      showToast(`Błąd odczytu: ${err.message}`, 'error');
    } finally {
      isLoading = false;
    }
  }

  function handleScheduleChange(e) {
    const id = parseInt(e.target.value, 10);
    selectedScheduleId = id;
    loadSchedule(id);
  }

  function toggleSlot(dayIdx, slotIdx) {
    const currentDay = days[dayIdx] || '1'.repeat(48);
    const currentBit = currentDay[slotIdx] || '1';
    const newBit = currentBit === '1' ? '0' : '1';
    setSlotBit(dayIdx, slotIdx, newBit);
  }

  function setSlotBit(dayIdx, slotIdx, bit) {
    const currentDay = days[dayIdx] || '1'.repeat(48);
    const chars = currentDay.split('');
    chars[slotIdx] = bit;
    days[dayIdx] = chars.join('');
  }

  function handleSlotMouseDown(dayIdx, slotIdx) {
    isDragging = true;
    const currentBit = (days[dayIdx] || '')[slotIdx] || '1';
    dragTargetBit = currentBit === '1' ? '0' : '1';
    setSlotBit(dayIdx, slotIdx, dragTargetBit);
  }

  function handleSlotMouseEnter(dayIdx, slotIdx) {
    if (isDragging) {
      setSlotBit(dayIdx, slotIdx, dragTargetBit);
    }
  }

  function handleMouseUp() {
    isDragging = false;
  }

  function setAllSlots(bit) {
    days = Array(7).fill(bit.repeat(48));
    showToast(
      bit === '1'
        ? 'Ustawiono wszystkie sloty na temperaturę komfortową'
        : 'Ustawiono wszystkie sloty na temperaturę obniżoną',
      'info'
    );
  }

  function copySundayToAll() {
    const sundayBits = days[0] || '1'.repeat(48);
    days = Array(7).fill(sundayBits);
    showToast('Skopiowano program z Niedzieli na wszystkie dni tygodnia', 'success');
  }

  async function saveSchedule() {
    if (!client || isSaving) return;
    isSaving = true;
    try {
      const ok = await client.setWeeklyProgram(selectedScheduleId, days);
      if (ok) {
        showToast('Pomyślnie zapisano harmonogram w sterowniku kotła!', 'success');
      } else {
        showToast('Sterownik odrzucił zapis harmonogramu', 'error');
      }
    } catch (err) {
      showToast(`Wyjątek zapisu: ${err.message}`, 'error');
    } finally {
      isSaving = false;
    }
  }

  function getSlotTitle(dayIdx, slotIdx, isComfort) {
    const hour = Math.floor(slotIdx / 2).toString().padStart(2, '0');
    const min = slotIdx % 2 === 0 ? '00' : '30';
    const stateName = isComfort ? 'Temperatura standardowa' : 'Obniżona';
    return `${DAY_NAMES[dayIdx]} ${hour}:${min} - ${stateName}`;
  }
</script>

<svelte:window onmouseup={handleMouseUp} />

<div class="schedule-container">
  <div class="schedule-header">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
      <label for="schedSelect" style="font-weight: 600;">Wybierz programator:</label>
      <select
        id="schedSelect"
        class="schedule-select"
        value={selectedScheduleId}
        onchange={handleScheduleChange}
        disabled={isLoading}
      >
        {#each SCHEDULES as s}
          <option value={s.id}>{s.name} (#{s.id})</option>
        {/each}
      </select>
    </div>

    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
      <button class="btn-save-param" onclick={() => setAllSlots('1')}>Wszystko komfort</button>
      <button class="btn-save-param" onclick={() => setAllSlots('0')}>Wszystko obniżona</button>
      <button class="btn-save-param" onclick={copySundayToAll}>Kopiuj Niedzielę</button>
      <button class="btn-primary" onclick={saveSchedule} disabled={isSaving || isLoading}>
        {isSaving ? 'Zapisywanie...' : '💾 Zapisz harmonogram'}
      </button>
    </div>
  </div>

  <div class="schedule-grid">
    <!-- Timeline Hours Header 00 .. 23 -->
    <div class="schedule-timeline-header">
      <span>Dzień</span>
      {#each Array(24) as _, h}
        <span>{h.toString().padStart(2, '0')}</span>
      {/each}
    </div>

    <!-- 7 Days x 48 Slots Body -->
    <div style="display: flex; flex-direction: column; gap: 4px;">
      {#each Array(7) as _, dayIdx}
        <div class="schedule-day-row">
          <div class="schedule-day-label">{DAY_NAMES[dayIdx]}</div>
          {#each Array(48) as __, slotIdx}
            {@const isComfort = (days[dayIdx] || '')[slotIdx] === '1'}
            <div
              class="slot-block"
              class:comfort={isComfort}
              title={getSlotTitle(dayIdx, slotIdx, isComfort)}
              onmousedown={() => handleSlotMouseDown(dayIdx, slotIdx)}
              onmouseenter={() => handleSlotMouseEnter(dayIdx, slotIdx)}
              role="button"
              tabindex="0"
              aria-label={getSlotTitle(dayIdx, slotIdx, isComfort)}
              onkeydown={(e) => {
                if (e.key === ' ' || e.key === 'Enter') {
                  e.preventDefault();
                  toggleSlot(dayIdx, slotIdx);
                }
              }}
            ></div>
          {/each}
        </div>
      {/each}
    </div>
  </div>
</div>
