// Mock of Freya Bank statement services. Serves exactly the answers in test-customers.json.
import DB from "./test-customers.json";

const JSON_H = { "content-type": "application/json; charset=utf-8" };
const NOT_FOUND = {
  "cards.list": ["FB_IVR_CHANNEL_102", "Müşteriye ait geçerli kart bilgisi bulunamadı."],
  "cards.balance": ["FB_IVR_CHANNEL_120", "Card not found"],
  "statement.week.get": ["FB_IVR_CHANNEL_121", "Card not found"],
  "statement.pdf.send": ["FB_IVR_CHANNEL_107", "Pdf dokümanı bulunamadı"],
};
const BY_CUSTOMER = ["cards.list", "contact.email.get", "statement.pdf.send"];
const BY_CARD = ["cards.balance", "statement.week.get"];
const BY_CARD_WEEK = ["statement.week.decide", "statement.week.change"];

const CUSTOMERS = new Map(DB.customers.map((c) => [String(c.customerNo), c]));
const isTemplate = (v) => typeof v === "string" && v.includes("{{");

function result(code, type, message, root) {
  const guid = [...crypto.getRandomValues(new Uint8Array(16))].map((b) => b.toString(16).padStart(2, "0")).join("");
  return { guid, returnCode: code, messageText: message, code, message, type,
    details: { guid, rootCause: root || null, errorOrigin: root ? "ivr-gateway-test:ivr-channel-v0" : null } };
}
const send = (status, body) => new Response(JSON.stringify(body), { status, headers: JSON_H });
const err = (status, code, type, message) => send(status, { result: result(code, type, message, status === 500 ? "TechnicalError" : "ValidationError") });
const sleep = (s) => new Promise((r) => setTimeout(r, s * 1000));

async function answer(entry) {
  if (entry && entry.delaySeconds) await sleep(entry.delaySeconds);
  return send(entry.http, entry.response);
}
const empty = (v) => v === undefined || v === null || String(v).trim() === "";

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;
    if (path === "/health") return send(200, { ok: true });
    if (path.endsWith("/oauth2/token")) return send(200, { access_token: "mock-token", token_type: "Bearer", expires_in: 1800 });
    if (request.method !== "POST") return err(405, "INVALID_ARGUMENTS_ERROR", "ERROR", "POST only");
    const m = path.match(/\/voice\/v1\/([a-z.]+)$/);
    const service = m && m[1];
    if (!service || !(BY_CUSTOMER.includes(service) || BY_CARD.includes(service) || BY_CARD_WEEK.includes(service)))
      return err(404, "INVALID_ARGUMENTS_ERROR", "ERROR", "unknown service");
    let body = {};
    try { body = await request.json(); } catch (e) { return err(400, "INVALID_ARGUMENTS_ERROR", "ERROR", "invalid JSON body"); }
    const data = (body && body.data) || {};
    const notFound = () => {
      const nf = NOT_FOUND[service];
      return nf ? err(404, nf[0], "WARNING", nf[1]) : err(400, "INVALID_ARGUMENTS_ERROR", "ERROR", "no matching record");
    };

    if (BY_CUSTOMER.includes(service)) {
      if (empty(data.customerNo)) return err(400, "INVALID_ARGUMENTS_ERROR", "ERROR", "customer number cannot be empty");
      let c = CUSTOMERS.get(String(data.customerNo).trim());
      if (!c && isTemplate(data.customerNo)) c = DB.customers.find((x) => x.services[service]);
      const e = c && c.services[service];
      return e ? answer(e) : notFound();
    }

    if (empty(data.cardNumber)) return err(400, "INVALID_ARGUMENTS_ERROR", "ERROR", "card number cannot be empty");
    const card = String(data.cardNumber).trim();
    const owners = DB.customers.filter((c) => c.services[service] && c.services[service][card]);
    let slot = owners.length ? owners[0].services[service][card] : undefined;
    if (!slot && isTemplate(card)) {
      const c = DB.customers.find((x) => x.services[service] && Object.keys(x.services[service]).length);
      if (c) slot = c.services[service][Object.keys(c.services[service])[0]];
    }
    if (!slot) return notFound();
    if (BY_CARD.includes(service)) return answer(slot);

    if (empty(data.newStatementWeek)) return err(400, "INVALID_ARGUMENTS_ERROR", "ERROR", "new statement week cannot be empty");
    let e = slot[String(data.newStatementWeek).trim()];
    if (!e && isTemplate(data.newStatementWeek)) e = slot[Object.keys(slot)[0]];
    return e ? answer(e) : notFound();
  },
};
