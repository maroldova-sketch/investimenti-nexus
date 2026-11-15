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
  uploadAttempt = null;
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
function active(field) {
  return Object.entries(field.when || {}).every(([k, v]) =>
    v.includes(answers[k]),
  );
}
function hasChildren() {
  return (
    answers.children_claim === "yes" &&
    answers.declaration === "yes" &&
    answers.tax_residency === "CZ"
  );
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
      saveStatus("Ukládám…");
      try {
        const saved = await api(`/cases/${current.id}/draft`, "PUT", {
          expected_version: current.version,
          answers: payload,
        });
        current = saved;
        if (generation === localGeneration) {
          answers = saved.answers;
          dirty = false;
        }
        saveFailed = false;
        saveStatus(dirty ? "Čekají další změny…" : "Uloženo do Nexusu");
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
      (c.status === "reviewed" && c.permissions.payroll),
  ).length;
  root.innerHTML = `<div class="intro"><div><div class="eyebrow">Personální agenda</div><h1>Každý krok má své místo.</h1><p class="muted">Podklady, které čekají na doplnění, kontrolu nebo převzetí. Vždy u konkrétní firmy a pracovního vztahu.</p></div>${meta.can_create ? '<button id="new-case" class="btn primary">＋ Nový případ</button>' : ""}</div><div class="stats"><div class="stat"><b>${rows.filter((c) => c.status !== "payroll_received").length}</b><span>Otevřené případy</span></div><div class="stat"><b>${pending}</b><span>Čeká na zásah</span></div><div class="stat"><b>${rows.filter((c) => c.status === "payroll_received").length}</b><span>Převzaté podklady</span></div></div><section class="panel"><div class="row"><h2>Vaše případy</h2><span class="eyebrow">Jen dostupné firmy</span></div>${rows.length ? rows.map((c) => `<article class="case-card"><div><h3>${escape(c.context.name)}</h3><p>${escape(c.context.employer)} · ${escape(c.context.position)}<br>${escape(c.context.employment_type)} · ${c.kind === "change" ? "Změna údajů" : "Doplnění existující evidence"}</p>${pill(c.status)}</div><button class="btn open-case" data-id="${escape(c.id)}">Otevřít →</button></article>`).join("") : '<div class="empty">Zatím tu není žádný případ.<br>HR vybere existující pracovní vztah a připraví podklady.</div>'}</section><div class="notice">${escape(meta.notice)} Převzetí podkladů samo nepotvrzuje způsobilost k práci ani zpracování mzdy.</div>`;
  bind("new-case", "click", newCase);
  document
    .querySelectorAll(".open-case")
    .forEach(
      (b) =>
        (b.onclick = () =>
          openCase(b.dataset.id).catch((e) => notify(e.message))),
    );
  history.replaceState(null, "", "/people/hr");
}
async function newCase() {
  try {
    const rows = await api("/employments");
    root.innerHTML = `<button id="back" class="btn text">← Vaše případy</button><div class="intro"><div><div class="eyebrow">Příprava HR</div><h1>Nový personální případ</h1><p class="muted">Vyberte existující pracovní vztah. Tím se určí člověk, právní zaměstnavatel a pozice.</p></div></div><form id="create-form" class="panel"><div class="field"><label for="employment">Pracovní vztah</label><select id="employment" required><option value="">Vyberte…</option>${rows.map((r) => `<option value="${escape(r.employment_id)}">${escape(r.name)} · ${escape(r.employer)} · ${escape(r.employment_type)} · ${escape(r.position)}</option>`).join("")}</select></div><div class="fields"><div class="field"><label for="kind">Typ případu</label><select id="kind"><option value="complete_existing">Doplnění existující evidence</option><option value="change">Změna údajů</option></select></div></div><div class="notice">Nevzniká nový zaměstnanec ani nová smlouva. Pokud člověk pracuje pro více firem, každý vztah má samostatný případ.</div><button class="btn primary" ${rows.length ? "" : "disabled"}>Připravit formulář →</button><div id="create-error" role="alert"></div></form>`;
    bind("back", "click", () => loadQueue().catch((e) => notify(e.message)));
    const requestKey = key();
    bind("create-form", "submit", async (e) => {
      e.preventDefault();
      const btn = e.target.querySelector("button");
      btn.disabled = true;
      try {
        const c = await api("/cases", "POST", {
          employment_id: $("#employment").value,
          kind: $("#kind").value,
          request_key: requestKey,
        });
        await openCase(c.id);
      } catch (err) {
        $("#create-error").textContent = err.message;
        btn.disabled = false;
      }
    });
  } catch (e) {
    notify(e.message);
  }
}
async function openCase(id) {
  current = await api("/cases/" + id);
  answers = structuredClone(current.answers);
  dirty = false;
  saveFailed = false;
  step = ["draft", "returned"].includes(current.status)
    ? 0
    : meta.sections.length + 1;
  history.replaceState(
    null,
    "",
    portal ? "/hr/entry" : "/people/hr?case=" + encodeURIComponent(id),
  );
  renderCase();
}
function renderField(f) {
  const val = answers[f.key] ?? "";
  const id = "f-" + f.key;
  const common = `id="${id}" data-field="${escape(f.key)}" ${editable() ? "" : "disabled"}`;
  let input;
  if (f.type === "select")
    input = `<select ${common}><option value="">Vyberte…</option>${f.options.map(([v, l]) => `<option value="${escape(v)}" ${val === v ? "selected" : ""}>${escape(l)}</option>`).join("")}</select>`;
  else if (f.type === "textarea")
    input = `<textarea ${common} maxlength="2000">${escape(val)}</textarea>`;
  else
    input = `<input ${common} type="${f.type}" value="${escape(val)}" maxlength="300" autocomplete="off">`;
  return `<div class="field ${f.type === "textarea" ? "full" : ""}" data-wrapper="${escape(f.key)}" ${active(f) ? "" : "hidden"}><label for="${id}">${escape(f.label)}${f.required ? " *" : ""}</label>${input}${f.help ? `<p class="help">${escape(f.help)}</p>` : ""}</div>`;
}
function childField(i, k, label, type = "text", options = null) {
  const c = answers.children[i],
    id = `child-${i}-${k}`,
    attrs = `id="${id}" data-child="${i}" data-key="${k}" ${editable() ? "" : "disabled"}`;
  return `<div class="field"><label for="${id}">${label}</label>${options ? `<select ${attrs}><option value="">Vyberte…</option>${options.map(([v, l]) => `<option value="${v}" ${c[k] === v ? "selected" : ""}>${l}</option>`).join("")}</select>` : `<input ${attrs} type="${type}" value="${escape(c[k])}" maxlength="200">`}</div>`;
}
function childrenHTML() {
  const yes = [
    ["yes", "Ano"],
    ["no", "Ne"],
    ["review", "Ověřit s účetní"],
  ];
  return (answers.children || [])
    .map(
      (c, i) =>
        `<article class="child"><div class="row"><h3>Dítě ${i + 1}</h3>${editable() ? `<button type="button" class="btn text remove-child" data-index="${i}">Odebrat</button>` : ""}</div><div class="fields">${childField(i, "name", "Jméno a příjmení")}${childField(i, "birth_date", "Datum narození", "date")}${childField(i, "relationship", "Vztah k dítěti")}${childField(i, "household", "Společná domácnost", "text", yes)}${childField(
          i,
          "order",
          "Pořadí pro zamýšlené uplatnění",
          "text",
          [
            ["1", "První dítě"],
            ["2", "Druhé dítě"],
            ["3", "Třetí a další"],
            ["not_claimed", "Neuplatňuji"],
            ["review", "Upřesnit s účetní"],
          ],
        )}${childField(i, "ztpp", "ZTP/P", "text", yes)}${childField(i, "study", "Doklad o studiu relevantní", "text", yes)}<fieldset class="field full"><legend>Měsíce zamýšleného uplatnění</legend><div class="months">${Array.from({ length: 12 }, (_, n) => `<label class="month"><input type="checkbox" data-month-child="${i}" value="${n + 1}" ${(c.months || []).includes(n + 1) ? "checked" : ""} ${editable() ? "" : "disabled"}>${n + 1}.</label>`).join("")}</div></fieldset></div></article>`,
    )
    .join("");
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
  const can =
    current.permissions.hr &&
    !["reviewed", "payroll_received"].includes(current.status);
  return `<details ${current.status === "submitted" ? "open" : ""}><summary>Požadavky a doklady · nastavení HR</summary><p class="help">Každý požadavek má samostatný stav. Odkaz je označení dokumentu v chráněném úložišti, nikoli důkaz jeho ověření.</p><form id="requirements-form">${current.requirements.map((r, i) => `<div class="requirement"><h3>${escape(r.label)}</h3><div class="fields"><div class="field"><label for="r-status-${i}">Stav</label><select id="r-status-${i}" ${can ? "" : "disabled"}>${opts.map(([v, l]) => `<option value="${v}" ${r.status === v ? "selected" : ""}>${l}</option>`).join("")}</select></div><div class="field"><label for="r-ref-${i}">Reference důkazu</label><input id="r-ref-${i}" value="${escape(r.evidence_ref)}" maxlength="300" ${can ? "" : "disabled"}></div><div class="field full"><label for="r-reason-${i}">Důvod výjimky / odkladu</label><input id="r-reason-${i}" value="${escape(r.reason)}" maxlength="500" ${can ? "" : "disabled"}></div></div><label class="checkbox" style="margin-top:14px"><input id="r-block-${i}" type="checkbox" ${r.blocks_payroll ? "checked" : ""} ${can ? "" : "disabled"}>Nutné před předáním mzdové roli</label></div>`).join("")}${can ? '<label class="checkbox"><input id="r-confirm" type="checkbox" required>Potvrzuji, že rozsah požadavků odpovídá pracovnímu vztahu a dohodnutému mzdovému minimu.</label><button class="btn" style="margin-top:18px">Uložit požadavky</button>' : ""}</form></details>`;
}
function summaryHTML() {
  return `<h2>Kontrola a předání</h2><p class="section-description">Podání se uloží jako samostatná verze. HR může vrátit konkrétní nedostatky k doplnění.</p>${current.issues.length ? `<div class="notice warn"><strong>K individuálnímu ověření:</strong><ul>${current.issues.map((x) => `<li>${escape(x)}</li>`).join("")}</ul></div>` : ""}<dl class="summary">${meta.sections
    .flatMap((s) => s.fields)
    .filter((f) => active(f) && answers[f.key])
    .map(
      (f) =>
        `<dt>${escape(f.label)}</dt><dd>${escape(f.options?.find((o) => o[0] === answers[f.key])?.[1] || answers[f.key])}</dd>`,
    )
    .join(
      "",
    )}${hasChildren() ? `<dt>Děti k ověření</dt><dd>${(answers.children || []).map((c) => escape(c.name) + " · " + escape(c.birth_date)).join("<br>")}</dd>` : ""}</dl>${requirementsHTML()}<div class="notice">Tento krok potvrzuje předání podkladů. Nenahrazuje podpis smlouvy ani Prohlášení poplatníka, školení, prohlídku nebo zpracování mzdy.</div><div id="form-errors" role="alert"></div>${editable() ? '<button id="submit-case" class="btn primary">Odeslat ke kontrole HR →</button>' : ""}${current.permissions.hr && ["submitted", "reviewed"].includes(current.status) ? '<div class="field" style="margin-top:22px"><label for="review-note">Poznámka / co je potřeba doplnit</label><textarea id="review-note" maxlength="1200"></textarea></div><div class="actions"><button id="return-case" class="btn danger">Vrátit k doplnění</button>' + (current.status === "submitted" ? '<button id="review-case" class="btn primary">Potvrdit kontrolu HR</button>' : "") + "</div>" : ""}${current.permissions.payroll && current.status === "reviewed" ? '<div class="actions"><button id="receive-case" class="btn primary">Převzít tuto verzi podkladů</button></div>' : ""}<details><summary>Historie případu</summary><ol class="history">${current.history.map((h) => `<li><b>${escape(actionLabels[h.action] || h.action)} · verze ${h.revision}</b><br>${escape(new Date(h.at + "Z").toLocaleString("cs-CZ"))}${h.note ? "<br>" + escape(h.note) : ""}</li>`).join("") || "<li>Zatím bez předání.</li>"}</ol></details>`;
}
function renderCase() {
  const sections = [
      ...meta.sections,
      { title: "Doklady" },
      { title: "Kontrola a předání" },
    ],
    s = sections[step];
  root.innerHTML = `<div class="row">${portal ? "" : '<button id="queue" class="btn text back-case">← Vaše případy</button>'}${current.permissions.hr ? '<button id="invitations" class="btn">Pozvat zaměstnance</button>' : ""}</div><div id="invite-panel"></div><div class="intro"><div><div class="topline"><span class="eyebrow">${escape(current.context.employer)}</span>${pill(current.status)}</div><h1>${escape(current.context.name)}</h1><p class="muted">${escape(current.context.position)} · ${escape(current.context.employment_type)}<br>${current.kind === "change" ? "Změna údajů" : "Doplnění existující personální evidence"}</p></div><span class="eyebrow">${step + 1} / ${sections.length}</span></div>${current.status === "returned" ? `<div class="notice warn"><b>Prosíme o doplnění:</b> ${escape([...current.history].reverse().find((h) => h.action === "return")?.note || "Podívejte se do historie případu.")}</div>` : ""}<div class="workspace"><aside class="steps">${sections.map((x, i) => `<button class="step ${step === i ? "active" : ""}" data-step="${i}" ${step === i ? 'aria-current="step"' : ""}><span>${i + 1}</span>${escape(x.title)}</button>`).join("")}<div class="context"><strong>Právní zaměstnavatel</strong>${escape(current.context.employer)}<br>IČO: ${escape(current.context.ico || "K ověření")}<br>Vztah od: ${escape(current.context.start || "K ověření")}</div></aside><section class="panel" id="form-panel">${step < meta.sections.length ? `<h2 tabindex="-1" id="step-title">${escape(s.title)}</h2><p class="section-description">${escape(s.description)}</p><div class="fields">${s.fields.map(renderField).join("")}</div>${s.id === "tax" ? `<div id="children-section" ${hasChildren() ? "" : "hidden"}><div id="children-list">${childrenHTML()}</div>${editable() ? '<button id="add-child" class="btn" style="margin-top:20px">＋ Přidat dítě</button>' : ""}</div>` : ""}` : step === meta.sections.length ? documentsHTML() : summaryHTML()}<div class="actions">${step > 0 ? '<button id="prev" class="btn">← Zpět</button>' : "<span></span>"}<span class="save-status" id="save-status" role="status" aria-live="polite">${dirty ? "Změny čekají na uložení…" : editable() ? "Uloženo do Nexusu" : "Odeslaná verze " + current.revision}</span>${step < sections.length - 1 ? '<button id="next" class="btn primary">Pokračovat →</button>' : ""}</div></section></div>`;
  bind("queue", "click", () => loadQueue().catch((e) => notify(e.message)));
  document
    .querySelectorAll("[data-step]")
    .forEach((b) => (b.onclick = () => goStep(+b.dataset.step)));
  bind("prev", "click", () => goStep(step - 1));
  bind("next", "click", () => goStep(step + 1));
  document.querySelectorAll("[data-field]").forEach((el) =>
    el.addEventListener("input", () => {
      answers[el.dataset.field] = el.value;
      document.querySelectorAll("[data-wrapper]").forEach((w) => {
        const f = meta.sections
          .flatMap((s) => s.fields)
          .find((f) => f.key === w.dataset.wrapper);
        w.hidden = !active(f);
      });
      if ($("#children-section"))
        $("#children-section").hidden = !hasChildren();
      markDirty();
    }),
  );
  bindChildren();
  bind("add-child", "click", () => {
    answers.children ??= [];
    answers.children.push({
      name: "",
      birth_date: "",
      relationship: "",
      household: "",
      order: "",
      months: [],
      ztpp: "",
      study: "",
    });
    markDirty();
    renderCase();
  });
  bind("submit-case", "click", () => perform("submit"));
  bind("return-case", "click", () => perform("return"));
  bind("review-case", "click", () => perform("review"));
  bind("receive-case", "click", () => perform("payroll_receive"));
  bind("requirements-form", "submit", saveRequirements);
  bind("requirements-form", "input", () => {
    requirementsDirty = true;
  });
  bind("invitations", "click", openInvitations);
  bindDocuments();
  $(".step.active")?.scrollIntoView({ block: "nearest", inline: "center" });
}
function bindChildren() {
  document.querySelectorAll("[data-child]").forEach((el) =>
    el.addEventListener("input", () => {
      answers.children[+el.dataset.child][el.dataset.key] = el.value;
      markDirty();
    }),
  );
  document.querySelectorAll("[data-month-child]").forEach((el) =>
    el.addEventListener("change", () => {
      const i = +el.dataset.monthChild;
      answers.children[i].months = [
        ...document.querySelectorAll(`[data-month-child="${i}"]:checked`),
      ].map((x) => +x.value);
      markDirty();
    }),
  );
  document.querySelectorAll(".remove-child").forEach(
    (b) =>
      (b.onclick = () => {
        answers.children.splice(+b.dataset.index, 1);
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
  busy = true;
  try {
    await flush();
    if (dirty) throw Error("Nejprve je potřeba uložit všechny změny.");
    const note = $("#review-note")?.value || "";
    current = await api(`/cases/${current.id}/actions`, "POST", {
      expected_version: current.version,
      revision: current.revision,
      request_key: key(),
      action,
      note,
      confirmed: ["review", "payroll_receive"].includes(action),
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
      `<section class="panel invitation-panel"><h2>Pozvánka do formuláře</h2><p>Odkaz můžete sdílet e-mailem nebo WhatsAppem. Přístup zaměstnanec ověří kódem doručeným na kontakt v osobní kartě.</p>
      ${enabled ? `<form id="invitation-form"><div class="field"><label for="invite-recipient">Ověřený kontakt pro kód</label><select id="invite-recipient" required><option value="">Vyberte…</option>${data.contacts.map((c) => `<option value="${c.source}">${escape(c.address)} · ${c.source === "personal" ? "osobní" : "pracovní"}</option>`).join("")}</select></div><label class="checkbox"><input id="invite-confirm" type="checkbox" required>Ověřil/a jsem, že tento kontakt ovládá příslušný zaměstnanec.</label><button class="btn primary">Připravit odkaz</button><p class="help">Nová pozvánka zneplatní předchozí odkaz i otevřený vstup. Platí 7 dní.</p></form>` : '<div class="notice">Pozvánky vyžadují otevřený případ, veřejnou zabezpečenou adresu a doručování ověřovacích kódů.</div>'}
      <div id="invitation-result" role="status"></div><div class="invitation-list">${data.invitations
        .slice(0, 10)
        .map(
          (i) =>
            `<div class="document"><span>${escape(i.recipient)} · ${i.revoked ? "Zneplatněna" : i.expired ? "Platnost skončila" : i.locked ? "Uzamčena" : "Platí do " + new Date(i.expires_at).toLocaleDateString("cs-CZ")}</span>${!i.revoked ? `<button class="btn text revoke-invite" data-id="${escape(i.id)}">Zneplatnit</button>` : ""}</div>`,
        )
        .join("")}</div></section>`;
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
              notify(
                "Zpráva zkopírována. Můžete ji vložit do e-mailu nebo WhatsAppu.",
              );
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
    ${/^[A-Za-z0-9_-]{43}$/.test(invitationTicket) ? '<button id="request-code" class="btn primary">Poslat ověřovací kód</button><div id="entry-status" role="status"></div><form id="verify-form" hidden><div class="field"><label for="entry-code">Osmimístný kód z e-mailu</label><input id="entry-code" type="text" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{8}" minlength="8" maxlength="8" required></div><button class="btn primary">Otevřít moje podklady →</button><p id="verify-error" role="alert"></p></form>' : '<div class="notice">Otevřete původní odkaz z e-mailu nebo WhatsAppu. Pokud už neplatí, HR vám připraví nový.</div>'}</section>`;
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
