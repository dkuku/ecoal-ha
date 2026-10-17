/**
 * eCoal Modern Single Page Application (app.js)
 *
 * Full-featured controller application:
 * - 1:1 parameter coverage (122 registers)
 * - 7 weekly schedules with 48 half-hour slots
 * - Pluggable transport (HA proxy, Direct LAN, Serial, Mock)
 * - Animated interactive hydraulic diagram (SVG)
 * - Zero external build dependencies (native ES modules)
 */

import { ECOAL_PARAMETERS } from "./params.js";
import {
  calcCrc8,
  SENSOR_NAMES,
  OUTPUT_NAMES,
  FEEDER_MODES,
  buildStatusCmd,
  buildReadParamCmd,
  buildWriteParamCmd,
  buildRefillHopperCmd,
  buildAckAlarmsCmd,
  decodeWeeklyProgram,
  encodeWeeklyProgram,
  buildWriteProgramCmd,
  CRamka,
  decodeStatusFrame,
} from "./protocol.js";
import {
  EcoalClient,
  HttpTransportAdapter,
  MockTransportAdapter,
  SerialTransportAdapter,
} from "./adapter.js";

const ALARM_DESCRIPTIONS = {
  1: "Błąd czujnika temperatury kotła (CO)",
  2: "Przekroczona maksymalna temperatura kotła (>85°C)",
  4: "Przekroczona temperatura podajnika (>65°C)",
  8: "Brak opału w zasobniku / wygaszenie",
  16: "Zacięcie podajnika / zerwana zawleczka ślimaka",
  32: "Błąd czujnika temperatury podajnika",
  64: "Błąd czujnika temperatury CWU",
  128: "Błąd czujnika temperatury spalin",
  256: "Błąd czujnika temperatury powrotu",
  512: "Zewnętrzny styk alarmowy rozwarty",
};

const SCHEDULE_NAMES = {
  24: "Harmonogram tygodniowy CO",
  25: "Harmonogram tygodniowy CWU",
  26: "Harmonogram pogodowy CO",
  27: "Harmonogram regulatora pokojowego",
  28: "Harmonogram cyrkulacji CWU",
  83: "Harmonogram Auto-Lato",
  87: "Harmonogram ogrzewania podłogowego",
};

const DAY_NAMES = [
  "Niedziela",
  "Poniedziałek",
  "Wtorek",
  "Środa",
  "Czwartek",
  "Piątek",
  "Sobota",
];

class EcoalApp {
  constructor() {
    this.client = new EcoalClient();
    this.currentStatus = null;
    this.paramsCache = new Map();
    this.activeTab = "dashboard";
    this.activeScheduleId = 24;
    this.currentScheduleDays = Array(7).fill("1".repeat(48));
    this.isPolling = false;
    this.pollInterval = 3000;
    this.pollTimer = null;
    this.hopperCapacity = 150; // kg
    this.logEntries = [];
  }

  async init() {
    this.setupTransport();
    this.bindEvents();
    this.switchTab("dashboard");
    this.startPolling();
  }

  setupTransport() {
    const urlParams = new URLSearchParams(window.location.search);
    const transportType = urlParams.get("transport") || localStorage.getItem("ecoal_transport") || "auto";
    const customHost = urlParams.get("host") || localStorage.getItem("ecoal_host") || "";

    const transportSelect = document.getElementById("transportSelect");
    if (transportSelect) transportSelect.value = transportType;

    if (transportType === "mock" || urlParams.get("mock") === "1") {
      this.client.setAdapter(new MockTransportAdapter());
      this.updateConnPill(true, "Symulator Mock");
    } else if (transportType === "serial") {
      this.client.setAdapter(new SerialTransportAdapter());
      this.updateConnPill(true, "Web Serial API");
    } else if (transportType === "direct" && customHost) {
      this.client.setAdapter(new HttpTransportAdapter(customHost.startsWith("http") ? customHost : `http://${customHost}`));
      this.updateConnPill(true, `Bezpośredni: ${customHost}`);
    } else {
      // Auto-detect: if running inside HA panel (/ecoal_ui or HA host)
      if (
        window.location.pathname.includes("/ecoal") ||
        window.location.port === "8123" ||
        window.location.pathname.includes("/api/ecoal")
      ) {
        this.client.setAdapter(new HttpTransportAdapter("/api/ecoal"));
        this.updateConnPill(true, "Home Assistant Proxy");
      } else {
        // Direct furnace root or port 8080 mock
        this.client.setAdapter(new HttpTransportAdapter(""));
        this.updateConnPill(true, "Połączenie HTTP");
      }
    }
  }

