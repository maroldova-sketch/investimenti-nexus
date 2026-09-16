/* === TAB PROGRAM: čte dashboard/data/program.json, nic natvrdo === */
(function () {
  const MESICE = ['Leden','Únor','Březen','Duben','Květen','Červen','Červenec','Srpen','Září','Říjen','Listopad','Prosinec'];
  const KC = n => (Math.round(n) || 0).toLocaleString('cs-CZ') + ' Kč';
  const PCT = x => (x * 100).toFixed(1).replace('.', ',') + ' %';
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const $ = id => document.getElementById(id);
  let P = null;

  function parterFull(cenik) { return cenik.sektory.reduce((a, s) => a + s.cena * s.mist, 0); }
  function parterSeats(cenik) { return cenik.sektory.reduce((a, s) => a + s.mist, 0); }

  /* --- čistá kalkulace, bez DOM --- */
  function kalkulace(P, t, inp) {
    const c = P.cenik, e = P.ekonomika, v = P.venue;
    const dphZ = c.dph_zajezd != null ? c.dph_zajezd : 0.21;
    const dphV = c.dph_vstupne != null ? c.dph_vstupne : 0.12;
    const kmSazba = e.doprava_kc_km_vozidlo != null ? e.doprava_kc_km_vozidlo : 16;
    const cekSazba = e.cekacka_kc_h_vozidlo != null ? e.cekacka_kc_h_vozidlo : 300;
    const prir = inp.prirazka && c.prirazky[inp.prirazka] ? c.prirazky[inp.prirazka] : 0;
    const seats = parterSeats(c), lozeOs = v.loze.kapacita_osob || 0;
    const parterGrossFull = parterFull(c) * (1 + prir);
    const lozeGrossFull = lozeOs * c.loze_cena_os;

    const zajezd = t.cena, zajezdDph = t.cena * dphZ;
    const doprava = inp.km * 2 * kmSazba * t.vozidel + inp.cekacka * cekSazba * t.vozidel;
    const provoz = inp.provoz;
    const parterGross = parterGrossFull * inp.obs;
    const lozeGross = lozeGrossFull * inp.obsLoze;
    const hruba = parterGross + lozeGross;
    const honorar = parterGross * t.honorar_pct / 100;          // základ: hrubá tržba ze vstupného (parter)
    const dph = hruba - hruba / (1 + dphV);
    const naklady = zajezd + zajezdDph + doprava + provoz;
    const vysledek = hruba - dph - honorar - naklady;
    // bod zvratu při společné obsazenosti o parteru i lóží
    const netPerUnit = (parterGrossFull + lozeGrossFull) / (1 + dphV) - parterGrossFull * t.honorar_pct / 100;
    const beObs = netPerUnit > 0 ? naklady / netPerUnit : Infinity;
    const beHostu = beObs * (seats + lozeOs);
    return { zajezd, zajezdDph, doprava, provoz, parterGross, lozeGross, hruba, honorar, dph, naklady, vysledek,
             beObs, beHostu, hostu: Math.round(seats * inp.obs + lozeOs * inp.obsLoze), seats, lozeOs, prir };
  }
  /* odvozený provoz z CFO break-even: net(BE) − honorar_fix − doprava_model */
  function provozOdvozeny(P) {
    const c = P.cenik, e = P.ekonomika, dphV = c.dph_vstupne != null ? c.dph_vstupne : 0.12;
    const gross = parterFull(c) * e.break_even_obsazenost;
    return Math.max(0, Math.round(gross / (1 + dphV) - e.honorar_fix_model - e.doprava_model));
  }

  /* --- render: kalendář --- */
  function renderKalendar() {
    const fT = $('prog-f-typ').value, fS = $('prog-f-stav').value, fTent = $('prog-f-tent').checked;
    const items = P.kalendar.filter(x => (!fT || x.typ === fT) && (!fS || x.stav === fS) && (!fTent || x.tentpole));
    const byM = {}; items.forEach(x => (byM[x.mesic] = byM[x.mesic] || []).push(x));
    const kat = Object.fromEntries(P.katalog.map(k => [k.id, k]));
    let html = '';
    for (let m = 1; m <= 12; m++) {
      const list = (byM[m] || []).slice().sort((a, b) => (a.datum || '9') < (b.datum || '9') ? -1 : 1);
      html += '<div class="col-md-4 col-lg-2"><div class="card month-card h-100"><div class="card-body p-2"><strong>' + MESICE[m - 1] + '</strong> <span class="small text-muted">(' + list.length + ')</span>';
      list.forEach(x => {
        const d = x.datum ? '<span class="prog-date">' + x.datum.slice(8, 10).replace(/^0/, '') + '.' + x.datum.slice(5, 7).replace(/^0/, '') + '.</span> ' : '';
        const k = x.katalog_id && kat[x.katalog_id] ? ' · ' + esc(kat[x.katalog_id].soubor) : '';
        html += '<span class="prog-ev ' + esc(x.typ) + (x.tentpole ? ' tentpole' : '') + '" title="' + esc(x.poznamka) + ' [' + esc(x.rezim) + ', ' + esc(x.stav) + ']">' + d + (x.tentpole ? '★ ' : '') + esc(x.nazev) + k + '</span>';
      });
      html += '</div></div></div>';
    }
    $('prog-kalendar').innerHTML = html;
    $('prog-f-count').textContent = items.length + ' / ' + P.kalendar.length + ' akcí';
  }

  /* --- render: ceník --- */
  function renderCenik() {
    const c = P.cenik, v = P.venue;
    const seats = parterSeats(c), full = parterFull(c);
    const lozeOs = v.loze.kapacita_osob || 0, lozeFull = lozeOs * c.loze_cena_os;
    let rows = c.sektory.map(s => '<tr><td>' + esc(s.nazev) + '</td><td class="text-end">' + KC(s.cena) + '</td><td class="text-end">' + s.mist + '</td><td class="text-end">' + KC(s.cena * s.mist) + '</td></tr>').join('');
    rows += '<tr class="table-active"><td><strong>Parter celkem</strong></td><td class="text-end">⌀ ' + KC(full / seats) + '</td><td class="text-end"><strong>' + seats + '</strong></td><td class="text-end"><strong>' + KC(full) + '</strong></td></tr>';
    rows += '<tr><td>Lóže (doplněk nad parter) <span class="small text-muted">' + v.loze.ctyrmistne_ks + '×4 + ' + v.loze.dvoumistne_ks + '×2</span></td><td class="text-end">' + KC(c.loze_cena_os) + ' / os</td><td class="text-end">' + lozeOs + '</td><td class="text-end">' + KC(lozeFull) + '</td></tr>';
    rows += '<tr class="table-active"><td><strong>Celkem vč. lóží</strong></td><td class="text-end">⌀ ' + KC((full + lozeFull) / (seats + lozeOs)) + '</td><td class="text-end"><strong>' + (seats + lozeOs) + '</strong></td><td class="text-end"><strong>' + KC(full + lozeFull) + '</strong></td></tr>';
    $('prog-cenik').querySelector('tbody').innerHTML = rows;
    $('prog-cenik-pozn').innerHTML = 'Lóže: ' + esc(c.loze_obsah) + ' · přirážky: prémiový večer +' + PCT(c.prirazky.premiovy_vecer) + ', koncert +' + PCT(c.prirazky.koncert) + ', gala lóže ' + KC(c.prirazky.gala_loze) + '/os · parkovné ' + KC(c.parkovne) + ' · <em>' + esc(v.loze.poznamka) + '</em>';
    const b = c.benchmark_divice;
    $('prog-divice').innerHTML = '<div class="h3 navy-text mb-0">' + b.mist + ' míst · ⌀ ' + KC(b.prumer_vstupenka) + '</div><div class="small text-muted">vyprodáno gross ' + KC(b.vyprodano_gross) + '</div><div class="small mt-1">Cítoliby parter ⌀ ' + KC(full / seats) + ' · vyprodáno ' + KC(full) + ' (' + (full >= b.vyprodano_gross ? '+' : '') + KC(full - b.vyprodano_gross) + ')</div>';
    $('prog-venue').innerHTML = 'Nádvoří ' + v.nadvori.rozmery_m.join('×') + ' m · parter ' + v.nadvori.parter_mist + ' míst<br>Lóže ' + lozeOs + ' os (arkády v patře)<br>Zahrada koncert ' + v.zahrada.kapacita_koncert + ' (strop ' + v.zahrada.strop + ')<br>Parkování ' + v.parkovani_mist + ' míst';
  }

  /* --- render: kalkulace --- */
  function renderKalk() {
    const t = P.katalog.find(k => k.id === $('prog-k-titul').value);
    if (!t) return;
    const inp = { km: +$('prog-k-km').value || 0, cekacka: +$('prog-k-cek').value || 0, obs: (+$('prog-k-obs').value || 0) / 100,
                  obsLoze: (+$('prog-k-obsl').value || 0) / 100, prirazka: $('prog-k-prir').value, provoz: +$('prog-k-prov').value || 0 };
    const r = kalkulace(P, t, inp), e = P.ekonomika, c = P.cenik;
    const row = (n, v, p, cls) => '<tr' + (cls ? ' class="' + cls + '"' : '') + '><td>' + n + '</td><td class="text-end">' + KC(v) + '</td><td class="small text-muted">' + p + '</td></tr>';
    let h = '';
    h += row('Cena zájezdu (bez DPH)', -r.zajezd, esc(t.soubor));
    h += row('DPH ze zájezdu ' + PCT(c.dph_zajezd != null ? c.dph_zajezd : 0.21), -r.zajezdDph, '');
    h += row('Doprava', -r.doprava, inp.km + ' km × 2 × ' + t.vozidel + ' voz. + čekačka ' + inp.cekacka + ' h');
    h += row('Provoz večera', -r.provoz, 'zadaný odhad');
    h += row('<strong>Náklady celkem</strong>', -r.naklady, '', 'table-active');
    h += row('Hrubá tržba parter', r.parterGross, Math.round(r.seats * inp.obs) + ' hostů' + (r.prir ? ' · přirážka +' + PCT(r.prir) : ''));
    h += row('Hrubá tržba lóže', r.lozeGross, Math.round(r.lozeOs * inp.obsLoze) + ' os × ' + KC(c.loze_cena_os));
    h += row('<strong>Hrubá tržba celkem</strong>', r.hruba, r.hostu + ' hostů', 'table-active');
    h += row('DPH ze vstupného ' + PCT(c.dph_vstupne != null ? c.dph_vstupne : 0.12), -r.dph, '');
    h += row('Autorský honorář ' + t.honorar_pct + ' %', -r.honorar, esc(t.honorar_kdo) + ' · základ: hrubá tržba parteru (potvrdit)');
    $('prog-kalk').querySelector('tbody').innerHTML = h;
    $('prog-r-vysl').innerHTML = '<span class="' + (r.vysledek >= 0 ? 'prog-pos' : 'prog-neg') + '">' + KC(r.vysledek) + '</span>';
    $('prog-r-be').textContent = isFinite(r.beObs) ? PCT(r.beObs) : 'nedosažitelný';
    $('prog-r-be2').textContent = isFinite(r.beObs) ? Math.round(r.beHostu) + ' hostů z ' + (r.seats + r.lozeOs) : 'honorář vyšší než čistá tržba';
    const diff = r.beObs - e.break_even_obsazenost;
    $('prog-r-cfo').innerHTML = '<span class="' + (diff <= 0 ? 'prog-pos' : 'prog-neg') + '">' + (diff <= 0 ? '−' : '+') + PCT(Math.abs(diff)) + '</span>';
    $('prog-r-cfo2').textContent = 'CFO model: ' + PCT(e.break_even_obsazenost) + ' / ' + e.break_even_hostu + ' hostů';
    $('prog-k-titul-info').innerHTML = '<strong>' + esc(t.titul) + '</strong>' + (t.autor ? ' · ' + esc(t.autor) : '') + (t.rezie ? ' · režie ' + esc(t.rezie) : '') + '<br>' + esc(t.obsazeni.join(', ')) + '<br>' + esc(t.anotace) + ' <em>' + esc(t.poznamka) + '</em> · stav: ' + esc(t.stav);
  }

  function init(data) {
    P = data;
    $('prog-meta').textContent = 'verze ' + data.verze + ' · aktualizováno ' + (data.aktualizovano || '').slice(0, 16).replace('T', ' ') + ' · katalog ' + data.katalog.length + ' · kalendář ' + data.kalendar.length + ' · zdroj: ' + data.zdroj_pravdy;
    const typy = [...new Set(data.kalendar.map(x => x.typ))].sort(), stavy = [...new Set(data.kalendar.map(x => x.stav))].sort();
    typy.forEach(t => $('prog-f-typ').insertAdjacentHTML('beforeend', '<option value="' + esc(t) + '">' + esc(t) + '</option>'));
    stavy.forEach(s => $('prog-f-stav').insertAdjacentHTML('beforeend', '<option value="' + esc(s) + '">' + esc(s) + '</option>'));
    data.katalog.forEach(k => $('prog-k-titul').insertAdjacentHTML('beforeend', '<option value="' + esc(k.id) + '">' + esc(k.titul) + ' · ' + KC(k.cena) + ' · ' + k.honorar_pct + ' %</option>'));
    $('prog-k-prov').value = provozOdvozeny(data);
    $('prog-k-hint').textContent = 'Provoz předvyplněn odvozením z CFO bodu zvratu (' + PCT(data.ekonomika.break_even_obsazenost) + ', fix honorář ' + KC(data.ekonomika.honorar_fix_model) + ', doprava ' + KC(data.ekonomika.doprava_model) + '). Km z Prahy doplní Honza.';
    ['prog-f-typ', 'prog-f-stav', 'prog-f-tent'].forEach(id => $(id).addEventListener('change', renderKalendar));
    ['prog-k-titul', 'prog-k-km', 'prog-k-cek', 'prog-k-obs', 'prog-k-obsl', 'prog-k-prir', 'prog-k-prov'].forEach(id => { $(id).addEventListener('input', renderKalk); $(id).addEventListener('change', renderKalk); });
    renderKalendar(); renderCenik(); renderKalk();
    $('prog-status').classList.add('d-none'); $('prog-body').classList.remove('d-none');
  }

  async function load() {
    const urls = ['dashboard/data/program.json', '/dashboard/data/program.json', '/api/program'];
    let lastErr = null;
    for (const u of urls) {
      try {
        const r = await fetch(u, { cache: 'no-store' });
        if (!r.ok) { lastErr = u + ' → HTTP ' + r.status; continue; }
        const d = await r.json();
        if (!d || !Array.isArray(d.kalendar) || !Array.isArray(d.katalog) || !d.cenik) { lastErr = u + ' → neplatná struktura'; continue; }
        $('prog-zdroj').textContent = u; init(d); return;
      } catch (err) { lastErr = u + ' → ' + (err && err.message ? err.message : err); }
    }
    const st = $('prog-status'); st.className = 'alert alert-danger';
    st.innerHTML = '<strong>program.json se nepodařilo načíst.</strong> Tab PROGRAM proto nemá data. Poslední chyba: ' + esc(lastErr) + '<br><span class="small">Ověř, že backend servíruje <code>dashboard/data/program.json</code> (routa musí být před catch-all <code>/{path:path}</code>).</span>';
  }
  const tab = document.querySelector('.castello-tab[data-tab="program"]');
  if (tab) tab.addEventListener('click', () => { if (!P) load(); }, { once: false });
  load().catch(err => { const st = $('prog-status'); st.className = 'alert alert-danger'; st.textContent = 'program.json: ' + err; });
})();
