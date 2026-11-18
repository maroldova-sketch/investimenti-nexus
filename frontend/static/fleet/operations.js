/* Fleet operations: manual input into the same audited command API used by Elias. */
(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  const API = '/api/fleet/elias';
  const state = { meta: null, vehicle: null, pending: null, busy: false, listSequence: 0, detailSequence: 0 };
  const kmFormat = new Intl.NumberFormat('cs-CZ');

  class ApiError extends Error {
    constructor(message, status = 0) { super(message); this.status = status; }
  }

  function announce(message, kind = '') {
    byId('fleet-status').textContent = message;
    byId('fleet-status').dataset.kind = kind;
  }

  function validationMessage(body, status, fallback) {
    if (![400, 409, 422].includes(status)) return fallback;
    // API-authored domain errors are user-facing text, never HTML. Do not expose
    // Pydantic's input/ctx fields, which can contain submitted private content.
    if (typeof body?.detail === 'string' && body.detail.length <= 400) {
      return body.detail.replace(/[\u0000-\u001f\u007f]/g, ' ');
    }
    if (status === 422 && Array.isArray(body?.detail)) {
      const fields = new Set(body.detail.flatMap(item => Array.isArray(item.loc) ? item.loc : []));
      const hints = [];
      if (fields.has('km')) hints.push('Kilometry musí být celé číslo od 0 do 9 999 999.');
      if (fields.has('description')) hints.push('Popis závady musí obsahovat 1 až 2 000 znaků.');
      if (fields.has('effective_at')) hints.push('Zkontroluj skutečné datum a čas události.');
      if (fields.has('expected_revision')) hints.push('Obnov údaje auta před novým zadáním.');
      if (hints.length) return hints.join(' ');
    }
    return fallback;
  }

  async function api(path, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(API + path, {
        ...options, credentials: 'same-origin', redirect: 'error',
        cache: 'no-store', signal: controller.signal,
        headers: { Accept: 'application/json', ...options.headers },
      });
      let body;
      try { body = await response.json(); }
      catch (_) { throw new ApiError('Server neposlal ověřitelnou odpověď. Zkontroluj přihlášení a zkus ověření znovu.', response.status); }
      if (!response.ok) {
        const messages = {
          401: 'Přihlášení vypršelo. Přihlas se v jiné kartě a zde opakuj ověření.',
          403: 'Pro tento úkon nemáš oprávnění, nebo vypršelo ověření požadavku.',
          404: 'Požadovaný záznam není dostupný.',
          409: 'Údaje se mezitím změnily nebo je zadání v konfliktu. Nejdřív ověř výsledek a načti aktuální údaje.',
          422: 'Server zadání odmítl. Zkontroluj kilometry, čas a povinné údaje.',
          429: 'Požadavků je příliš mnoho. Za chvíli opakuj stejné zadání.',
        };
        const fallback = messages[response.status] || 'Požadavek se nepodařilo potvrdit. Opakuj ověření stejného zadání.';
        throw new ApiError(validationMessage(body, response.status, fallback), response.status);
      }
      return body;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(error.name === 'AbortError'
        ? 'Vypršel čas čekání. Záznam mohl být uložen; výsledek zatím není ověřen.'
        : 'Spojení se nepodařilo dokončit. Záznam mohl být uložen; výsledek zatím není ověřen.');
    } finally { clearTimeout(timer); }
  }

  function lockControls() {
    const locked = Boolean(state.pending) || state.busy;
    byId('odometer-fields').disabled = locked || !state.vehicle || !state.meta;
    byId('defect-fields').disabled = locked || !state.vehicle || !state.meta;
    byId('refresh-vehicle').disabled = locked;
    byId('vehicle-query').disabled = locked;
    byId('vehicle-search-button').disabled = locked;
    byId('vehicle-list').querySelectorAll('button').forEach(button => { button.disabled = locked; });
    byId('retry-command').disabled = state.busy;
    byId('new-command').disabled = state.busy;
  }

  function localNow() {
    const date = new Date();
    const pad = value => String(value).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }

  function setDefaultDates() {
    byId('odometer-at').value = localNow();
    byId('defect-at').value = localNow();
  }

  function appendText(parent, tag, value, className) {
    const element = document.createElement(tag);
    element.textContent = value;
    if (className) element.className = className;
    parent.appendChild(element);
    return element;
  }

  function dateLabel(raw) {
    if (!raw) return 'Datum není uvedené';
    // Preserve date-only source values rather than shifting them between time zones.
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw.split('-').reverse().join('. ');
    const date = new Date(raw);
    return Number.isNaN(date.getTime()) ? String(raw) : date.toLocaleString('cs-CZ');
  }

  function renderHistory(id, rows, render, empty) {
    const list = byId(id);
    list.replaceChildren();
    if (!Array.isArray(rows) || rows.length === 0) {
      appendText(list, 'li', empty, 'text-muted');
      return;
    }
    rows.forEach(row => { const item = document.createElement('li'); render(item, row); list.appendChild(item); });
  }

  function renderVehicle(vehicle) {
    if (!vehicle || typeof vehicle.id !== 'string' || vehicle.revision == null) {
      throw new ApiError('Údaje auta nejsou úplné. Zápis je do obnovení nedostupný.');
    }
    state.vehicle = vehicle;
    byId('vehicle-placeholder').hidden = true;
    byId('vehicle-panel').hidden = false;
    byId('selected-vehicle-spz').textContent = vehicle.spz || 'SPZ není doplněná';
    byId('selected-vehicle-title').textContent = [vehicle.make, vehicle.model].filter(Boolean).join(' ') || 'Vozidlo';
    byId('vehicle-state').textContent = vehicle.status || 'Neznámý';
    byId('vehicle-driver').textContent = typeof vehicle.current_driver === 'string' && vehicle.current_driver ? vehicle.current_driver : 'Není doložený';
    byId('vehicle-odometer').textContent = typeof vehicle.km_current === 'number' && Number.isFinite(vehicle.km_current)
      ? `${kmFormat.format(vehicle.km_current)} km` : 'Není doložený';
    byId('assignment-warning').hidden = !vehicle.assignment_warning;
    byId('assignment-warning').textContent = typeof vehicle.assignment_warning === 'string'
      ? vehicle.assignment_warning : 'Přiřazení řidiče vyžaduje kontrolu.';
    renderHistory('odometer-history', vehicle.odometer_readings, (item, row) => {
      appendText(item, 'strong', typeof row.km === 'number' ? `${kmFormat.format(row.km)} km` : 'Stav není doložený');
      appendText(item, 'small', dateLabel(row.reading_date));
    }, 'Žádný odečet není dostupný.');
    renderHistory('event-history', vehicle.events, (item, row) => {
      appendText(item, 'strong', row.event_type || 'Událost');
      appendText(item, 'small', dateLabel(row.event_date));
      appendText(item, 'p', row.description || 'Bez popisu');
    }, 'Žádné události nejsou dostupné.');
    byId('vehicle-list').querySelectorAll('button').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.vehicleId === vehicle.id));
    });
    lockControls();
  }

  async function loadVehicle(id, focus = false) {
    const sequence = ++state.detailSequence;
    state.vehicle = null;
    lockControls();
    announce('Načítám aktuální údaje auta…');
    try {
      const vehicle = await api(`/vehicles/${encodeURIComponent(id)}`);
      if (sequence !== state.detailSequence) return;
      renderVehicle(vehicle);
      announce('Údaje načtené.');
      if (focus) byId('selected-vehicle-title').focus();
    } catch (error) {
      if (sequence === state.detailSequence) { announce(error.message, 'error'); lockControls(); }
    }
  }

  async function searchVehicles() {
    if (state.pending || state.busy) return;
    const sequence = ++state.listSequence;
    const q = byId('vehicle-query').value.trim();
    announce('Vyhledávám vozidla…');
    try {
      const result = await api(`/vehicles?q=${encodeURIComponent(q)}`);
      if (sequence !== state.listSequence) return;
      if (!Array.isArray(result.items)) throw new ApiError('Seznam vozidel se nepodařilo načíst.');
      const list = byId('vehicle-list');
      list.replaceChildren();
      byId('vehicle-count').textContent = result.items.length ? `Zobrazeno vozidel: ${result.items.length}` : 'Žádné odpovídající vozidlo.';
      result.items.forEach(vehicle => {
        const item = document.createElement('li');
        const button = document.createElement('button');
        button.type = 'button'; button.className = 'fleet-vehicle-button';
        button.dataset.vehicleId = vehicle.id;
        button.setAttribute('aria-pressed', String(state.vehicle?.id === vehicle.id));
        appendText(button, 'strong', vehicle.spz || 'SPZ není doplněná');
        appendText(button, 'span', [vehicle.make, vehicle.model].filter(Boolean).join(' ') || 'Vozidlo');
        appendText(button, 'span', vehicle.status || 'Stav neznámý');
        button.addEventListener('click', () => { if (!state.pending && !state.busy) loadVehicle(vehicle.id, true); });
        item.appendChild(button); list.appendChild(item);
      });
      announce(result.items.length ? 'Vyber vozidlo ze seznamu.' : 'Nebylo nalezeno žádné vozidlo. Zkus jinou SPZ nebo model.');
      lockControls();
    } catch (error) { if (sequence === state.listSequence) announce(error.message, 'error'); }
  }

  function commandMessage(message, kind = 'info') {
    byId('command-progress').hidden = false;
    byId('command-progress').className = `alert alert-${kind} mt-3 mb-0`;
    byId('command-message').textContent = message;
    const pending = state.pending;
    byId('command-reference').textContent = pending ? `Zadání: ${pending.payload.idempotency_key}` : '';
  }

  function receiptMatches(receipt, pending) {
    return receipt && receipt.status === 'recorded' && typeof receipt.id === 'string'
      && typeof receipt.record_id === 'string' && receipt.revision != null
      && receipt.vehicle_id === pending.payload.vehicle_id && receipt.kind === pending.payload.kind;
  }

  async function executePending() {
    if (!state.pending || state.busy) return;
    const pending = state.pending;
    state.busy = true;
    byId('retry-command').hidden = true;
    byId('new-command').hidden = true;
    lockControls();
    commandMessage(pending.receipt ? 'Ověřuji uložený záznam…' : 'Odesílám zadání a ověřím jeho uložení…');
    try {
      if (!pending.receipt) {
        state.meta = await api('/meta');
        if (typeof state.meta.csrf !== 'string' || !state.meta.csrf) throw new ApiError('Ověření požadavku není dostupné. Zápis nelze potvrdit.');
        pending.sent = true;
        const receipt = await api('/commands', {
          method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Fleet-CSRF': state.meta.csrf },
          body: JSON.stringify(pending.payload),
        });
        if (!receiptMatches(receipt, pending)) throw new ApiError('Server nepotvrdil odpovídající záznam. Opakuj ověření stejného zadání.');
        pending.receipt = receipt;
      }
      const verified = await api(`/commands/${encodeURIComponent(pending.receipt.id)}`);
      if (!receiptMatches(verified, pending) || verified.id !== pending.receipt.id || verified.record_id !== pending.receipt.record_id) {
        throw new ApiError('Zpětné ověření záznamu nesouhlasí. Výsledek není potvrzený; neodesílej nové zadání.');
      }
      const vehicleId = pending.payload.vehicle_id;
      const kind = pending.payload.kind;
      const recordId = verified.record_id;
      state.pending = null;
      state.vehicle = null; // Do not submit a subsequent command with the pre-write revision.
      if (kind === 'odometer') byId('odometer-km').value = '';
      else byId('defect-description').value = '';
      setDefaultDates();
      commandMessage(kind === 'odometer' ? 'Odečet je uložený a zpětně ověřený.' : 'Hlášení závady je uložené a zpětně ověřené.', 'success');
      byId('command-reference').textContent = `Záznam: ${recordId}`;
      // A failed card refresh does not undo the verified command; show both facts.
      try {
        const vehicle = await api(`/vehicles/${encodeURIComponent(vehicleId)}`);
        renderVehicle(vehicle);
        announce('Záznam uložený a ověřený. Karta auta je aktualizovaná.', 'success');
      } catch (_) {
        announce('Záznam je uložený a ověřený. Kartu auta se nepodařilo obnovit; před dalším zápisem načti auto znovu.', 'error');
      }
    } catch (error) {
      // A later permission failure cannot disprove an earlier timed-out write.
      pending.definitelyRejected = !pending.receipt && !pending.hadUncertainResult
        && [400, 401, 403, 404, 422].includes(error.status);
      if (pending.sent && !pending.definitelyRejected) pending.hadUncertainResult = true;
      commandMessage(error.message + (pending.definitelyRejected
        ? ' Zadání lze upravit přes Nové zadání.'
        : ' Původní zadání zůstává zachované pro bezpečné opakování.'), 'warning');
      byId('retry-command').hidden = false;
      byId('new-command').hidden = false;
      announce('Uložení dosud není potvrzené.', 'error');
    } finally { state.busy = false; lockControls(); }
  }

  function createCommand(kind) {
    if (state.pending || state.busy || !state.vehicle || !state.meta) return;
    const form = byId(`${kind === 'odometer' ? 'odometer' : 'defect'}-form`);
    if (!form.reportValidity()) return;
    const rawDate = byId(kind === 'odometer' ? 'odometer-at' : 'defect-at').value;
    const effective = new Date(rawDate);
    if (Number.isNaN(effective.getTime())) { announce('Doplň skutečné datum a čas.', 'error'); return; }
    const pad = value => String(value).padStart(2, '0');
    const roundTrip = `${effective.getFullYear()}-${pad(effective.getMonth() + 1)}-${pad(effective.getDate())}T${pad(effective.getHours())}:${pad(effective.getMinutes())}`;
    if (roundTrip !== rawDate) { announce('Tento místní čas neexistuje, například kvůli změně letního času. Oprav datum a čas.', 'error'); return; }
    if (!globalThis.crypto?.randomUUID) { announce('Zápis není dostupný bez zabezpečeného spojení. Otevři aplikaci přes HTTPS.', 'error'); return; }
    const payload = {
      vehicle_id: state.vehicle.id, expected_revision: String(state.vehicle.revision),
      idempotency_key: crypto.randomUUID(), kind, effective_at: effective.toISOString(), source: 'web',
    };
    if (kind === 'odometer') {
      const km = Number(byId('odometer-km').value);
      if (!Number.isSafeInteger(km) || km < 0 || km > 9999999) { announce('Kilometry musí být celé číslo od 0 do 9 999 999.', 'error'); return; }
      payload.km = km;
    } else {
      payload.description = byId('defect-description').value.trim();
      if (!payload.description) { announce('Popiš závadu.', 'error'); byId('defect-description').focus(); return; }
      if (payload.description.length > 2000) { announce('Popis závady může mít nejvýše 2 000 znaků.', 'error'); byId('defect-description').focus(); return; }
    }
    state.pending = { payload: Object.freeze(payload), receipt: null, definitelyRejected: false, sent: false, hadUncertainResult: false };
    executePending();
  }

  byId('vehicle-search-form').addEventListener('submit', event => { event.preventDefault(); searchVehicles(); });
  byId('odometer-form').addEventListener('submit', event => { event.preventDefault(); createCommand('odometer'); });
  byId('defect-form').addEventListener('submit', event => { event.preventDefault(); createCommand('defect'); });
  byId('refresh-vehicle').addEventListener('click', () => {
    const id = state.vehicle?.id || byId('vehicle-list').querySelector('[aria-pressed="true"]')?.dataset.vehicleId;
    if (id && !state.pending && !state.busy) loadVehicle(id);
  });
  byId('retry-command').addEventListener('click', executePending);
  byId('new-command').addEventListener('click', async () => {
    if (!state.pending || state.busy) return;
    if (!state.pending.definitelyRejected && !confirm('Výsledek původního zadání není ověřený. Mohl už být uložen. Opravdu chceš ukončit jeho ověřování? Před novým zápisem zkontroluj historii auta, aby nevznikla duplicita.')) return;
    const id = state.pending.payload.vehicle_id;
    state.pending = null;
    byId('command-progress').hidden = true;
    await loadVehicle(id);
  });
  window.addEventListener('beforeunload', event => {
    if (state.pending) { event.preventDefault(); event.returnValue = ''; }
  });

  async function init() {
    setDefaultDates();
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'místní čas zařízení';
    byId('fleet-timezone').textContent = `Datum a čas zadávej podle svého zařízení (${zone}). Ukládá se skutečný okamžik události.`;
    try {
      state.meta = await api('/meta');
      if (typeof state.meta.csrf !== 'string' || !state.meta.csrf) throw new ApiError('Ověření zápisu není dostupné. Obnov stránku po přihlášení.');
      await searchVehicles();
    } catch (error) { state.meta = null; announce(error.message, 'error'); }
    lockControls();
  }
  init();
})();
