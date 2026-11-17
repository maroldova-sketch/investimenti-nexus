const root = document.querySelector("#main");
const portal = document.body.dataset.portal === "true";
const apiBase = portal ? "/hr/api" : "/api/hr";
let invitationTicket = portal ? location.hash.slice(1) : "";
if (portal) history.replaceState(null, "", "/hr/entry");
const $ = (s) => document.querySelector(s);
const escape = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const statusLabels = {
  draft: "Rozpracováno",
  submitted: "Čeká na HR",
  returned: "K doplnění",
  reviewed: "Připraveno pro mzdy",
  payroll_received: "Převzato mzdovou rolí",
};
const actionLabels = {
  submit: "Odeslání podkladů",
  return: "Vrácení k doplnění",
  review: "Kontrola HR",
  payroll_receive: "Převzetí mzdovou rolí",
  payroll_return: "Vrácení z mzdové kontroly",
  payroll_import: "Potvrzený import do mzdového programu",
  authority_filing: "Potvrzené úřední podání",
};
let meta,
  current,
  answers = {},
  step = 0,
  dirty = false,
  saveTimer,
  saving = Promise.resolve(),
  generation = 0,
  saveFailed = false,
  busy = false,
  attachmentBusy = false,
  requirementsDirty = false,
  uploadAttempt = null,
  clearHidden = false;
const key = () => crypto.randomUUID();
const editable = () =>
  current?.permissions.edit && ["draft", "returned"].includes(current.status);
