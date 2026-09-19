// Cloudflare Pages Function: POST /api/poptavka → e-mail přes Resend (+ volitelný webhook)
// Env: RESEND_API_KEY, NOTIFY_EMAIL (kam chodí poptávky, např. svatby@zamek-citoliby.cz), FROM_EMAIL (ověřená doména v Resend), WEBHOOK_URL (volitelné)
const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const esc = (s) => String(s ?? "").replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]));

export async function onRequestPost({ request, env }) {
  let d; try { d = await request.json(); } catch { return json({ ok: false, error: "Neplatná data." }, 400); }
  if (d.web) return json({ ok: true });
  const email = String(d.email || "").trim().toLowerCase();
  if (!EMAIL.test(email)) return json({ ok: false, error: "Zkontrolujte e-mail." }, 400);
  if (!String(d.name || "").trim()) return json({ ok: false, error: "Doplňte jméno." }, 400);
  if (d.consent !== "ano") return json({ ok: false, error: "Bez souhlasu poptávku nemůžeme přijmout." }, 400);
  const fields = ["name", "phone", "email", "type", "date", "guests", "message", "source", "page"];
  const rows = fields.map((k) => `<tr><td style="padding:4px 10px 4px 0;color:#666">${k}</td><td>${esc(d[k]).slice(0, 2000)}</td></tr>`).join("");
  const html = `<h2>Poptávka z webu: ${esc(d.type || "")}</h2><table>${rows}</table><p>${new Date().toLocaleString("cs-CZ", { timeZone: "Europe/Prague" })}</p>`;

  const results = [];
  if (env.RESEND_API_KEY && env.NOTIFY_EMAIL) {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${env.RESEND_API_KEY}` },
      body: JSON.stringify({ from: env.FROM_EMAIL || "Zámek Cítoliby <web@zamek-citoliby.cz>", to: env.NOTIFY_EMAIL.split(",").map((s) => s.trim()), reply_to: email, subject: `Poptávka: ${d.type || "akce"} · ${d.name} · ${d.date || "termín neuveden"}`, html }),
    });
    results.push(["resend", r.status]);
    if (!r.ok) console.log("resend", r.status, await r.text());
  }
  if (env.WEBHOOK_URL) {
    const r = await fetch(env.WEBHOOK_URL, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ kind: "poptavka", ...d, at: new Date().toISOString() }) }).catch(() => null);
    results.push(["webhook", r ? r.status : 0]);
  }
  if (!results.length) return json({ ok: false, error: "Formulář zatím není napojen. Napište nám na info@zamek-citoliby.cz." }, 503);
  if (results.some(([, s]) => s >= 200 && s < 300)) return json({ ok: true });
  return json({ ok: false, error: "Nepodařilo se odeslat. Napište nám na info@zamek-citoliby.cz." }, 502);
}
export const onRequest = ({ request }) => request.method === "POST" ? undefined : json({ ok: false, error: "Použijte POST." }, 405);