  updateConnPill(connected, label) {
    const pill = document.getElementById("connPill");
    const text = document.getElementById("connLabel");
    if (!pill || !text) return;
    if (connected) {
      pill.className = "conn-pill";
      text.textContent = label || "Połączono";
    } else {
      pill.className = "conn-pill disconnected";
      text.textContent = label || "Brak połączenia";
    }
  }

  bindEvents() {
    // Navigation Tabs
    document.querySelectorAll(".nav-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        if (tab) this.switchTab(tab);
      });
    });

    // Transport selector in footer
    const transportSelect = document.getElementById("transportSelect");
    if (transportSelect) {
      transportSelect.addEventListener("change", (e) => {
        localStorage.setItem("ecoal_transport", e.target.value);
        this.setupTransport();
        this.fetchStatus();
      });
    }

    // Setpoint +/- buttons
    document.getElementById("btnCoMinus")?.addEventListener("click", () => this.stepSetpoint("co", -1));
    document.getElementById("btnCoPlus")?.addEventListener("click", () => this.stepSetpoint("co", 1));
    document.getElementById("btnCwuMinus")?.addEventListener("click", () => this.stepSetpoint("cwu", -1));
    document.getElementById("btnCwuPlus")?.addEventListener("click", () => this.stepSetpoint("cwu", 1));

    // Refill Hopper button
    document.getElementById("btnRefillHopper")?.addEventListener("click", () => this.handleRefillHopper());

    // Alarm acknowledge button
    document.getElementById("btnAckAlarm")?.addEventListener("click", () => this.handleAckAlarms());

    // Feeder mode select
    document.getElementById("feederModeSelect")?.addEventListener("change", (e) => {
      const mode = parseInt(e.target.value, 10);
      this.client.setFeederMode(mode).then((ok) => {
        if (ok) this.showToast("Zmieniono tryb pracy podajnika", "success");
        else this.showToast("Błąd zapisu trybu podajnika", "error");
      });
    });

    // Load all parameters button
    document.getElementById("btnLoadAllParams")?.addEventListener("click", () => this.loadAllParameters());

    // Parameter search filter
    document.getElementById("paramSearch")?.addEventListener("input", (e) => {
      this.filterParameters(e.target.value.toLowerCase());
    });

    // Schedule selector
    document.getElementById("scheduleSelect")?.addEventListener("change", (e) => {
      this.activeScheduleId = parseInt(e.target.value, 10);
      this.loadSchedule(this.activeScheduleId);
    });

    // Schedule action buttons
    document.getElementById("btnSaveSchedule")?.addEventListener("click", () => this.saveCurrentSchedule());
    document.getElementById("btnSchedAllComfort")?.addEventListener("click", () => this.setAllScheduleSlots("1"));
    document.getElementById("btnSchedAllLowered")?.addEventListener("click", () => this.setAllScheduleSlots("0"));
    document.getElementById("btnSchedCopySunday")?.addEventListener("click", () => this.copyDayToAll(0));
  }

  switchTab(tabId) {
    this.activeTab = tabId;
    document.querySelectorAll(".nav-btn").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-tab") === tabId);
    });
    document.querySelectorAll(".tab-panel").forEach((p) => {
      p.classList.toggle("active", p.id === `tab-${tabId}`);
    });

    if (tabId === "combustion" || tabId === "advanced" || tabId === "calibration") {
      this.renderParametersTab(tabId);
      this.loadTabParameters(tabId);
    } else if (tabId === "schedules") {
      this.renderScheduleMatrix();
      this.loadSchedule(this.activeScheduleId);
    }
  }

  async loadTabParameters(groupCategory) {
    let groupFilter = [];
    if (groupCategory === "combustion") groupFilter = ["gr_spalanie"];
    else if (groupCategory === "advanced") groupFilter = ["gr_zaaw", "extended"];
    else if (groupCategory === "calibration") groupFilter = ["gr_kalib", "gr_krzywa", "gr_user", "gr_eth"];

    const params = ECOAL_PARAMETERS.filter((p) => groupFilter.includes(p.group));
    for (const p of params) {
      if (this.paramsCache.has(p.id)) continue;
      try {
        const raw = await this.client.readParam(p.id);
        if (raw && raw.length >= 2) {
          let val = raw[0] | (raw[1] << 8);
          if (val > 32767) val -= 65536;
          const displayVal = val / p.div;
          this.paramsCache.set(p.id, { val: displayVal });
          const input = document.getElementById(`inputParam-${p.id}`);
          if (input && input.value === "") {
            input.value = displayVal;
          }
        }
      } catch (err) {
        console.warn(`Error reading param ${p.id}:`, err);
      }
    }
  }

  startPolling() {
    if (this.isPolling) return;
    this.isPolling = true;
    this.fetchStatus();
    this.pollTimer = setInterval(() => this.fetchStatus(), this.pollInterval);
  }

  stopPolling() {
    this.isPolling = false;
    if (this.pollTimer) clearInterval(this.pollTimer);
  }

  async fetchStatus() {
    try {
      const status = await this.client.getStatus();
      if (status) {
        this.currentStatus = status;
        this.updateConnPill(true, "Połączono");
        this.updateDashboard(status);
      } else {
        this.updateConnPill(false, "Brak odpowiedzi");
      }
    } catch (err) {
      console.warn("fetchStatus error:", err);
      this.updateConnPill(false, "Błąd transmisji");
    }
  }

  updateDashboard(s) {
    // 1. Live temperatures on cards
    this.setText("valBoilerTemp", s.boiler_temp !== undefined ? s.boiler_temp.toFixed(1) : "--");
    this.setText("targetBoilerTemp", s.target_boiler_temp || "--");
    this.setText("valDhwTemp", s.dhw_temp !== undefined ? s.dhw_temp.toFixed(1) : "--");
    this.setText("targetDhwTemp", s.target_dhw_temp || "--");
    this.setText("valReturnTemp", s.return_temp !== undefined ? s.return_temp.toFixed(1) : "--");
    this.setText("valExhaustTemp", s.exhaust_temp !== undefined ? s.exhaust_temp.toFixed(1) : "--");
    this.setText("valOutdoorTemp", s.outdoor_temp !== undefined ? s.outdoor_temp.toFixed(1) : "--");
    this.setText("valIndoorTemp", s.indoor_temp !== undefined ? s.indoor_temp.toFixed(1) : "--");
    this.setText("valFeederTemp", s.feeder_temp !== undefined ? s.feeder_temp.toFixed(1) : "--");

    // 2. SVG Diagram updates
    this.setText("svgBoilerTemp", `${s.boiler_temp !== undefined ? s.boiler_temp.toFixed(1) : "--"}°C`);
    this.setText("svgDhwTemp", `${s.dhw_temp !== undefined ? s.dhw_temp.toFixed(1) : "--"}°C`);
    this.setText("svgReturnTemp", `${s.return_temp !== undefined ? s.return_temp.toFixed(1) : "--"}°C`);
    this.setText("svgExhaustTemp", `${s.exhaust_temp !== undefined ? s.exhaust_temp.toFixed(1) : "--"}°C`);
    this.setText("svgOutdoorTemp", `${s.outdoor_temp !== undefined ? s.outdoor_temp.toFixed(1) : "--"}°C`);

    // Pumps rotation animations in SVG
    this.toggleClass("svgPumpCo", "pump-active", s.ch_pump);
    this.toggleClass("svgPumpCwu", "pump-active", s.dhw_pump);
    this.toggleClass("svgPumpMixer", "pump-active", s.mixer_pump);

    // Pipe flow animations
    this.toggleClass("svgPipeHot", "pipe-flow", s.ch_pump || s.heating > 0);
    this.toggleClass("svgPipeReturn", "pipe-flow-reverse", s.ch_pump || s.mixer_pump);
    this.toggleClass("svgPipeCwu", "pipe-flow", s.dhw_pump);

    // Flame animation
    const isFlameActive = s.heating > 0 || s.air_pump;
    this.toggleClass("svgFlame", "flame-inactive", !isFlameActive);

    // 3. Actuators pills
    this.toggleClass("tagBlower", "on", s.air_pump);
    this.toggleClass("tagFeeder", "on", s.coal_feeder);
    this.toggleClass("tagPumpCo", "on", s.ch_pump);
    this.toggleClass("tagPumpCwu", "on", s.dhw_pump);
    this.toggleClass("tagPumpMixer", "on", s.mixer_pump);

    this.setText("valBlowerPower", `${s.air_pump_power || 0}%`);

    // 4. Fuel Hopper
    const fuelPct = s.fuel_load_pct !== undefined ? s.fuel_load_pct : 0;
    this.setText("fuelPctText", `${fuelPct}%`);
    const fuelKg = (s.fuel_remaining_kg !== undefined && s.fuel_remaining_kg !== null)
      ? s.fuel_remaining_kg
      : Math.round((this.hopperCapacity * fuelPct) / 100);
    this.setText("fuelKgText", `ok. ${fuelKg} kg`);
    const fillBar = document.getElementById("fuelBarFill");
    if (fillBar) {
      fillBar.style.width = `${fuelPct}%`;
      fillBar.classList.toggle("low", fuelPct <= 15);
    }
    const mins = s.feeder_runtime_min !== undefined ? s.feeder_runtime_min : (s.feeder_runtime !== undefined ? s.feeder_runtime : 0);
    const hours = Math.floor(mins / 60);
    const remMins = Math.round(mins % 60);
    this.setText("feederRuntimeText", `${hours}h ${remMins}m`);

    // Feeder combustion mode select sync
    if (s.feeder_mode !== undefined && s.feeder_mode !== null) {
      const modeSelect = document.getElementById("feederModeSelect");
      if (modeSelect && modeSelect.value !== String(s.feeder_mode)) {
        modeSelect.value = String(s.feeder_mode);
      }
    }

    // 5. Heating State / Feeder Mode
    const statePill = document.getElementById("heatingStatePill");
    if (statePill) {
      if (s.heating === 1) {
        statePill.textContent = "Grzanie";
        statePill.className = "card-status-pill active";
      } else if (s.heating === 2) {
        statePill.textContent = "Podtrzymanie";
        statePill.className = "card-status-pill";
      } else {
        statePill.textContent = s.auto_mode ? "Auto" : "Ręczny";
        statePill.className = "card-status-pill";
      }
    }

    // 6. Alarms Banner
    const alarmBanner = document.getElementById("alarmBanner");
    const alarmText = document.getElementById("alarmText");
    if (alarmBanner && alarmText) {
      if (s.alarm_active && s.alarms_raw) {
        alarmBanner.style.display = "flex";
        const messages = [];
        for (const [mask, desc] of Object.entries(ALARM_DESCRIPTIONS)) {
          if ((s.alarms_raw & parseInt(mask, 10)) !== 0) {
            messages.push(desc);
          }
        }
        alarmText.textContent = messages.length > 0 ? messages.join(" | ") : `Kod alarmu: 0x${s.alarms_raw.toString(16)}`;
      } else {
        alarmBanner.style.display = "none";
      }
    }
  }

  async stepSetpoint(type, delta) {
    if (!this.currentStatus) return;
    if (type === "co") {
      const current = this.currentStatus.target_boiler_temp || 55;
      const next = Math.max(45, Math.min(80, current + delta));
      this.currentStatus.target_boiler_temp = next;
      this.setText("targetBoilerTemp", next);
      const ok = await this.client.setTargetBoilerTemp(next);
      if (ok) this.showToast(`Zadana CO: ${next}°C`, "success");
      else this.showToast("Błąd zmiany temperatury CO", "error");
    } else if (type === "cwu") {
      const current = this.currentStatus.target_dhw_temp || 50;
      const next = Math.max(35, Math.min(65, current + delta));
      this.currentStatus.target_dhw_temp = next;
      this.setText("targetDhwTemp", next);
      const ok = await this.client.setTargetDhwTemp(next);
      if (ok) this.showToast(`Zadana CWU: ${next}°C`, "success");
      else this.showToast("Błąd zmiany temperatury CWU", "error");
    }
  }

  async handleRefillHopper() {
    if (!confirm("Czy na pewno chcesz zresetować licznik i ustawić zasyp na 100%?")) return;
    const ok = await this.client.refillHopper(this.hopperCapacity);
    if (ok) {
      this.showToast("Zasyp zresetowany do 100%", "success");
      await this.fetchStatus();
    } else {
      this.showToast("Błąd resetowania zasypu", "error");
    }
  }

  async handleAckAlarms() {
    const ok = await this.client.ackAlarms();
    if (ok) {
      this.showToast("Skasowano aktywne alarmy", "success");
      await this.fetchStatus();
    } else {
      this.showToast("Błąd kasowania alarmów", "error");
    }
  }

  // --- Parameters Management ---

  renderParametersTab(groupCategory) {
    const container = document.getElementById(`paramsGrid-${groupCategory}`);
    if (!container) return;

    let groupFilter = [];
    if (groupCategory === "combustion") groupFilter = ["gr_spalanie"];
    else if (groupCategory === "advanced") groupFilter = ["gr_zaaw", "extended"];
    else if (groupCategory === "calibration") groupFilter = ["gr_kalib", "gr_krzywa", "gr_user", "gr_eth"];

    const params = ECOAL_PARAMETERS.filter((p) => groupFilter.includes(p.group));
    container.innerHTML = "";

    for (const p of params) {
      const card = document.createElement("div");
      card.className = "param-card";
      card.setAttribute("data-param-id", p.id);
      card.setAttribute("data-param-name", p.name.toLowerCase());

      const cached = this.paramsCache.get(p.id);
      const currentVal = cached !== undefined ? cached.val : "";

      card.innerHTML = `
        <div class="param-header">
          <span class="param-name">${p.name}</span>
          <span class="param-id">#${p.id}</span>
        </div>
        <div class="param-body">
          <input type="number" class="param-input" id="inputParam-${p.id}"
            value="${currentVal}" min="${p.min}" max="${p.max}" step="${p.div === 10 ? '0.1' : '1'}">
          <span class="param-unit">${p.unit}</span>
          <button class="btn-save-param" data-id="${p.id}">Zapisz</button>
        </div>
        <div class="param-limits">Zakres: ${p.min / p.div} .. ${p.max / p.div} ${p.unit}</div>
      `;

      card.querySelector(".btn-save-param")?.addEventListener("click", () => {
        this.saveSingleParam(p);
      });

      container.appendChild(card);
    }
  }

  async saveSingleParam(p) {
    const input = document.getElementById(`inputParam-${p.id}`);
    if (!input) return;
    const rawVal = parseFloat(input.value);
    if (isNaN(rawVal)) {
      this.showToast("Nieprawidłowa wartość", "error");
      return;
    }
    const valToSend = Math.round(rawVal * p.div);
    const ok = await this.client.writeParam(p.id, valToSend);
    if (ok) {
      this.paramsCache.set(p.id, { val: rawVal });
      this.showToast(`Zapisano ${p.name}`, "success");
    } else {
      this.showToast(`Błąd zapisu ${p.name}`, "error");
    }
  }

  async loadAllParameters() {
    const btn = document.getElementById("btnLoadAllParams");
    const progressText = document.getElementById("paramsProgress");
    if (btn) btn.disabled = true;

    let loadedCount = 0;
    const total = ECOAL_PARAMETERS.length;

    for (const p of ECOAL_PARAMETERS) {
      try {
        const raw = await this.client.readParam(p.id);
        if (raw && raw.length >= 2) {
          let val = raw[0] | (raw[1] << 8);
          if (val > 32767) val -= 65536;
          const displayVal = val / p.div;
          this.paramsCache.set(p.id, { val: displayVal });
          const input = document.getElementById(`inputParam-${p.id}`);
          if (input) input.value = displayVal;
          loadedCount++;
        }
      } catch (err) {
        console.warn(`Failed reading param ${p.id}:`, err);
      }
      if (progressText) {
        progressText.textContent = `Wczytano ${loadedCount}/${total}`;
      }
    }

    if (btn) btn.disabled = false;
    this.showToast(`Wczytano ${loadedCount} z ${total} parametrów!`, "success");
  }

  filterParameters(query) {
    document.querySelectorAll(".param-card").forEach((card) => {
      const name = card.getAttribute("data-param-name") || "";
      const id = card.getAttribute("data-param-id") || "";
      const matches = name.includes(query) || id.includes(query);
      card.style.display = matches ? "flex" : "none";
    });
  }

  // --- Weekly Schedules ---

  async loadSchedule(paramId) {
    const sched = await this.client.getWeeklyProgram(paramId);
    if (sched) {
      this.currentScheduleDays = sched;
      this.renderScheduleMatrix();
    } else {
      this.showToast("Błąd odczytu harmonogramu", "error");
    }
  }

  renderScheduleMatrix() {
    const container = document.getElementById("scheduleGridBody");
    if (!container) return;
    container.innerHTML = "";

    for (let day = 0; day < 7; day++) {
      const row = document.createElement("div");
      row.className = "schedule-day-row";

      const label = document.createElement("div");
      label.className = "schedule-day-label";
      label.textContent = DAY_NAMES[day];
      row.appendChild(label);

      const dayBits = this.currentScheduleDays[day] || "1".repeat(48);

      for (let slot = 0; slot < 48; slot++) {
        const block = document.createElement("div");
        const isComfort = dayBits[slot] === "1";
        block.className = `slot-block ${isComfort ? 'comfort' : ''}`;
        const hour = Math.floor(slot / 2).toString().padStart(2, "0");
        const min = (slot % 2 === 0 ? "00" : "30");
        block.title = `${DAY_NAMES[day]} ${hour}:${min} - ${isComfort ? 'Temperatura standardowa' : 'Obniżona'}`;

        block.addEventListener("click", () => {
          const currentBit = this.currentScheduleDays[day][slot];
          const newBit = currentBit === "1" ? "0" : "1";
          const dayArr = this.currentScheduleDays[day].split("");
          dayArr[slot] = newBit;
          this.currentScheduleDays[day] = dayArr.join("");
          block.className = `slot-block ${newBit === "1" ? 'comfort' : ''}`;
        });

        row.appendChild(block);
      }

      container.appendChild(row);
    }
  }

  setAllScheduleSlots(bitVal) {
    for (let day = 0; day < 7; day++) {
      this.currentScheduleDays[day] = bitVal.repeat(48);
    }
    this.renderScheduleMatrix();
  }

  copyDayToAll(sourceDayIndex) {
    const sourceBits = this.currentScheduleDays[sourceDayIndex];
    for (let day = 0; day < 7; day++) {
      this.currentScheduleDays[day] = sourceBits;
    }
    this.renderScheduleMatrix();
    this.showToast(`Skopiowano ${DAY_NAMES[sourceDayIndex]} na wszystkie dni`, "success");
  }

  async saveCurrentSchedule() {
    const ok = await this.client.setWeeklyProgram(this.activeScheduleId, this.currentScheduleDays);
    if (ok) {
      this.showToast("Zapisano harmonogram w sterowniku!", "success");
    } else {
      this.showToast("Błąd zapisu harmonogramu", "error");
    }
  }

  // --- Utilities ---

  setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  toggleClass(id, className, condition) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle(className, !!condition);
  }

  showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${type === 'success' ? '✔' : type === 'error' ? '✖' : 'ℹ'}</span> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }
}

// Instantiate and initialize immediately or on DOM ready
function startApp() {
  const app = new EcoalApp();
  window.ecoalApp = app;
  app.init();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", startApp);
} else {
  startApp();
}