function notify(message) {
  const t = $("#toast");
  t.textContent = message;
  t.hidden = false;
  setTimeout(() => (t.hidden = true), 9000);
}
async function api(path, method = "GET", body) {
  const res = await fetch(apiBase + path, {
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(meta ? { "X-HR-CSRF": meta.csrf } : {}),
      ...(portal ? { "X-HR-Portal": "1" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (res.redirected || res.status === 303) {
    const error = Error(
      portal
        ? "Ověření vypršelo. Otevřete původní pozvánku a ověřte se znovu."
        : "Přihlášení vypršelo. Přihlaste se znovu do Nexusu.",
    );
    error.status = 401;
    throw error;
  }
  let value;
  try {
    value = await res.json();
  } catch {
    throw Error(
      "Server nevrátil očekávanou odpověď. Zkuste obnovit přihlášení.",
    );
  }
  if (!res.ok) {
    let detail = value.detail;
    const err = Error(
      typeof detail === "string"
        ? detail
        : detail?.message || "Zkontrolujte zadané údaje.",
    );
    err.fields = detail?.fields;
    err.hidden = detail?.hidden;
    err.matches = detail?.matches;
    err.hiddenMatches = detail?.hidden_matches;
    err.status = res.status;
    throw err;
  }
  return value;
}
function saveStatus(text, error = false) {
  const el = $("#save-status");
  if (el) {
    el.textContent = text;
    el.classList.toggle("error", error);
  }
}

// ---- template: sections and transitive branch activity (mirrors the server)
const sections = () => current?.sections?.length ? current.sections : meta.sections;
const allFields = () => sections().flatMap((s) => s.fields);
function activity() {
  const byKey = Object.fromEntries(allFields().map((f) => [f.key, f]));
  const memo = {};
  const isActive = (k, trail = []) => {
    if (k in memo) return memo[k];
    const f = byKey[k];
    if (!f || trail.includes(k)) return false;
    const result = Object.entries(f.when || {}).every(
      ([ref, values]) => isActive(ref, [...trail, k]) && values.includes(answers[ref]),
    );
    memo[k] = result;
    return result;
  };
  return Object.fromEntries(Object.keys(byKey).map((k) => [k, isActive(k)]));
}
const sectionActive = (s, act) =>
  Object.entries(s.when || {}).every(([ref, values]) => act[ref] && values.includes(answers[ref]));
function formSections() {
  const act = activity();
  return sections().filter((s) => sectionActive(s, act));
}
const reviewed = (k) => (answers._review || []).includes(k);
const isEmpty = (v) => v === undefined || v === null || v === "" || (Array.isArray(v) && !v.length);
function hiddenKeys() {
  const act = activity();
  return allFields()
    .filter((f) => !act[f.key] && !isEmpty(answers[f.key]))
    .map((f) => f.key);
}

function markDirty() {
  dirty = true;
  saveFailed = false;
  generation++;
  saveStatus("Změny čekají na uložení…");
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => flush().catch(() => {}), 900);
}
async function flush() {
  clearTimeout(saveTimer);
  saving = saving
    .catch(() => {})
    .then(async () => {
      if (!dirty || !editable()) return;
      const localGeneration = generation;
      const payload = structuredClone(answers);
      const confirmClear = clearHidden;
      saveStatus("Ukládám…");
      try {
        const saved = await api(`/cases/${current.id}/draft`, "PUT", {
          expected_version: current.version,
          answers: payload,
          confirm_clear: confirmClear,
        });
        current = saved;
        clearHidden = false;
        if (generation === localGeneration) {
          answers = saved.answers;
          dirty = false;
        }
        saveFailed = false;
        // "Uloženo" only after the server confirmed this exact version.
        saveStatus(dirty ? "Čekají další změny…" : "Uloženo na serveru");
      } catch (err) {
        saveFailed = true;
        saveStatus("Neuloženo — " + err.message, true);
        throw err;
      }
    });
  return saving;
}
window.addEventListener("beforeunload", (e) => {
  if (dirty || requirementsDirty || attachmentBusy) {
    e.preventDefault();
    e.returnValue = "";
  }
});
function bind(id, event, callback) {
  const el = document.getElementById(id);
  if (el) el.addEventListener(event, callback);
}
function pill(s) {
  return `<span class="pill ${escape(s)}">${escape(statusLabels[s] || s)}</span>`;
}

// ---- queue ------------------------------------------------------------------
async function loadQueue() {
  if (portal) return openCase(meta.case_id);
  if (requirementsDirty || attachmentBusy)
    throw Error("Nejprve uložte požadavky nebo dokončete nahrávání.");
  if (dirty) await flush();
  if (dirty || saveFailed)
    throw Error("Před opuštěním dokončete uložení změn.");
  current = null;
  const rows = await api("/cases");
  const pending = rows.filter(
    (c) =>
      (["draft", "returned"].includes(c.status) && c.permissions.edit) ||
      (c.status === "submitted" && c.permissions.hr) ||
      (c.status === "reviewed" && c.permissions.payroll_owner),
  ).length;
  root.innerHTML = `<div class="intro"><div><div class="eyebrow">Personální agenda</div><h1>Každý krok má své místo.</h1><p class="muted">Podklady, které čekají na doplnění, kontrolu nebo převzetí. Vždy u konkrétní firmy a pracovního vztahu.</p></div>${meta.can_create ? '<button id="new-case" class="btn primary">＋ Připravit podklady</button>' : ""}</div><div class="stats"><div class="stat"><b>${rows.filter((c) => c.status !== "payroll_received").length}</b><span>Otevřené případy</span></div><div class="stat"><b>${pending}</b><span>Čeká na zásah</span></div><div class="stat"><b>${rows.filter((c) => c.status === "payroll_received").length}</b><span>Převzaté podklady</span></div></div><section class="panel"><div class="row"><h2>Vaše případy</h2><span class="eyebrow">Jen dostupné firmy</span></div>${rows.length ? rows.map((c) => `<article class="case-card"><div><h3>${escape(c.context.name)}</h3><p>${escape(c.context.employer)} · ${escape(c.context.position)}<br>${escape(c.context.employment_type)} · ${c.kind === "change" ? "Změna údajů" : "Doplnění existující evidence"}${c.owners?.hr ? " · HR: " + escape(c.owners.hr) : ""}</p>${pill(c.status)}</div><button class="btn open-case" data-id="${escape(c.id)}">Otevřít →</button></article>`).join("") : '<div class="empty">Zatím tu není žádný případ.<br>HR vybere firmu, člověka a jeho pracovní vztah a připraví podklady.</div>'}</section><div class="notice">${escape(meta.notice)} Převzetí podkladů samo nepotvrzuje způsobilost k práci ani zpracování mzdy.</div>`;
  bind("new-case", "click", () => wizard().catch((e) => notify(e.message)));
  document
    .querySelectorAll(".open-case")
    .forEach(
      (b) =>
        (b.onclick = () =>
          openCase(b.dataset.id).catch((e) => notify(e.message))),
    );
  history.replaceState(null, "", "/people/hr");
}

// ---- internal HR wizard: company → person → relationship → purpose/owners ---
const wz = {};
const wizardSteps = ["Firma", "Osoba", "Pracovní vztah", "Účel a odpovědnost"];
function wizardFrame(n, body) {
  root.innerHTML = `<button id="back" class="btn text">← Vaše případy</button><div class="intro"><div><div class="eyebrow">Příprava HR · krok ${n + 1} z ${wizardSteps.length}</div><h1>${escape(wizardSteps[n])}</h1><p class="muted">Po vytvoření případu následují požadavky HR, ověřený kontakt a pozvánka.</p></div></div><ol class="wizard-steps">${wizardSteps.map((s, i) => `<li class="${i === n ? "active" : i < n ? "done" : ""}">${escape(s)}</li>`).join("")}</ol><section class="panel">${body}<div id="wizard-error" role="alert"></div></section>`;
  bind("back", "click", () => loadQueue().catch((e) => notify(e.message)));
}
const wizardError = (e) => {
  const el = $("#wizard-error");
  if (el) {
    el.className = "error-box";
    el.textContent = e.message;
  } else notify(e.message);
};
async function wizard() {
  Object.keys(wz).forEach((k) => delete wz[k]);
  const data = await api("/wizard/entities");
  wizardFrame(
    0,
    `<div class="field"><label for="wz-entity">Právní zaměstnavatel</label><select id="wz-entity"><option value="">Vyberte firmu…</option>${data.entities.map((e) => `<option value="${escape(e.id)}">${escape(e.legal_name || e.name)}${e.ico ? " · IČO " + escape(e.ico) : ""}</option>`).join("")}</select><p class="help">Značka provozu sama zaměstnavatele nepotvrzuje. Vyberte firmu ze smlouvy.</p></div><div class="actions"><span></span><button id="wz-next" class="btn primary">Pokračovat →</button></div>${data.can_create ? `<details><summary>Firma v Nexusu chybí</summary><form id="wz-entity-form"><div class="fields"><div class="field"><label for="wz-legal">Obchodní firma</label><input id="wz-legal" required maxlength="300"></div><div class="field"><label for="wz-name">Krátký název</label><input id="wz-name" required maxlength="200"></div><div class="field"><label for="wz-code">Kód (A–Z, 0–9)</label><input id="wz-code" required pattern="[A-Z0-9-]{2,20}"></div><div class="field"><label for="wz-ico">IČO</label><input id="wz-ico" required pattern="[0-9]{8}" inputmode="numeric"></div><div class="field"><label for="wz-division">Divize</label><input id="wz-division" maxlength="50"></div><div class="field full"><label for="wz-source">Zdroj údajů</label><input id="wz-source" required maxlength="300" placeholder="Např. výpis z obchodního rejstříku ze dne…"></div></div><button class="btn">Založit firmu</button></form></details>` : ""}`,
  );
  bind("wz-next", "click", () => {
    wz.entity = data.entities.find((e) => e.id === $("#wz-entity").value);
    if (!wz.entity) return wizardError(Error("Vyberte firmu."));
    wizardPerson().catch(wizardError);
  });
  bind("wz-entity-form", "submit", async (e) => {
    e.preventDefault();
    try {
      await api("/wizard/entities", "POST", {
        legal_name: $("#wz-legal").value,
        name: $("#wz-name").value,
        code: $("#wz-code").value,
        ico: $("#wz-ico").value,
        division: $("#wz-division").value,
        source: $("#wz-source").value,
      });
      await wizard();
    } catch (err) {
      wizardError(err);
    }
  });
}
async function wizardPerson(q = "") {
  const data = await api(
    `/wizard/people?entity_id=${encodeURIComponent(wz.entity.id)}&q=${encodeURIComponent(q)}`,
  );
  const createKey = key();
  wizardFrame(
    1,
    `<p class="muted">${escape(wz.entity.legal_name || wz.entity.name)}</p><form id="wz-search" class="row"><input id="wz-q" value="${escape(q)}" placeholder="Hledat jméno nebo e-mail (min. 3 znaky)" maxlength="100"><button class="btn">Hledat</button></form><div class="document-list">${data.people.map((p) => `<article class="document"><div><h3>${escape(p.name)}</h3><p class="help">${p.birth_year ? "Ročník " + escape(p.birth_year) + " · " : ""}${p.employments.length} pracovních vztahů · ${p.contacts.length ? escape(p.contacts.map((c) => c.address).join(", ")) : "bez ověřeného e-mailu"}</p></div><button class="btn pick-person" data-id="${escape(p.id)}">Vybrat</button></article>`).join("") || '<p class="muted">U této firmy zatím nikdo není. Vyhledejte osobu, nebo ji založte.</p>'}</div>${data.hidden_matches ? `<div class="notice">Další ${data.hidden_matches} shod je mimo vaši působnost. Požádejte správce o propojení, nezakládejte duplicitu.</div>` : ""}<details><summary>Založit novou osobu</summary><form id="wz-person-form"><div class="fields"><div class="field"><label for="wz-first">Jméno</label><input id="wz-first" required maxlength="100"></div><div class="field"><label for="wz-last">Příjmení</label><input id="wz-last" required maxlength="100"></div><div class="field"><label for="wz-title">Titul před jménem</label><input id="wz-title" maxlength="20"></div><div class="field"><label for="wz-birth">Datum narození (pokud je známé)</label><input id="wz-birth" type="date"></div></div><label class="checkbox" id="wz-confirm-wrap" hidden><input id="wz-confirm-new" type="checkbox">Ověřil/a jsem, že jde o jiného člověka než nalezené osoby.</label><button class="btn">Založit osobu</button></form></details>`,
  );
  bind("wz-search", "submit", (e) => {
    e.preventDefault();
    wizardPerson($("#wz-q").value).catch(wizardError);
  });
  document.querySelectorAll(".pick-person").forEach(
    (b) =>
      (b.onclick = () => {
        wz.person = data.people.find((p) => p.id === b.dataset.id);
        wizardEmployment().catch(wizardError);
      }),
  );
  bind("wz-person-form", "submit", async (e) => {
    e.preventDefault();
    try {
      const r = await api("/wizard/people", "POST", {
        request_key: createKey,
        entity_id: wz.entity.id,
        first_name: $("#wz-first").value,
        last_name: $("#wz-last").value,
        title_before: $("#wz-title").value,
        birth_date: $("#wz-birth").value,
        confirm_new: $("#wz-confirm-new").checked,
      });
      wz.person = r.person;
      await wizardEmployment();
    } catch (err) {
      if (err.status === 409) $("#wz-confirm-wrap").hidden = false;
      wizardError(err);
    }
  });
}
async function wizardEmployment() {
  const list = wz.person.employments.filter((x) => x.entity_id === wz.entity.id);
  wizardFrame(
    2,
    `<p class="muted">${escape(wz.person.name)} · ${escape(wz.entity.legal_name || wz.entity.name)}</p><div class="document-list">${list.map((x) => `<article class="document"><div><h3>${escape(x.type)} · ${escape(x.position || "Pozice k upřesnění")}</h3><p class="help">Od ${escape(x.start || "?")}${x.end ? " do " + escape(x.end) : ""} · ${escape(x.status)}</p></div>${x.status !== "terminated" ? `<button class="btn pick-employment" data-id="${escape(x.id)}">Vybrat</button>` : ""}</article>`).join("") || '<p class="muted">U této firmy nemá zapsaný žádný vztah.</p>'}</div><details ${list.length ? "" : "open"}><summary>Zapsat doložený pracovní vztah</summary><form id="wz-employment-form"><div class="notice">Vztah se zapisuje jen podle podepsané smlouvy nebo dohody. Dotazník sám žádný vztah nezakládá.</div><div class="fields"><div class="field"><label for="wz-type">Druh</label><select id="wz-type" required><option value="HPP">Pracovní poměr</option><option value="DPP">Dohoda o provedení práce</option><option value="DPC">Dohoda o pracovní činnosti</option></select></div><div class="field"><label for="wz-position">Pozice</label><input id="wz-position" required maxlength="100"></div><div class="field"><label for="wz-start">Vznik vztahu</label><input id="wz-start" type="date" required></div><div class="field full"><label for="wz-evidence">Doklad (co a kde je uloženo)</label><input id="wz-evidence" required maxlength="500"></div></div><label class="checkbox"><input id="wz-employment-confirm" type="checkbox" required>Vztah je doložen podepsanou smlouvou nebo dohodou.</label><button class="btn">Zapsat vztah</button></form></details>`,
  );
  document.querySelectorAll(".pick-employment").forEach(
    (b) =>
      (b.onclick = () => {
        wz.employment = b.dataset.id;
        wizardPurpose().catch(wizardError);
      }),
  );
  bind("wz-employment-form", "submit", async (e) => {
    e.preventDefault();
    try {
      const r = await api("/wizard/employments", "POST", {
        entity_id: wz.entity.id,
        person_id: wz.person.id,
        employment_type: $("#wz-type").value,
        position: $("#wz-position").value,
        date_start: $("#wz-start").value,
        evidence: $("#wz-evidence").value,
        confirmed: $("#wz-employment-confirm").checked,
      });
      wz.employment = r.employment_id;
      await wizardPurpose();
    } catch (err) {
      wizardError(err);
    }
  });
}
async function wizardPurpose() {
  const staff = await api(`/wizard/staff?entity_id=${encodeURIComponent(wz.entity.id)}`);
  const requestKey = key();
  wizardFrame(
    3,
    `<form id="wz-case-form"><div class="fields"><div class="field"><label for="wz-kind">Účel</label><select id="wz-kind"><option value="complete_existing">Doplnění stávající evidence</option><option value="change">Změna údajů</option></select></div><div class="field"><label>Šablona</label><input value="${escape(meta.template_version)}" disabled></div><div class="field"><label for="wz-hr">Odpovědné HR</label><select id="wz-hr" required>${staff.hr.map((p) => `<option value="${escape(p.id)}" ${p.id === meta.person_id ? "selected" : ""}>${escape(p.name)}</option>`).join("")}</select></div><div class="field"><label for="wz-payroll">Mzdová osoba</label><select id="wz-payroll"><option value="">Zatím neurčena</option>${staff.payroll.map((p) => `<option value="${escape(p.id)}">${escape(p.name)}</option>`).join("")}</select><p class="help">Bez určené mzdové osoby lze vše připravit a zkontrolovat, ale převzetí mzdami se nezapíše.</p></div></div><button class="btn primary">Vytvořit případ →</button></form>`,
  );
  bind("wz-case-form", "submit", async (e) => {
    e.preventDefault();
    try {
      const c = await api("/cases", "POST", {
        employment_id: wz.employment,
        kind: $("#wz-kind").value,
        request_key: requestKey,
        hr_owner_id: $("#wz-hr").value,
        payroll_owner_id: $("#wz-payroll").value || null,
      });
      await openCase(c.id, true);
    } catch (err) {
      wizardError(err);
    }
  });
}

// ---- case ---------------------------------------------------------------------
async function openCase(id, setup = false) {
  current = await api("/cases/" + id);
  answers = structuredClone(current.answers);
  dirty = false;
  saveFailed = false;
  clearHidden = false;
  const steps = formSections().length + 2;
  step = ["draft", "returned"].includes(current.status) && !setup ? 0 : steps - 1;
  history.replaceState(
    null,
    "",
    portal ? "/hr/entry" : "/people/hr?case=" + encodeURIComponent(id),
  );
  renderCase();
  if (setup) $("#setup-panel")?.scrollIntoView({ block: "start" });
}
function inputFor(f, val, attrs) {
  if (f.type === "select")
    return `<select ${attrs}><option value="">Vyberte…</option>${f.options.map(([v, l]) => `<option value="${escape(v)}" ${val === v ? "selected" : ""}>${escape(l)}</option>`).join("")}</select>`;
  if (f.type === "textarea")
    return `<textarea ${attrs} maxlength="2000">${escape(val)}</textarea>`;
  return `<input ${attrs} type="${escape(f.type)}" value="${escape(val)}" maxlength="300" autocomplete="off">`;
}
function renderField(f, act) {
  if (f.type === "list") return listHTML(f, act);
  const val = answers[f.key] ?? "";
  const id = "f-" + f.key;
  const common = `id="${id}" data-field="${escape(f.key)}" ${editable() ? "" : "disabled"}`;
  const flag = current.review_flags
    ? `<label class="review-flag"><input type="checkbox" data-review="${escape(f.key)}" ${reviewed(f.key) ? "checked" : ""} ${editable() ? "" : "disabled"}>Potřebuji upřesnit</label>`
    : "";
  return `<div class="field ${f.type === "textarea" ? "full" : ""}" data-wrapper="${escape(f.key)}" ${act[f.key] ? "" : "hidden"}><label for="${id}">${escape(f.label)}${f.required ? " *" : ""}</label>${inputFor(f, val, common)}${f.help ? `<p class="help">${escape(f.help)}</p>` : ""}${flag}</div>`;
}
function listHTML(f, act) {
  const rows = answers[f.key] || [];
  const itemActive = (sub, row) =>
    Object.entries(sub.when || {}).every(([r, v]) => v.includes(row[r]));
  return `<div class="field full list-field" data-wrapper="${escape(f.key)}" ${act[f.key] ? "" : "hidden"}><h3>${escape(f.label)}</h3>${rows
    .map(
      (row, i) =>
        `<article class="child"><div class="row"><h3>${escape(f.label)} ${i + 1}</h3>${editable() ? `<button type="button" class="btn text remove-item" data-list="${escape(f.key)}" data-index="${i}">Odebrat</button>` : ""}</div><div class="fields">${f.items
          .map((sub) => {
            const id = `item-${f.key}-${i}-${sub.key}`;
            if (sub.type === "months")
              return `<fieldset class="field full"><legend>${escape(sub.label)}</legend><div class="months">${Array.from({ length: 12 }, (_, n) => `<label class="month"><input type="checkbox" data-month-list="${escape(f.key)}" data-index="${i}" value="${n + 1}" ${(row.months || []).includes(n + 1) ? "checked" : ""} ${editable() ? "" : "disabled"}>${n + 1}.</label>`).join("")}</div></fieldset>`;
            const attrs = `id="${id}" data-list="${escape(f.key)}" data-index="${i}" data-key="${escape(sub.key)}" ${editable() ? "" : "disabled"}`;
            return `<div class="field" ${itemActive(sub, row) ? "" : "hidden"}><label for="${id}">${escape(sub.label)}${sub.required ? " *" : ""}</label>${inputFor(sub, row[sub.key] ?? "", attrs)}</div>`;
          })
          .join("")}</div></article>`,
    )
    .join(
      "",
    )}${editable() ? `<button type="button" class="btn add-item" data-list="${escape(f.key)}">＋ ${escape(f.add_label || "Přidat")}</button>` : ""}${current.review_flags ? `<label class="review-flag"><input type="checkbox" data-review="${escape(f.key)}" ${reviewed(f.key) ? "checked" : ""} ${editable() ? "" : "disabled"}>Potřebuji upřesnit</label>` : ""}</div>`;
}
function emptyItem(f) {
  return Object.fromEntries(f.items.map((s) => [s.key, s.type === "months" ? [] : ""]));
}
function requirementsHTML() {
  if (portal) return "";
  const opts = [
    ["unknown", "Neověřeno"],
    ["pending", "Čeká na doložení"],
    ["verified", "Ověřeno"],
    ["not_applicable", "Nepoužije se"],
    ["deferred", "Odloženo s důvodem"],
  ];
  const ways = [
    ["", "Způsob ověření…"],
    ["document", "Přiložený doklad"],
    ["inspection", "Nahlédnutí do originálu"],
    ["register", "Ověřeno v registru"],
    ["statement", "Prohlášení zaměstnance"],
  ];
  const can =
    current.permissions.hr &&
    !["reviewed", "payroll_received"].includes(current.status);
  const suggested = current.suggested_requirements || [];
  return `<details id="requirements-panel" ${current.status === "submitted" || !current.requirements_confirmed ? "open" : ""}><summary>Požadavky a doklady · nastavení HR</summary><p class="help">Každý požadavek má stav, vlastníka a způsob ověření. Kopii dokladu ukládejte jen tam, kde je opravdu potřeba; ověření nahlédnutím stačí zapsat referencí.</p>${can && suggested.length ? `<div class="notice">Podle odpovědí navrhujeme doplnit: ${suggested.map((r) => escape(r.label)).join(", ")}. <button type="button" id="add-suggested" class="btn text">Přidat navržené</button></div>` : ""}<form id="requirements-form">${current.requirements.map((r, i) => `<div class="requirement"><h3>${escape(r.label)} <small class="muted">· ${escape(r.owner_role)}</small></h3><div class="fields"><div class="field"><label for="r-status-${i}">Stav</label><select id="r-status-${i}" ${can ? "" : "disabled"}>${opts.map(([v, l]) => `<option value="${v}" ${r.status === v ? "selected" : ""}>${l}</option>`).join("")}</select></div><div class="field"><label for="r-way-${i}">Ověření</label><select id="r-way-${i}" ${can ? "" : "disabled"}>${ways.map(([v, l]) => `<option value="${v}" ${(r.verification || "") === v ? "selected" : ""}>${l}</option>`).join("")}</select></div><div class="field"><label for="r-ref-${i}">Reference důkazu</label><input id="r-ref-${i}" value="${escape(r.evidence_ref)}" maxlength="300" ${can ? "" : "disabled"}></div><div class="field"><label for="r-reason-${i}">Důvod výjimky / odkladu</label><input id="r-reason-${i}" value="${escape(r.reason)}" maxlength="500" ${can ? "" : "disabled"}></div></div><label class="checkbox" style="margin-top:14px"><input id="r-block-${i}" type="checkbox" ${r.blocks_payroll ? "checked" : ""} ${can ? "" : "disabled"}>Nutné před předáním mzdové roli</label></div>`).join("")}${can ? '<label class="checkbox"><input id="r-confirm" type="checkbox" required>Potvrzuji, že rozsah požadavků odpovídá pracovnímu vztahu a dohodnutému mzdovému minimu.</label><button class="btn" style="margin-top:18px">Uložit požadavky</button>' : ""}</form></details>`;
}
function valueLabel(f, v) {
  return f.options?.find((o) => o[0] === v)?.[1] || v;
}
function summaryHTML() {
  const act = activity();
  const rows = allFields()
    .filter((f) => act[f.key] && (!isEmpty(answers[f.key]) || reviewed(f.key)))
    .map((f) => {
      if (f.type === "list")
        return `<dt>${escape(f.label)}</dt><dd>${(answers[f.key] || []).map((row) => escape(f.items.filter((s) => s.type !== "months" && row[s.key]).slice(0, 3).map((s) => valueLabel(s, row[s.key])).join(" · "))).join("<br>")}${reviewed(f.key) ? " <em>(k upřesnění)</em>" : ""}</dd>`;
      return `<dt>${escape(f.label)}</dt><dd>${escape(valueLabel(f, answers[f.key] || ""))}${reviewed(f.key) ? " <em>(k upřesnění)</em>" : ""}</dd>`;
    })
    .join("");
  const attest = editable() && current.review_flags
    ? '<label class="checkbox"><input id="attest" type="checkbox">Údaje jsem vyplnil/a podle svého nejlepšího vědomí. Beru na vědomí, že odeslání není podpis smlouvy, Prohlášení poplatníka ani potvrzení školení BOZP.</label>'
    : "";
  return `<h2 id="step-title" tabindex="-1">Kontrola a předání</h2><p class="section-description">Podání se uloží jako samostatná verze. HR může vrátit konkrétní nedostatky k doplnění.</p>${current.issues.length ? `<div class="notice warn"><strong>K individuálnímu ověření:</strong><ul>${current.issues.map((x) => `<li>${escape(x)}</li>`).join("")}</ul></div>` : ""}<dl class="summary">${rows}</dl>${requirementsHTML()}<div class="notice">Tento krok předává podklady. Nenahrazuje podpis smlouvy ani Prohlášení poplatníka, školení, prohlídku nebo zpracování mzdy.</div><div id="form-errors" role="alert"></div>${attest}${editable() ? '<button id="submit-case" class="btn primary">Odeslat ke kontrole HR →</button>' : ""}${current.permissions.hr && ["submitted", "reviewed"].includes(current.status) ? '<div class="field" style="margin-top:22px"><label for="review-note">Poznámka / co konkrétně doplnit (uveďte pole)</label><textarea id="review-note" maxlength="1200"></textarea></div><div class="actions"><button id="return-case" class="btn danger">Vrátit k doplnění</button>' + (current.status === "submitted" ? '<button id="review-case" class="btn primary">Potvrdit kontrolu HR</button>' : "") + "</div>" : ""}${payrollHTML()}<details><summary>Historie případu</summary><ol class="history">${current.history.map((h) => `<li><b>${escape(actionLabels[h.action] || h.action)} · verze ${h.revision}</b><br>${escape(new Date(h.at + "Z").toLocaleString("cs-CZ"))}${h.note ? "<br>" + escape(h.note) : ""}</li>`).join("") || "<li>Zatím bez předání.</li>"}</ol></details>`;
}
function payrollHTML() {
  if (portal) return "";
  let out = "";
  if ((current.permissions.hr || current.permissions.payroll) && ["reviewed", "payroll_received"].includes(current.status))
    out += `<div class="notice"><strong>Export schválené verze ${current.revision}</strong><br>Neutrální formát pro mzdovou účetní (není to importní soubor POHODA ani PAMICA).<div class="actions"><a class="btn" href="${apiBase}/cases/${encodeURIComponent(current.id)}/export?fmt=zip">Balík ZIP</a><a class="btn text" href="${apiBase}/cases/${encodeURIComponent(current.id)}/export?fmt=xlsx">XLSX</a><a class="btn text" href="${apiBase}/cases/${encodeURIComponent(current.id)}/export?fmt=csv">CSV</a><a class="btn text" href="${apiBase}/cases/${encodeURIComponent(current.id)}/export?fmt=json">JSON</a></div></div>`;
  if (current.status === "reviewed" && !current.owners?.payroll)
    out += '<div class="notice warn">Mzdová osoba není určena. Případ je připravený pro mzdy, převzetí se nezapíše.</div>';
  if (current.permissions.payroll_owner && current.status === "reviewed")
    out += '<div class="field" style="margin-top:22px"><label for="payroll-note">Co je potřeba opravit</label><textarea id="payroll-note" maxlength="1200"></textarea></div><div class="actions"><button id="payroll-return-case" class="btn danger">Vrátit z mzdové kontroly</button><button id="receive-case" class="btn primary">Převzít tuto verzi podkladů</button></div>';
  if (current.permissions.payroll_owner && current.status === "payroll_received")
    out += '<div class="field" style="margin-top:22px"><label for="payroll-note">Konkrétní údaj (program a datum importu, číslo podání)</label><input id="payroll-note" maxlength="1200"></div><div class="actions"><button id="import-case" class="btn">Potvrdit úspěšný import</button><button id="filing-case" class="btn">Potvrdit úřední podání</button></div>';
  return out;
}
function handoverHTML() {
  const h = current.handover;
  if (!h || (!h.equipment.length && !h.benefits.length && !h.car)) return "";
  return `<div class="notice"><strong>Ve vaší evidenci je předáno:</strong> ${escape([...h.equipment, ...h.benefits, ...(h.car ? [h.car] : [])].join(", "))}. Pokud něco nesedí, napište to níže. Nic se tím neobjednává.</div>`;
}
function setupHTML() {
  if (portal || !current.permissions.hr) return "";
  const t = current.terms;
  const items = [
    ["Odpovědné osoby", current.owners?.hr ? `HR: ${current.owners.hr}${current.owners.payroll ? " · mzdy: " + current.owners.payroll : " · mzdová osoba neurčena"}` : "Neurčeno", "owners"],
    ["Interní kontext HR", t ? `Verze ${t.revision}, účinnost od ${t.effective_from}` : "Nevyplněno", "terms"],
    ["Požadavky HR", current.requirements_confirmed ? "Potvrzeny" : "Čekají na potvrzení", "requirements"],
    ["Ověřený kontakt", "Kontakt pro kód je v osobní kartě", "contact"],
    ["Pozvánka", "Odkaz s kódem na ověřený kontakt", "invite"],
  ];
  return `<section class="panel" id="setup-panel"><div class="row"><h2>Příprava HR</h2><span class="eyebrow">${escape(current.template_version)}</span></div><ol class="setup-list">${items.map(([title, state, id]) => `<li><div><b>${escape(title)}</b><br><span class="muted">${escape(state)}</span></div><button class="btn text setup-open" data-panel="${id}">Upravit</button></li>`).join("")}</ol><div id="setup-detail"></div></section>`;
}
async function openSetup(panel) {
  if (panel === "requirements") {
    step = formSections().length + 1;
    renderCase();
    $("#requirements-panel")?.setAttribute("open", "");
    $("#requirements-panel")?.scrollIntoView({ block: "start" });
    return;
  }
  if (panel === "invite") return openInvitations();
  const box = $("#setup-detail");
  if (panel === "owners") {
    const staff = await api(`/wizard/staff?entity_id=${encodeURIComponent(current.context.entity_id)}`);
    box.innerHTML = `<form id="owners-form"><div class="fields"><div class="field"><label for="own-hr">Odpovědné HR</label><select id="own-hr">${staff.hr.map((p) => `<option value="${escape(p.id)}" ${p.id === current.owners.hr_id ? "selected" : ""}>${escape(p.name)}</option>`).join("")}</select></div><div class="field"><label for="own-payroll">Mzdová osoba</label><select id="own-payroll"><option value="">Zatím neurčena</option>${staff.payroll.map((p) => `<option value="${escape(p.id)}" ${p.id === current.owners.payroll_id ? "selected" : ""}>${escape(p.name)}</option>`).join("")}</select></div></div><button class="btn">Uložit</button></form>`;
    bind("owners-form", "submit", async (e) => {
      e.preventDefault();
      try {
        current = await api(`/cases/${current.id}/owners`, "PUT", {
          expected_version: current.version,
          hr_owner_id: $("#own-hr").value,
          payroll_owner_id: $("#own-payroll").value || null,
        });
        renderCase();
      } catch (err) {
        notify(err.message);
      }
    });
  } else if (panel === "terms") {
    const t = current.terms?.data || {};
    const lines = (list, keys) => (list || []).map((x) => keys.map((k) => x[k] || "").join(" | ")).join("\n");
    const sel = (id, value, opts) => `<select id="${id}">${opts.map(([v, l]) => `<option value="${v}" ${value === v ? "selected" : ""}>${l}</option>`).join("")}</select>`;
    box.innerHTML = `<form id="terms-form"><p class="help">Interní kontext vidí jen HR a mzdová role. Zaměstnanec vidí pouze názvy předaného vybavení a benefitů.</p><div class="fields"><div class="field"><label for="t-effective">Účinnost od</label><input id="t-effective" type="date" required value="${escape(current.terms?.effective_from || current.context.start || "")}"></div><div class="field"><label for="t-source">Zdroj (smlouva, dodatek…)</label><input id="t-source" required maxlength="300"></div><div class="field"><label for="t-signed">Smlouva podepsána</label><input id="t-signed" type="date" value="${escape(t.contract_signed_on || "")}"></div><div class="field"><label for="t-ref">Kde je smlouva uložena</label><input id="t-ref" maxlength="300" value="${escape(t.contract_ref || "")}"></div><div class="field"><label for="t-workplace">Místo výkonu práce</label><input id="t-workplace" maxlength="300" value="${escape(t.workplace || "")}"></div><div class="field"><label for="t-fte">Úvazek (0–1)</label><input id="t-fte" maxlength="5" value="${escape(t.fte || "")}"></div><div class="field"><label for="t-hours">Hodin týdně</label><input id="t-hours" maxlength="4" value="${escape(t.weekly_hours || "")}"></div><div class="field"><label for="t-schedule">Režim</label>${sel("t-schedule", t.schedule || "", [["", "—"], ["fixed", "Pevná pracovní doba"], ["flexible", "Pružná"], ["shift", "Směny"], ["uneven", "Nerovnoměrně rozvržená"], ["review", "K upřesnění"]])}</div><div class="field"><label for="t-paytype">Odměna</label>${sel("t-paytype", t.pay_type || "", [["", "—"], ["monthly", "Měsíční mzda"], ["hourly", "Hodinová"], ["agreement", "Odměna z dohody"], ["review", "K upřesnění"]])}</div><div class="field"><label for="t-pay">Částka (Kč)</label><input id="t-pay" maxlength="12" value="${escape(t.pay_amount || "")}"></div><div class="field"><label for="t-probation">Zkušební doba do</label><input id="t-probation" type="date" value="${escape(t.probation_until || "")}"></div><div class="field"><label for="t-fixed">Doba určitá do</label><input id="t-fixed" type="date" value="${escape(t.fixed_term_until || "")}"></div><div class="field full"><label for="t-equipment">Předané vybavení (řádek: položka | datum | reference)</label><textarea id="t-equipment">${escape(lines(t.equipment, ["item", "handed_over_on", "evidence_ref"]))}</textarea></div><div class="field full"><label for="t-benefits">Benefity (řádek: benefit | od | poznámka)</label><textarea id="t-benefits">${escape(lines(t.benefits, ["benefit", "since", "note"]))}</textarea></div><div class="field"><label for="t-car">Služební vůz</label>${sel("t-car", t.car?.assigned || "no", [["no", "Nepřidělen"], ["yes", "Přidělen"], ["review", "K upřesnění"]])}</div><div class="field"><label for="t-vehicle">Vozidlo</label><input id="t-vehicle" maxlength="200" value="${escape(t.car?.vehicle || "")}"></div><div class="field"><label for="t-private">Soukromé užití</label>${sel("t-private", t.car?.private_use || "", [["", "—"], ["yes", "Ano"], ["no", "Ne"], ["review", "K upřesnění"]])}</div><div class="field full"><label for="t-note">Poznámka HR</label><textarea id="t-note" maxlength="1000">${escape(t.note || "")}</textarea></div></div><button class="btn">Uložit novou verzi</button></form>`;
    const parse = (text, keys) =>
      text.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => {
        const parts = l.split("|").map((p) => p.trim());
        return Object.fromEntries(keys.map((k, i) => [k, parts[i] || ""]));
      });
    bind("terms-form", "submit", async (e) => {
      e.preventDefault();
      try {
        await api(`/employments/${encodeURIComponent(current.context.employment_id)}/terms`, "POST", {
          expected_revision: current.terms?.revision || 0,
          effective_from: $("#t-effective").value,
          source: $("#t-source").value,
          data: {
            contract_signed_on: $("#t-signed").value,
            contract_ref: $("#t-ref").value,
            workplace: $("#t-workplace").value,
            fte: $("#t-fte").value,
            weekly_hours: $("#t-hours").value,
            schedule: $("#t-schedule").value,
            pay_type: $("#t-paytype").value,
            pay_amount: $("#t-pay").value,
            probation_until: $("#t-probation").value,
            fixed_term_until: $("#t-fixed").value,
            equipment: parse($("#t-equipment").value, ["item", "handed_over_on", "evidence_ref"]),
            benefits: parse($("#t-benefits").value, ["benefit", "since", "note"]),
            car: { assigned: $("#t-car").value, vehicle: $("#t-vehicle").value, private_use: $("#t-private").value },
            note: $("#t-note").value,
          },
        });
        await openCase(current.id, true);
      } catch (err) {
        notify(err.message);
      }
    });
  } else if (panel === "contact") {
    box.innerHTML = `<form id="contact-form"><p class="help">Kód pro vstup chodí jen na adresu uloženou v osobní kartě. Zapište ji jen tehdy, když jste ji ověřili (např. z přímé pracovní korespondence).</p><div class="fields"><div class="field"><label for="c-source">Typ</label><select id="c-source"><option value="work">Pracovní e-mail</option><option value="personal">Soukromý e-mail</option></select></div><div class="field"><label for="c-email">E-mail</label><input id="c-email" type="email" required maxlength="254"></div><div class="field full"><label for="c-verification">Jak byl ověřen</label><input id="c-verification" required maxlength="300"></div></div><label class="checkbox"><input id="c-confirm" type="checkbox" required>Tento kontakt ovládá příslušný zaměstnanec.</label><button class="btn">Uložit ověřený kontakt</button></form>`;
    bind("contact-form", "submit", async (e) => {
      e.preventDefault();
      try {
        await api(`/wizard/people/${encodeURIComponent(current.context.person_id)}/contact`, "PUT", {
          entity_id: current.context.entity_id,
          source: $("#c-source").value,
          email: $("#c-email").value,
          verification: $("#c-verification").value,
          confirmed: $("#c-confirm").checked,
        });
        notify("Kontakt uložen do osobní karty.");
        await openInvitations();
      } catch (err) {
        notify(err.message);
      }
    });
  }
}
function renderCase() {
  const visible = formSections();
  const nav = [...visible, { title: "Doklady" }, { title: "Kontrola a předání" }];
  if (step >= nav.length) step = nav.length - 1;
  const s = nav[step];
  const act = activity();
  const hidden = hiddenKeys();
  root.innerHTML = `<div class="row">${portal ? "" : '<button id="queue" class="btn text back-case">← Vaše případy</button>'}${current.permissions.hr ? '<button id="invitations" class="btn">Pozvat zaměstnance</button>' : ""}</div><div id="invite-panel"></div>${setupHTML()}<div class="intro"><div><div class="topline"><span class="eyebrow">${escape(current.context.employer)}</span>${pill(current.status)}</div><h1>${escape(current.context.name)}</h1><p class="muted">${escape(current.context.position)} · ${escape(current.context.employment_type)}<br>${current.kind === "change" ? "Změna údajů" : "Doplnění existující personální evidence"}${current.owners?.hr ? " · kontaktní osoba HR: " + escape(current.owners.hr) : ""}</p></div><span class="eyebrow">${step + 1} / ${nav.length}</span></div>${current.status === "returned" ? `<div class="notice warn"><b>Prosíme o doplnění:</b> ${escape([...current.history].reverse().find((h) => ["return", "payroll_return"].includes(h.action))?.note || "Podívejte se do historie případu.")}</div>` : ""}${hidden.length && editable() ? `<div class="notice">Máte uložené odpovědi z jiné volby (${hidden.length}). Zůstávají uložené, ale neodešlou se. <button type="button" id="clear-hidden" class="btn text">Vymazat je</button></div>` : ""}<div class="workspace"><aside class="steps">${nav.map((x, i) => `<button class="step ${step === i ? "active" : ""}" data-step="${i}" ${step === i ? 'aria-current="step"' : ""}><span>${i + 1}</span>${escape(x.title)}</button>`).join("")}<div class="context"><strong>Právní zaměstnavatel</strong>${escape(current.context.employer)}<br>IČO: ${escape(current.context.ico || "K ověření")}<br>Vztah od: ${escape(current.context.start || "K ověření")}</div></aside><section class="panel" id="form-panel">${step < visible.length ? `<h2 tabindex="-1" id="step-title">${escape(s.title)}</h2><p class="section-description">${escape(s.description || "")}</p>${s.id === "work" ? handoverHTML() : ""}<div class="fields">${s.fields.map((f) => renderField(f, act)).join("")}</div>` : step === visible.length ? documentsHTML() : summaryHTML()}<div class="actions">${step > 0 ? '<button id="prev" class="btn">← Zpět</button>' : "<span></span>"}<span class="save-status" id="save-status" role="status" aria-live="polite">${dirty ? "Změny čekají na uložení…" : editable() ? "Uloženo na serveru" : "Odeslaná verze " + current.revision}</span>${step < nav.length - 1 ? '<button id="next" class="btn primary">Pokračovat →</button>' : ""}</div></section></div>`;
  bind("queue", "click", () => loadQueue().catch((e) => notify(e.message)));
  document
    .querySelectorAll("[data-step]")
    .forEach((b) => (b.onclick = () => goStep(+b.dataset.step)));
  bind("prev", "click", () => goStep(step - 1));
  bind("next", "click", () => goStep(step + 1));
  document.querySelectorAll("[data-field]").forEach((el) =>
    el.addEventListener(el.tagName === "SELECT" ? "change" : "input", () => {
      answers[el.dataset.field] = el.value;
      markDirty();
      if (el.tagName === "SELECT") refreshBranches();
    }),
  );
  document.querySelectorAll("[data-review]").forEach((el) =>
    el.addEventListener("change", () => {
      const set = new Set(answers._review || []);
      el.checked ? set.add(el.dataset.review) : set.delete(el.dataset.review);
      answers._review = [...set];
      markDirty();
    }),
  );
  bindLists();
  bind("clear-hidden", "click", () => {
    const labels = allFields().filter((f) => hidden.includes(f.key)).map((f) => f.label);
    if (!confirm("Opravdu trvale vymazat tyto skryté odpovědi?\n\n" + labels.join("\n"))) return;
    hidden.forEach((k) => delete answers[k]);
    answers._review = (answers._review || []).filter((k) => !hidden.includes(k));
    clearHidden = true;
    markDirty();
    flush().then(renderCase).catch((e) => notify(e.message));
  });
  bind("submit-case", "click", () => perform("submit"));
  bind("return-case", "click", () => perform("return"));
  bind("review-case", "click", () => perform("review"));
  bind("receive-case", "click", () => perform("payroll_receive"));
  bind("payroll-return-case", "click", () => perform("payroll_return"));
  bind("import-case", "click", () => perform("payroll_import"));
  bind("filing-case", "click", () => perform("authority_filing"));
  bind("requirements-form", "submit", saveRequirements);
  bind("requirements-form", "input", () => {
    requirementsDirty = true;
  });
  bind("add-suggested", "click", () => {
    current.requirements = [...current.requirements, ...current.suggested_requirements];
    current.suggested_requirements = [];
    requirementsDirty = true;
    renderCase();
    $("#requirements-panel")?.setAttribute("open", "");
  });
  bind("invitations", "click", openInvitations);
  document
    .querySelectorAll(".setup-open")
    .forEach((b) => (b.onclick = () => openSetup(b.dataset.panel).catch((e) => notify(e.message))));
  bindDocuments();
  $(".step.active")?.scrollIntoView({ block: "nearest", inline: "center" });
}
function refreshBranches() {
  // Re-render the current step so newly active/hidden branches and steps update;
  // values stay in `answers`, focus moves to the changed control.
  const focused = document.activeElement?.id;
  renderCase();
  if (focused) document.getElementById(focused)?.focus();
}
function bindLists() {
  document.querySelectorAll("[data-list][data-key]").forEach((el) =>
    el.addEventListener(el.tagName === "SELECT" ? "change" : "input", () => {
      answers[el.dataset.list][+el.dataset.index][el.dataset.key] = el.value;
      markDirty();
      if (el.tagName === "SELECT") refreshBranches();
    }),
  );
  document.querySelectorAll("[data-month-list]").forEach((el) =>
    el.addEventListener("change", () => {
      const list = el.dataset.monthList,
        i = +el.dataset.index;
      answers[list][i].months = [
        ...document.querySelectorAll(`[data-month-list="${list}"][data-index="${i}"]:checked`),
      ].map((x) => +x.value);
      markDirty();
    }),
  );
  document.querySelectorAll(".add-item").forEach(
    (b) =>
      (b.onclick = () => {
        const f = allFields().find((x) => x.key === b.dataset.list);
        answers[f.key] ??= [];
        answers[f.key].push(emptyItem(f));
        markDirty();
        renderCase();
      }),
  );
  document.querySelectorAll(".remove-item").forEach(
    (b) =>
      (b.onclick = () => {
        if (!confirm("Odebrat tuto položku?")) return;
        answers[b.dataset.list].splice(+b.dataset.index, 1);
        markDirty();
        renderCase();
      }),
  );
}
async function goStep(n) {
  if (attachmentBusy || busy) return;
  if (requirementsDirty) return notify("Nejprve uložte nastavení požadavků.");
  try {
    await flush();
    if (dirty || saveFailed) return;
    step = n;
    renderCase();
    $("#step-title")?.focus();
  } catch (e) {
    notify(e.message);
  }
}
async function perform(action) {
  if (busy) return;
  if (requirementsDirty) return notify("Nejprve uložte nastavení požadavků.");
  if (action === "submit" && current.review_flags && !$("#attest")?.checked)
    return notify("Před odesláním potvrďte prohlášení nad tlačítkem.");
  busy = true;
  try {
    await flush();
    if (dirty) throw Error("Nejprve je potřeba uložit všechny změny.");
    const payrollNote = $("#payroll-note")?.value;
    const note = (["payroll_return", "payroll_import", "authority_filing"].includes(action) ? payrollNote : $("#review-note")?.value) || "";
    current = await api(`/cases/${current.id}/actions`, "POST", {
      expected_version: current.version,
      revision: current.revision,
      request_key: key(),
      action,
      note,
      confirmed: ["submit", "review", "payroll_receive", "payroll_import", "authority_filing"].includes(action),
    });
    answers = structuredClone(current.answers);
    renderCase();
  } catch (e) {
    const err = $("#form-errors");
    if (err) {
      err.className = "error-box";
      err.textContent = e.fields
        ? Object.values(e.fields).join(" ")
        : e.message;
    }
    notify(e.message);
  } finally {
    busy = false;
  }
}
async function saveRequirements(e) {
  e.preventDefault();
  if (busy) return;
  busy = true;
  try {
    await flush();
    const items = current.requirements.map((r, i) => ({
      ...r,
      status: $("#r-status-" + i).value,
      verification: $("#r-way-" + i).value,
      evidence_ref: $("#r-ref-" + i).value,
      reason: $("#r-reason-" + i).value,
      blocks_payroll: $("#r-block-" + i).checked,
    }));
    current = await api(`/cases/${current.id}/requirements`, "PUT", {
      expected_version: current.version,
      items,
      confirmed: $("#r-confirm").checked,
    });
    requirementsDirty = false;
    renderCase();
  } catch (err) {
    notify(err.message);
  } finally {
    busy = false;
  }
}

function documentsHTML() {
  return `<h2 id="step-title" tabindex="-1">Doklady k vašemu případu</h2><p class="section-description">Přiložte jen podklady vyžádané HR. Fotografie musí být čitelná a zachycovat celý dokument.</p>
    <div class="document-list">${(current.documents || []).map((d) => `<article class="document"><div><h3>${escape(d.name)}</h3><p class="help">${escape(current.requirements.find((r) => r.id === d.requirement_id)?.label || d.requirement_id)} · ${Math.ceil(d.size / 1024)} kB<br>Soubor přijat. Obsah a platnost ověří HR.</p>${current.permissions.hr ? `<small class="document-ref">Reference: document:${escape(d.id)}</small>` : ""}</div><div class="actions"><a class="btn" href="${apiBase}/cases/${encodeURIComponent(current.id)}/documents/${encodeURIComponent(d.id)}">Stáhnout</a>${editable() ? `<button class="btn text withdraw-doc" data-id="${escape(d.id)}">Odebrat z podání</button>` : ""}</div></article>`).join("") || '<p class="muted">Zatím nejsou přiložené žádné doklady.</p>'}</div>
    ${editable() && meta.capabilities.uploads ? `<form id="upload-form" class="upload-box"><div class="field"><label for="document-purpose">K čemu doklad patří</label><select id="document-purpose" required><option value="">Vyberte požadavek HR…</option>${current.requirements.map((r) => `<option value="${escape(r.id)}">${escape(r.label)}</option>`).join("")}</select></div><div class="field"><label for="document-file">Vyberte soubor nebo fotografii</label><input id="document-file" type="file" accept="application/pdf,image/jpeg,image/png" required><p class="help">PDF, JPG nebo PNG · nejvýše 8 MB za soubor. Zdravotní dokumentaci ani diagnózy nepřikládejte.</p></div><button class="btn primary">Přiložit doklad</button><p id="upload-status" role="status" aria-live="polite"></p></form>` : editable() ? '<div class="notice">Nahrávání ještě není připojené. Způsob doložení domluvte s HR.</div>' : '<div class="notice">Doklady jsou součástí odeslané verze. Opravu nejprve otevře HR.</div>'}`;
}

function bindDocuments() {
  bind("upload-form", "submit", async (event) => {
    event.preventDefault();
    if (attachmentBusy) return;
    const file = $("#document-file").files[0];
    if (!file) return;
    if (file.size > 8 * 1024 * 1024)
      return notify("Jeden doklad může mít nejvýše 8 MB.");
    attachmentBusy = true;
    const status = $("#upload-status"),
      button = event.target.querySelector("button");
    button.disabled = true;
    status.textContent = "Nahrávám a kontroluji soubor…";
    try {
      await flush();
      const purpose = $("#document-purpose").value;
      if (
        !uploadAttempt ||
        uploadAttempt.file !== file ||
        uploadAttempt.purpose !== purpose
      )
        uploadAttempt = { file, purpose, key: key() };
      const response = await fetch(`${apiBase}/cases/${current.id}/documents`, {
        method: "POST",
        credentials: "same-origin",
        body: file,
        headers: {
          "Content-Type": file.type || "application/octet-stream",
          "X-HR-CSRF": meta.csrf,
          "X-HR-File-Name": encodeURIComponent(file.name),
          "X-HR-Requirement": purpose,
          "X-HR-Expected-Version": String(current.version),
          "X-HR-Request-Key": uploadAttempt.key,
          ...(portal ? { "X-HR-Portal": "1" } : {}),
        },
      });
      const result = await response.json();
      if (!response.ok)
        throw Error(
          typeof result.detail === "string"
            ? result.detail
            : "Doklad se nepodařilo přijmout.",
        );
      current = result;
      uploadAttempt = null;
      renderCase();
      notify("Doklad byl přijat ke kontrole HR.");
    } catch (error) {
      status.textContent = error.message;
      status.className = "error";
      button.disabled = false;
    } finally {
      attachmentBusy = false;
    }
  });
  document.querySelectorAll(".withdraw-doc").forEach(
    (button) =>
      (button.onclick = async () => {
        if (attachmentBusy || busy) return;
        attachmentBusy = true;
        try {
          current = await api(
            `/cases/${current.id}/documents/${button.dataset.id}/withdraw`,
            "POST",
            { expected_version: current.version },
          );
          renderCase();
        } catch (error) {
          notify(error.message);
        } finally {
          attachmentBusy = false;
        }
      }),
  );
}

async function openInvitations() {
  if (requirementsDirty || attachmentBusy || busy)
    return notify("Nejprve dokončete rozpracovanou změnu.");
  try {
    await flush();
    const data = await api(`/cases/${current.id}/invitations`);
    const enabled = meta.capabilities.external_invitations && editable();
    $("#invite-panel").innerHTML =
      `<section class="panel invitation-panel"><h2>Pozvánka do formuláře</h2><p>Odkaz můžete sdílet e-mailem. Přístup zaměstnanec ověří kódem doručeným na kontakt v osobní kartě.</p>
      ${!data.contacts.length ? '<div class="notice warn">V osobní kartě chybí ověřený e-mail. Doplňte ho v Přípravě HR → Ověřený kontakt.</div>' : ""}
      ${enabled ? `<form id="invitation-form"><div class="field"><label for="invite-recipient">Ověřený kontakt pro kód</label><select id="invite-recipient" required><option value="">Vyberte…</option>${data.contacts.map((c) => `<option value="${escape(c.source)}">${escape(c.address)} · ${c.source === "personal" ? "osobní" : "pracovní"}</option>`).join("")}</select></div><label class="checkbox"><input id="invite-confirm" type="checkbox" required>Ověřil/a jsem, že tento kontakt ovládá příslušný zaměstnanec.</label><button class="btn primary">Připravit odkaz</button><p class="help">Nová pozvánka zneplatní předchozí odkaz i otevřený vstup. Platí 7 dní.</p></form>` : '<div class="notice">Pozvánky vyžadují otevřený případ, veřejnou zabezpečenou adresu a doručování ověřovacích kódů.</div>'}
      <div id="invitation-result" role="status"></div><div class="invitation-list">${data.invitations
        .slice(0, 10)
        .map(
          (i) =>
            `<div class="document"><span>${escape(i.recipient)} · ${i.revoked ? "Zneplatněna" : i.expired ? "Platnost skončila" : i.locked ? "Uzamčena" : "Platí do " + new Date(i.expires_at).toLocaleDateString("cs-CZ")}</span>${!i.revoked ? `<button class="btn text revoke-invite" data-id="${escape(i.id)}">Zneplatnit</button>` : ""}</div>`,
        )
        .join("")}</div></section>`;
    $("#invite-panel").scrollIntoView({ block: "start" });
    const requestKey = key();
    bind("invitation-form", "submit", async (event) => {
      event.preventDefault();
      const button = event.target.querySelector("button");
      button.disabled = true;
      try {
        const result = await api(`/cases/${current.id}/invitations`, "POST", {
          expected_version: current.version,
          request_key: requestKey,
          recipient_source: $("#invite-recipient").value,
          confirmed: $("#invite-confirm").checked,
        });
        current.version = result.case_version;
        $("#invitation-result").innerHTML =
          `<div class="notice">${escape(result.notice)}</div>${result.url ? '<label for="invite-link">Odkaz pro zaměstnance</label><textarea id="invite-link" readonly></textarea><div class="actions"><button id="copy-invite" class="btn">Kopírovat zprávu</button><button id="share-invite" class="btn primary">Sdílet…</button></div>' : ""}`;
        if (result.url) {
          $("#invite-link").value = result.url;
          const message = `Prosím doplňte personální podklady pro ${current.context.employer}. Vstup ověříte kódem z e-mailu.\n${result.url}`;
          bind("copy-invite", "click", async () => {
            try {
              await navigator.clipboard.writeText(message);
              notify("Zpráva zkopírována. Můžete ji vložit do e-mailu.");
            } catch {
              $("#invite-link").select();
              notify("Zkopírujte označený odkaz.");
            }
          });
          bind("share-invite", "click", async () => {
            try {
              if (navigator.share)
                await navigator.share({
                  title: "Personální podklady",
                  text: message,
                });
              else $("#copy-invite").click();
            } catch (error) {
              if (error.name !== "AbortError")
                notify("Sdílení se nepodařilo. Zkopírujte zprávu.");
            }
          });
        }
      } catch (error) {
        notify(error.message);
        button.disabled = false;
      }
    });
    document.querySelectorAll(".revoke-invite").forEach(
      (button) =>
        (button.onclick = async () => {
          button.disabled = true;
          try {
            const result = await api(
              `/cases/${current.id}/invitations/${button.dataset.id}/revoke`,
              "POST",
              { expected_version: current.version },
            );
            current.version = result.case_version;
            await openInvitations();
          } catch (error) {
            notify(error.message);
            button.disabled = false;
          }
        }),
    );
  } catch (error) {
    notify(error.message);
  }
}

function entryScreen(message = "") {
  root.innerHTML = `<section class="panel entry-panel"><div class="eyebrow">Váš osobní vstup</div><h1>Vítejte.</h1><p>Než otevřeme podklady, ověříme váš přístup krátkým kódem z e-mailu. Potom můžete vyplňovat vlastním tempem a vracet se k uloženým údajům.</p>${message ? `<p role="alert">${escape(message)}</p>` : ""}
    ${/^[A-Za-z0-9_-]{43}$/.test(invitationTicket) ? '<button id="request-code" class="btn primary">Poslat ověřovací kód</button><div id="entry-status" role="status"></div><form id="verify-form" hidden><div class="field"><label for="entry-code">Osmimístný kód z e-mailu</label><input id="entry-code" type="text" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{8}" minlength="8" maxlength="8" required></div><button class="btn primary">Otevřít moje podklady →</button><p id="verify-error" role="alert"></p></form>' : '<div class="notice">Otevřete původní odkaz z e-mailu. Pokud už neplatí, HR vám připraví nový.</div>'}</section>`;
  bind("request-code", "click", async () => {
    const button = $("#request-code");
    button.disabled = true;
    try {
      const result = await api("/code", "POST", { token: invitationTicket });
      $("#entry-status").textContent =
        `Kód byl předán k doručení na ${result.recipient}. Platí 10 minut.`;
      $("#verify-form").hidden = false;
      $("#entry-code").focus();
      button.textContent = "Poslat nový kód";
      setTimeout(() => {
        button.disabled = false;
      }, 60000);
    } catch (error) {
      $("#entry-status").textContent = error.message;
      button.disabled = false;
    }
  });
  bind("verify-form", "submit", async (event) => {
    event.preventDefault();
    const button = event.target.querySelector("button");
    button.disabled = true;
    try {
      await api("/verify", "POST", {
        token: invitationTicket,
        code: $("#entry-code").value,
      });
      await start();
    } catch (error) {
      $("#verify-error").textContent = error.message;
      button.disabled = false;
    }
  });
}

async function start() {
  try {
    meta = await api("/meta");
    const id = portal
      ? meta.case_id
      : new URLSearchParams(location.search).get("case");
    if (id) await openCase(id);
    else await loadQueue();
    if (portal) {
      $("#logout").hidden = false;
      $("#logout").onclick = async () => {
        try {
          if (attachmentBusy) return;
          await flush();
          await api("/logout", "POST", {});
          current = null;
          answers = {};
          meta = null;
          dirty = false;
          invitationTicket = "";
          $("#logout").hidden = true;
          entryScreen(
            "Vstup byl ukončen. Uložené podklady zůstávají v bezpečí.",
          );
        } catch (error) {
          notify(error.message);
        }
      };
    }
  } catch (error) {
    if (portal) entryScreen(error.status === 401 ? "" : error.message);
    else
      root.innerHTML = `<section class="panel"><h1>Podklady nyní nejsou dostupné.</h1><p>${escape(error.message)}</p><a class="btn" href="/auth/login">Přihlásit se do Nexusu</a></section>`;
  }
}
await start();
