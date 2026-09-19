// Cloudflare Pages Function: POST /api/subscribe → Ecomail (+ volitelný webhook)
// Env: ECOMAIL_API_KEY, ECOMAIL_LIST_ID, WEBHOOK_URL (volitelné, např. Make/n8n/Sheet)
const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export async function onRequestPost({ request, env }) {
  let d; try { d = await request.json(); } catch { return json({ ok: false, error: "Neplatná data." }, 400); }
  if (d.web) return json({ ok: true }); // honeypot: tváříme se, že prošlo
  const email = String(d.email || "").trim().toLowerCase();
  const name = String(d.name || "").trim().slice(0, 120);
  if (!EMAIL.test(email)) return json({ ok: false, error: "Zkontrolujte e-mail." }, 400);
  if (d.consent !== "ano") return json({ ok: false, error: "Bez souhlasu vás nemůžeme zapsat." }, 400);
  const source = String(d.source || "web").slice(0, 60);

  const results = [];
  if (env.ECOMAIL_API_KEY && env.ECOMAIL_LIST_ID) {
    const r = await fetch(`https://api2.ecomailapp.cz/lists/${env.ECOMAIL_LIST_ID}/subscribe`, {
      method: "POST",
      headers: { "content-type": "application/json", key: env.ECOMAIL_API_KEY },
      body: JSON.stringify({
        subscriber_data: { email, name, tags: [source, "predprodej-2027"], custom_fields: { CONSENT_AT: new Date().toISOString(), PAGE: String(d.page || "") } },
        trigger_autoresponders: true, update_existing: true, resubscribe: false, skip_confirmation: false,
      }),
    });
    results.push(["ecomail", r.status]);
    if (!r.ok) console.log("ecomail", r.status, await r.text());
  }
  if (env.WEBHOOK_URL) {
    const r = await fetch(env.WEBHOOK_URL, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ kind: "subscribe", email, name, source, page: d.page, at: new Date().toISOString() }) }).catch(() => null);
    results.push(["webhook", r ? r.status : 0]);
  }
  if (!results.length) return json({ ok: false, error: "Zápis zatím není nastaven. Napište nám na info@zamek-citoliby.cz." }, 503);
  if (results.some(([, s]) => s >= 200 && s < 300)) return json({ ok: true });
  return json({ ok: false, error: "Nepodařilo se uložit. Zkuste to prosím znovu." }, 502);
}
export const onRequest = ({ request }) => request.method === "POST" ? undefined : json({ ok: false, error: "Použijte POST." }, 405);
