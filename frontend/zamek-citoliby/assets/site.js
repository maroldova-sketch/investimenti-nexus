(function(){
  const cfg = window.SITE_CONFIG || {};
  const $ = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));

  // menu
  const mb = $('.menu-btn'), nav = $('.nav');
  if (mb && nav) mb.addEventListener('click', () => { const o = nav.classList.toggle('open'); mb.setAttribute('aria-expanded', o); });

  // program
  const MONTHS = ['led','úno','bře','dub','kvě','čvn','čvc','srp','zář','říj','lis','pro'];
  const CAT = {Divadlo:'Divadlo', Koncert:'Koncert', Gastro:'Gastro', Event:'Slavnost', Svatba:'Svatba'};
  function fmtDate(iso){ const d = new Date(iso+'T12:00:00'); return {d: d.getDate(), m: MONTHS[d.getMonth()], y: d.getFullYear()}; }
  function eventCard(e){
    const a = fmtDate(e.start), b = fmtDate(e.end);
    const range = e.start===e.end ? `${a.d}. ${a.m}` : `${a.d}.–${b.d}. ${b.m}`;
    const status = e.status==='potvrzeno' ? '<span class="badge ok">potvrzeno</span>' : '<span class="badge">termín upřesníme</span>';
    const buy = (e.tickets ? `<a class="btn" href="${e.tickets}?utm_source=web&utm_medium=program&utm_campaign=${e.id}">Vstupenky</a>` : '');
    return `<article class="ev" data-cat="${e.category}">
      <div class="d">${range}<small>${a.y}${e.time?' · '+e.time:''}</small></div>
      <div><h3>${e.title}</h3><div class="meta"><span class="badge cat">${CAT[e.category]||e.category}</span> ${e.place}${e.note?' · '+e.note:''}</div></div>
      <div class="side">${buy||status}</div>
    </article>`;
  }
  async function loadProgram(){
    const r = await fetch('/data/program.json', {cache:'no-store'});
    const j = await r.json();
    const evs = j.events.filter(e => e.public).sort((x,y) => x.start.localeCompare(y.start));
    // rozsvícená okna
    const lit = evs.filter(e => e.announced).length;
    $$('.facade .w').forEach((w,i) => { if (i < lit) setTimeout(() => w.classList.add('lit'), 300 + i*160); });
    const cap = $('#facade-cap'); if (cap) cap.textContent = `Rozsvíceno ${lit} z ${j.windows} oken. Každý oznámený večer rozsvítí jedno.`;
    // nejbližší
    const next = $('#next-events');
    if (next) { const today = new Date().toISOString().slice(0,10); next.innerHTML = evs.filter(e => e.end >= today).slice(0,3).map(eventCard).join('') || '<p>Program zveřejníme 24. 11. 2026.</p>'; }
    // celý program
    const list = $('#program-list');
    if (list) {
      const render = (cat) => { list.innerHTML = evs.filter(e => !cat || e.category===cat).map(eventCard).join('') || '<p>Zatím nic v této rubrice.</p>'; };
      render('');
      $$('.filters button').forEach(b => b.addEventListener('click', () => { $$('.filters button').forEach(x => x.setAttribute('aria-pressed','false')); b.setAttribute('aria-pressed','true'); render(b.dataset.cat||''); }));
    }
    const gl = $('#gastro-list');
    if (gl) gl.innerHTML = evs.filter(e => e.category==='Gastro' || e.category==='Event').map(eventCard).join('');
    // tlačítka vstupenek
    if (cfg.ticketsUrl) $$('[data-tickets]').forEach(a => { a.href = cfg.ticketsUrl; a.hidden = false; });
  }
  loadProgram().catch(() => {});

  // formuláře
  $$('form.f').forEach(f => f.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const msg = $('.msg', f); msg.className = 'msg'; msg.textContent = 'Odesílám…';
    const data = Object.fromEntries(new FormData(f).entries());
    data.page = location.pathname; data.source = f.dataset.source || 'web';
    try {
      const r = await fetch(f.action, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)});
      const j = await r.json().catch(() => ({}));
      if (r.ok && j.ok) { msg.className = 'msg ok'; msg.textContent = f.dataset.ok || 'Děkujeme, jste v seznamu. Ozveme se, jakmile bude co oznámit.'; f.reset(); }
      else { msg.className = 'msg err'; msg.textContent = j.error || 'Nepodařilo se odeslat. Napište nám na info@zamek-citoliby.cz.'; }
    } catch (e) { msg.className = 'msg err'; msg.textContent = 'Nepodařilo se odeslat. Napište nám na info@zamek-citoliby.cz.'; }
  }));

  // cookies: měření jen po souhlasu
  const KEY = 'zc.consent';
  let consent = null; try { consent = localStorage.getItem(KEY); } catch(e) {}
  function loadTracking(){
    if (cfg.metaPixelId) { !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js'); fbq('init', cfg.metaPixelId); fbq('track','PageView'); }
    if (cfg.ga4Id) { const s = document.createElement('script'); s.async = true; s.src = 'https://www.googletagmanager.com/gtag/js?id='+cfg.ga4Id; document.head.appendChild(s); window.dataLayer = window.dataLayer||[]; function gtag(){dataLayer.push(arguments)} window.gtag = gtag; gtag('js', new Date()); gtag('config', cfg.ga4Id, {anonymize_ip:true}); }
  }
  if (consent === 'yes') loadTracking();
  else if (consent !== 'no' && (cfg.metaPixelId || cfg.ga4Id)) {
    const bar = document.createElement('div'); bar.className = 'cookie'; bar.setAttribute('role','dialog');
    bar.innerHTML = '<span>Používáme měření návštěvnosti (Meta, Google), abychom věděli, co vás zajímá. <a href="/soukromi.html">Více</a></span><button class="btn" id="c-yes">Souhlasím</button><button class="btn ghost dark" id="c-no">Jen nutné</button>';
    document.body.appendChild(bar);
    $('#c-yes', bar).onclick = () => { try{localStorage.setItem(KEY,'yes')}catch(e){}; bar.remove(); loadTracking(); };
    $('#c-no', bar).onclick = () => { try{localStorage.setItem(KEY,'no')}catch(e){}; bar.remove(); };
  }
  // odkazy na sítě
  $$('[data-ig]').forEach(a => a.href = cfg.instagram || '#');
  $$('[data-fb]').forEach(a => a.href = cfg.facebook || '#');
  // sledování kliků Koupit
  document.addEventListener('click', (e) => { const a = e.target.closest('a[data-tickets], .ev a.btn'); if (a && window.fbq) fbq('track','InitiateCheckout'); if (a && window.gtag) gtag('event','begin_checkout'); });
})();
