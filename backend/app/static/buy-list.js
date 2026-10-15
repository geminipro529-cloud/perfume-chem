// Buy: what the saved cards need and the stock lists don't own, priced from
// PerfumersWorld list prices (GET /v2/workbench/buy-list, schema workbench-buy-list-v1,
// built by engine/buy_list.py). Kenny's input goes out as buy events (POST
// /v2/workbench/buy-events) before the page data is read again: the US$ rate, the
// budget, a match answer, an order, or a pasted LABPICKS/1 block. Ticks stay in page
// memory; nothing here orders anything.
//
// Money arrives as unrounded decimal strings and is summed and rounded here on the
// digits (BigInt), never through floats. Shop titles, card names and every other text
// go in through textContent only, never HTML strings. lab/stock.js attaches it; node
// loads the same file in the tests.

const BUY_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const BUY_CHECK_STOCK_TEXT = "Your two stock lists disagree on this one, so this page counts it neither as owned nor as not owned.";

// "1254.77" rounded half up to `places` decimals, as plain digits ("1255"); null when
// the text is not a non-negative decimal.
function buyRound(text, places) {
  const match = /^(\d+)(?:\.(\d+))?$/.exec(String(text ?? "").trim());
  if (!match) return null;
  const fraction = match[2] || "";
  let scaled = BigInt(match[1] + fraction.slice(0, places).padEnd(places, "0"));
  if ((fraction[places] || "0") >= "5") scaled += 1n;
  const digits = scaled.toString().padStart(places + 1, "0");
  return places ? `${digits.slice(0, -places)}.${digits.slice(-places)}` : digits;
}

function buyGroup(digits) {
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function buyIsUnder(text, limit) {
  const whole = /^(\d+)/.exec(String(text ?? "").trim());
  return Boolean(whole) && BigInt(whole[1]) < BigInt(limit);
}

// "฿1,255": whole baht, half up, thousands separated.
function buyThbText(text) {
  const rounded = buyRound(text, 0);
  return rounded === null ? "" : `฿${buyGroup(rounded)}`;
}

// "US$7.30": two decimals, half up.
function buyUsdText(text) {
  const rounded = buyRound(text, 2);
  if (rounded === null) return "";
  const [whole, cents] = rounded.split(".");
  return `US$${buyGroup(whole)}.${cents}`;
}

// A cost per bottle: whole baht, or one decimal under ฿10 ("฿2.4"; "฿2" for 2.0).
function buyBottleThbText(text) {
  if (!buyIsUnder(text, 10)) return buyThbText(text);
  const rounded = buyRound(text, 1);
  return rounded === null ? "" : `฿${rounded.replace(/\.0$/, "")}`;
}

// "฿29 a bottle", or "฿29 to ฿35 a bottle" when the cards differ.
function buyBottleRangeText(range) {
  if (!range) return "";
  const low = buyBottleThbText(range.min);
  const high = buyBottleThbText(range.max);
  if (!low || !high) return "";
  return low === high ? `${low} a bottle` : `${low} to ${high} a bottle`;
}

// "2026-10-09" -> "9 Oct".
function buyDayLabel(isoDay) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(isoDay ?? ""));
  if (!match) return "";
  return `${Number(match[3])} ${BUY_MONTHS[Number(match[2]) - 1]}`;
}

function buyCount(count, word) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

// The banner line before the rate field; "" when the page has a current rate.
function buyRateBannerText(banner) {
  if (!banner) return "";
  if (banner.reason === "stale" && banner.last_set_on) return `No US$ rate since ${buyDayLabel(banner.last_set_on)}.`;
  if (banner.reason === "change") return "Type the new rate.";
  return "No US$ rate yet.";
}

// A dated price from a review or an order: "฿450 for 10 g, 14 Oct".
function buyShownPriceText(price) {
  if (!price || price.amount === undefined || price.amount === null) return "";
  const amount = price.currency === "THB" ? buyThbText(price.amount)
    : price.currency === "USD" ? buyUsdText(price.amount)
      : `${price.amount} ${price.currency || ""}`.trim();
  const pack = price.pack ? ` for ${price.pack}` : "";
  const day = price.observed_on ? `, ${buyDayLabel(price.observed_on)}` : "";
  return `${amount}${pack}${day}`;
}

// One offer as display lines. An unknown offer (maybe not this material) has no price.
function buyOfferView(offer, material) {
  const priced = offer.match !== "unknown";
  const form = offer.form && offer.form !== "neat" ? `, ${offer.form}` : "";
  const perG = priced && offer.usd_per_g ? `${buyUsdText(offer.usd_per_g)}/g, ${offer.observed_label || buyDayLabel(offer.observed_on)}` : "";
  let upfront = "";
  if (priced && offer.upfront_usd) {
    const thb = offer.upfront_thb ? `, ${buyThbText(offer.upfront_thb)}` : "";
    upfront = `${offer.default_pack_g} g: ${buyUsdText(offer.upfront_usd)}${thb}`;
  }
  return {
    offerKey: offer.offer_key,
    head: `${offer.shop} ${offer.sku}${form}`,
    title: offer.title || "",
    previous: offer.previous_title ? `${offer.shop} used to call it '${offer.previous_title}'.` : "",
    perG,
    upfront,
    bottle: priced ? buyBottleRangeText(offer.cost_per_bottle_thb) : "",
    unknown: priced ? "" : `No price: this may not be your ${material}.`,
    notThis: offer.last_not_this_on ? `You marked it not this on ${buyDayLabel(offer.last_not_this_on)}.` : "",
    question: offer.match_question || "",
    url: /^https?:\/\//.test(String(offer.product_url || "")) ? offer.product_url : "",
    linkText: `Open on ${offer.shop}`,
    tickable: offer.tickable === true,
  };
}

// One Buy first row as display text.
function buyRowView(row) {
  const cards = (row.cards || []).map((card) => {
    const cost = card.cost_per_bottle_thb ? `: ${buyBottleThbText(card.cost_per_bottle_thb)} a bottle` : "";
    return `${card.name || card.formula_id || "Unnamed card"}${cost}`;
  });
  const back = row.returned_from_order;
  return {
    materialKey: row.material_key,
    material: row.material,
    neededBy: `needed by ${buyCount(row.need_count ?? cards.length, "card")}`,
    cards,
    back: back ? `Back from your ${back.shop} order` : "",
    tier: row.pick_tier ? `Tier ${row.pick_tier}` : "",
    similar: (row.similar || []).map((entry) => entry.name).filter(Boolean),
    offers: (row.offers || []).map((offer) => buyOfferView(offer, row.material)),
  };
}

function buyCardNames(cards) {
  return (cards || []).map((card) => card.name || card.formula_id || "Unnamed card");
}

// A Tier 1 or Tier 2 pick in one line.
function buyPickText(pick) {
  const price = buyShownPriceText(pick.price);
  const reviewed = pick.reviewed_on ? ` Reviewed ${buyDayLabel(pick.reviewed_on)}${price ? `; ${price}` : ""}.` : (price ? ` ${price}.` : "");
  const note = pick.offer_note ? ` ${pick.offer_note}` : "";
  return `${pick.material}, ${pick.dose}: ${String(pick.reason || "").replace(/\.$/, "")}.${reviewed}${note}`;
}

function buyOrderLineText(line) {
  const price = buyShownPriceText(line.shown_price);
  return `${line.material}, ${line.pack}${price ? `, ${price}` : ""}${line.state === "STILL_COMING" ? " (still coming)" : ""}`;
}

// ---- Exact decimal sums (no floats) ----

function buyDecimal(text) {
  const match = /^(\d+)(?:\.(\d+))?$/.exec(String(text ?? "").trim());
  if (!match) return null;
  const fraction = match[2] || "";
  return { units: BigInt(match[1] + fraction), places: fraction.length };
}

function buyDecimalText({ units, places }) {
  const digits = units.toString().padStart(places + 1, "0");
  return places ? `${digits.slice(0, -places)}.${digits.slice(-places)}` : digits;
}

function buyScaled(value, places) {
  return value.units * 10n ** BigInt(places - value.places);
}

// The exact sum of non-negative decimal strings ("1254.77" + "0.5" = "1255.27");
// text that is not a decimal counts as nothing.
function buyDecimalSum(texts) {
  const values = (texts || []).map(buyDecimal).filter(Boolean);
  const places = Math.max(0, ...values.map((value) => value.places));
  const units = values.reduce((total, value) => total + buyScaled(value, places), 0n);
  return buyDecimalText({ units, places });
}

// The exact product of two decimal strings ("30" x "33.55" = "1006.50"); null when either is not one.
function buyDecimalTimes(left, right) {
  const a = buyDecimal(left);
  const b = buyDecimal(right);
  if (!a || !b) return null;
  return buyDecimalText({ units: a.units * b.units, places: a.places + b.places });
}

// -1, 0 or 1, comparing two decimal strings.
function buyDecimalCompare(left, right) {
  const a = buyDecimal(left);
  const b = buyDecimal(right);
  const places = Math.max(a.places, b.places);
  const difference = buyScaled(a, places) - buyScaled(b, places);
  return difference < 0n ? -1 : difference > 0n ? 1 : 0;
}

// ---- Ticks, the total bar and the events they post ----

// PerfumersWorld shipping, from PW's shipping page read 15 Oct 2026: US$30 on an
// order under US$150, free at US$150 or more.
const BUY_PW_SHIPPING_USD = "30";
const BUY_PW_FREE_SHIPPING_FROM_USD = "150";

// Ticks are a Map of material_key -> offer_key: at most one ticked offer per material.
function buyTick(ticks, materialKey, offerKey, checked) {
  const next = new Map(ticks);
  if (checked) next.set(materialKey, offerKey);
  else if (next.get(materialKey) === offerKey) next.delete(materialKey);
  return next;
}

// The ticked offers still on the page and tickable, in page order.
function buyTicked(data, ticks) {
  const ticked = [];
  for (const row of data?.buy_first || []) {
    const offerKey = ticks.get(row.material_key);
    const offer = (row.offers || []).find((entry) => entry.offer_key === offerKey && entry.tickable === true);
    if (offer) ticked.push({ materialKey: row.material_key, material: row.material, offer });
  }
  return ticked;
}

// After the data is read again: keep the ticks whose offers are still there and
// still confirmed. An offer whose question is open again (its PW title changed
// since "Same") loses its tick, so ticking it again asks again.
function buyKeepTicks(data, ticks) {
  return new Map(buyTicked(data, ticks)
    .filter((entry) => !entry.offer.match_question)
    .map((entry) => [entry.materialKey, entry.offer.offer_key]));
}

// The bar's text, or null when nothing is ticked. Without a US$ rate it shows no ฿
// figures at all (the rate banner asks for the rate). The budget line counts PW shipping.
function buyBarView(data, ticks) {
  const ticked = buyTicked(data, ticks);
  if (!ticked.length) return null;
  const rate = buyDecimal(data.fx?.rate) ? String(data.fx.rate).trim() : null;
  const priceOf = (offer) => (rate ? offer.upfront_thb : offer.upfront_usd);
  const priced = ticked.filter((entry) => buyDecimal(priceOf(entry.offer)));
  const goods = buyDecimalSum(priced.map((entry) => priceOf(entry.offer)));
  const shops = [...new Set(ticked.map((entry) => entry.offer.shop))];
  const parts = [`${ticked.length} ticked`];
  if (priced.length) parts.push(rate ? buyThbText(goods) : buyUsdText(goods));
  parts.push(buyCount(shops.length, "shop"));
  if (ticked.length > priced.length) parts.push(`${ticked.length - priced.length} not priced`);

  let shipping = "";
  let shippingThb = "0";
  const pw = ticked.filter((entry) => entry.offer.shop === "PW");
  if (pw.length) {
    const pwUsd = buyDecimalSum(pw.map((entry) => entry.offer.upfront_usd));
    if (buyDecimalCompare(pwUsd, BUY_PW_FREE_SHIPPING_FROM_USD) >= 0) {
      shipping = "PW ships free";
    } else {
      shippingThb = rate ? buyDecimalTimes(BUY_PW_SHIPPING_USD, rate) : "0";
      shipping = `PW shipping US$${BUY_PW_SHIPPING_USD}${rate ? ` (${buyThbText(shippingThb)})` : ""}`;
    }
  }

  let budget = "";
  if (rate && buyDecimal(data.budget?.amount_thb)) {
    const total = buyRound(buyDecimalSum([goods, shippingThb]), 0);
    const limit = buyRound(data.budget.amount_thb, 0);
    const over = BigInt(total) - BigInt(limit);
    budget = `${buyThbText(total)} of your ${buyThbText(limit)} budget${over > 0n ? `: ${buyThbText(String(over))} over` : ""}`;
  }

  return {
    totals: parts.join(", "),
    shipping,
    budget,
    shops: shops.map((shop) => ({ shop, count: ticked.filter((entry) => entry.offer.shop === shop).length })),
  };
}

// "PW-20261015-a1b2c3": one id shared by every line of one "I ordered these" click.
function buyOrderId(shop, isoDay, hex) {
  return `${shop}-${String(isoDay).replace(/-/g, "")}-${hex}`;
}

// One order event per ticked offer of `shop`, all with the same order_id.
function buyOrderEvents(data, ticks, shop, orderId) {
  return buyTicked(data, ticks)
    .filter((entry) => entry.offer.shop === shop)
    .map(({ materialKey, offer }) => ({
      kind: "order",
      order_id: orderId,
      shop,
      material_key: materialKey,
      offer_key: offer.offer_key,
      pack: `${offer.default_pack_g} g`,
      state: "ORDERED",
      shown_price: { amount: offer.upfront_usd, currency: "USD", observed_on: offer.observed_on },
    }));
}

// Kenny's answer to "Is PW <sku> '<title>' your <material>?": SAME or DIFFERENT.
function buyMatchEvent(materialKey, offer, answer) {
  return { kind: "match", material_key: materialKey, offer_key: offer.offer_key, answer, title_at_confirm: offer.title };
}

// The budget event for the typed amount ("1,600" and "฿1600" are read as 1600), the
// clearing event for null, or null when the text is not an amount above zero.
function buyBudgetEvent(text) {
  if (text === null) return { kind: "budget", clear: true };
  const amount = String(text ?? "").replace(/[\s,฿]/g, "");
  if (!/^\d+(\.\d+)?$/.test(amount) || !/[1-9]/.test(amount)) return null;
  return { kind: "budget", amount_thb: amount };
}

// material_key -> display name, from every list on the page.
function buyMaterialNames(data) {
  const names = new Map();
  const tiers = data?.tiers || {};
  for (const list of [data?.buy_first, tiers["1"], tiers["2"], data?.skip]) {
    for (const item of Array.isArray(list) ? list : []) {
      if (item.material_key && item.material) names.set(item.material_key, item.material);
    }
  }
  return names;
}

// A dry-run answer to a pasted LABPICKS/1 block: "2 picks and 1 skip", one line each.
function buyPicksPreview(response, names = new Map()) {
  const entries = response?.entries || [];
  const picks = entries.filter((entry) => entry.kind === "pick");
  const skips = entries.filter((entry) => entry.kind === "skip");
  const nameOf = (entry) => names.get(entry.material_key) || entry.material_key;
  const lines = entries.map((entry) => (entry.kind === "pick"
    ? `${nameOf(entry)}, Tier ${entry.tier}, ${entry.dose}: ${entry.reason}`
    : `${nameOf(entry)}, skip: ${entry.reason}`));
  return { summary: `${buyCount(picks.length, "pick")} and ${buyCount(skips.length, "skip")}`, lines };
}

// ---- On the way: answers, "It arrived" and the price paid ----

const BUY_SHOP_NAMES = { PW: "PerfumersWorld" };
const BUY_LABEL_CHECK = "Check the label: form, strength and species.";

// Kenny's answer for one line of an order: STILL_COMING, ARRIVED, DIDNT_COME, NOT_THIS
// or ALREADY_HAVE. Only ORDERED carries the shown price.
function buyOrderStateEvent(group, line, state) {
  return {
    kind: "order",
    order_id: group.order_id,
    shop: group.shop,
    material_key: line.material_key,
    offer_key: line.offer_key,
    pack: line.pack,
    state,
  };
}

// The same answer for every line of the order (the day-10 nudge's buttons).
function buyGroupStateEvents(group, state) {
  return (group.lines || []).map((line) => buyOrderStateEvent(group, line, state));
}

function buySku(line) {
  return String(line.offer_key || "").replace(/^[a-z]+:/, "");
}

// "5 g" -> "5"; null for a pack not in grams.
function buyPackGrams(pack) {
  const match = /^\s*(\d+(?:\.\d+)?)\s*g\s*$/.exec(String(pack ?? ""));
  return match ? match[1] : null;
}

// "0.1" -> "10", "0.025" -> "2.5", "1" -> "100"; null when not a decimal.
function buyPercentText(fraction) {
  const times = buyDecimalTimes(fraction, "100");
  if (times === null) return null;
  return times.includes(".") ? times.replace(/0+$/, "").replace(/\.$/, "") : times;
}

// The Stock page's add form, filled from an order line (field name -> value). Neat is
// 100%; a PW dilution ("10% in DPG") is w/w in its solvent. What the line can't tell
// (category, and the strength of an unknown form) is left blank for Kenny to choose.
function buyStockPrefill(group, line) {
  const fields = {
    identity_name: line.material,
    category: "",
    supplier_name: BUY_SHOP_NAMES[group.shop] || group.shop,
    supplier_sku: buySku(line),
    user_note: `Arrived from ${group.shop} order ${group.order_id}`,
  };
  const percent = buyPercentText(line.strength);
  if (line.form === "neat") {
    return { ...fields, fraction_percent_decimal: "100", fraction_basis: "neat", carrier: "",
      physical_form: "as_supplied", homogeneity: "NOT_APPLICABLE" };
  }
  if (percent !== null && line.solvent) {
    return { ...fields, fraction_percent_decimal: percent, fraction_basis: "mass_fraction", carrier: line.solvent,
      physical_form: "solution", homogeneity: "" };
  }
  return { ...fields, fraction_percent_decimal: "", fraction_basis: "", carrier: "", physical_form: "", homogeneity: "" };
}

// "Paid US$37.40?" from the order's shown price.
function buyPaidQuestion(line) {
  const price = line.shown_price;
  return price?.amount ? `Paid ${buyShownPriceText({ amount: price.amount, currency: price.currency })}?` : "What did you pay?";
}

// The stock price for [Save]: what Kenny paid for the pack, per g, in the shop's
// currency. null when the amount is not a number above zero.
function buyStockPriceBody(stockId, group, line, amountText) {
  const amount = String(amountText ?? "").replace(/[\s,฿$]|US/g, "");
  if (!/^\d+(\.\d+)?$/.test(amount) || !/[1-9]/.test(amount)) return null;
  return {
    stock_id: stockId,
    per_unit: "g",
    pack_price: amount,
    pack_size: buyPackGrams(line.pack),
    currency: line.shown_price?.currency || "USD",
    note: `Paid for ${group.shop} order ${group.order_id}`,
  };
}

// The "It arrived" walk is { shop, orderId, done, stage, materialKey, offerKey, stockId, note }.
// stage: "check" (label check), "stock" (the Stock add is open), "price" (paid?).
// The current line is the pinned one while adding it, else the first line still on the
// way: after each answer the page data is read again and handled lines drop out.
function buyWalkStart(group) {
  return { shop: group.shop, orderId: group.order_id, done: 0, stage: "check", materialKey: null, offerKey: null,
    stockId: null, note: "" };
}

function buyWalkLine(data, walk) {
  if (!walk) return null;
  const group = (data?.on_the_way || []).find((entry) => entry.shop === walk.shop && entry.order_id === walk.orderId);
  const lines = group?.lines || [];
  const pinned = walk.offerKey
    ? lines.find((line) => line.material_key === walk.materialKey && line.offer_key === walk.offerKey) : null;
  const line = pinned || lines[0];
  if (!line) return null;
  return { group, line, number: walk.done + 1, total: walk.done + lines.length, stage: pinned ? walk.stage : "check" };
}

// The walk after an answer: matches, differs, added ({ stockId }), closed, saved, skipped
// or stop (null: the walk ends; lines not handled stay on the way).
function buyWalkNext(walk, answer, detail = {}) {
  if (!walk || answer === "stop") return null;
  const next = { ...walk, stage: "check", materialKey: null, offerKey: null, stockId: null, note: "" };
  if (answer === "differs" || answer === "saved" || answer === "skipped") return { ...next, done: walk.done + 1 };
  if (answer === "matches") {
    return { ...next, stage: "stock", materialKey: detail.line.material_key, offerKey: detail.line.offer_key };
  }
  if (answer === "added") return { ...walk, stage: "price", stockId: detail.stockId, note: "" };
  if (answer === "closed") {
    return { ...walk, stage: "check", stockId: null, note: "Not added to your stock, and nothing saved for this one." };
  }
  return walk;
}

// What the walk shows now, or null when the order has no line left.
function buyWalkView(data, walk) {
  const step = buyWalkLine(data, walk);
  if (!step) return null;
  const { group, line, number, total, stage } = step;
  const form = line.form && line.form !== "neat" ? `, ${line.form}` : "";
  return {
    shop: group.shop,
    orderId: group.order_id,
    stage,
    text: `${number} of ${total}: ${line.material}, ${group.shop} ${buySku(line)}${form}, ${line.pack}. ${BUY_LABEL_CHECK}`,
    note: stage === "stock" ? "Add it on the Stock page, then come back here." : walk.note || "",
    question: stage === "price" ? buyPaidQuestion(line) : "",
    amount: line.shown_price?.amount || "",
  };
}

// ---- The page ----

function buyEl(doc, tag, className, text) {
  const node = doc.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function buySection(doc, title, note) {
  const section = buyEl(doc, "section", "make-group");
  section.append(buyEl(doc, "h2", "", title));
  if (note) section.append(buyEl(doc, "p", "field-help", note));
  return section;
}

function buyButton(doc, text, type = "button") {
  const button = buyEl(doc, "button", "quiet-button", text);
  button.type = type;
  return button;
}

// "Is PW <sku> '<title>' your <material>? [Same] [Different] [Not now]", shown on the
// first tick of an offer the shop list doesn't confirm. Not now writes nothing.
function buyMatchAsk(doc, question, onAnswer) {
  const ask = buyEl(doc, "div", "make-ask buy-match");
  ask.hidden = true;
  const buttons = buyEl(doc, "div", "make-left-form");
  const same = buyButton(doc, "Same");
  const different = buyButton(doc, "Different");
  const later = buyButton(doc, "Not now");
  const message = buyEl(doc, "p", "make-left-message");
  message.setAttribute("role", "status");
  buttons.append(same, different, later);
  ask.append(buyEl(doc, "p", "make-verdict", question), buttons, message);
  const answer = async (value) => {
    same.disabled = true;
    different.disabled = true;
    message.textContent = "Saving…";
    try {
      await onAnswer(value);
    } catch (error) {
      message.textContent = `Not saved: ${error?.message || error}`;
      same.disabled = false;
      different.disabled = false;
    }
  };
  same.addEventListener("click", () => answer("SAME"));
  different.addEventListener("click", () => answer("DIFFERENT"));
  later.addEventListener("click", () => { ask.hidden = true; message.textContent = ""; });
  return ask;
}

function buyOfferNode(doc, view, offer, { materialKey, ticks = new Map(), onTick = () => {}, onAnswer = async () => {} } = {}) {
  const box = buyEl(doc, "li", "make-row buy-offer");
  box.dataset.offerKey = view.offerKey;
  const head = buyEl(doc, "div", "make-card-head");
  head.append(buyEl(doc, "strong", "", view.head));
  let ask = null;
  if (view.tickable) {
    if (view.question) ask = buyMatchAsk(doc, view.question, (answer) => onAnswer(materialKey, offer, answer));
    const tick = buyEl(doc, "span", "buy-tick");
    tick.dataset.offerKey = view.offerKey;
    const label = buyEl(doc, "label");
    label.setAttribute("style", "display: inline-flex; align-items: center; justify-content: center; min-width: 44px; min-height: 44px;");
    const input = buyEl(doc, "input");
    Object.assign(input, { type: "checkbox", checked: ticks.get(materialKey) === view.offerKey });
    input.dataset.materialKey = materialKey;
    input.dataset.offerKey = view.offerKey;
    input.setAttribute("aria-label", `Tick ${view.head} to buy`);
    input.setAttribute("style", "width: 22px; height: 22px;");
    input.addEventListener("change", () => {
      if (input.checked && ask) {
        // Not ticked until Kenny says it is the same material.
        input.checked = false;
        ask.hidden = false;
        return;
      }
      onTick(materialKey, view.offerKey, input.checked);
    });
    label.append(input);
    tick.append(label);
    head.append(tick);
  }
  box.append(head);
  for (const text of [view.title, view.previous, view.perG, view.upfront, view.bottle, view.unknown, view.notThis]) {
    if (text) box.append(buyEl(doc, "span", "", text));
  }
  if (view.url) {
    const link = buyEl(doc, "a", "", view.linkText);
    link.href = view.url;
    link.target = "_blank";
    link.rel = "noopener";
    box.append(link);
  }
  if (ask) box.append(ask);
  else if (view.question) box.append(buyEl(doc, "p", "field-help", view.question));
  return box;
}

function buyRowNode(doc, row, handlers = {}) {
  const view = buyRowView(row);
  const card = buyEl(doc, "article", "make-card buy-row");
  const head = buyEl(doc, "div", "make-card-head");
  head.append(buyEl(doc, "h3", "", view.material));
  if (view.tier) head.append(buyEl(doc, "span", "make-chip make-chip-ok", view.tier));
  card.append(head);
  const needed = buyEl(doc, "details", "optional-details");
  needed.append(buyEl(doc, "summary", "", view.neededBy));
  const names = buyEl(doc, "ul", "make-rows");
  for (const name of view.cards) names.append(buyEl(doc, "li", "", name));
  needed.append(names);
  card.append(needed);
  if (view.back) card.append(buyEl(doc, "p", "make-verdict", view.back));
  if (view.similar.length) card.append(buyEl(doc, "p", "field-help", `Similar you own: ${view.similar.join(", ")}`));
  if (view.offers.length) {
    const offers = buyEl(doc, "ul", "make-rows");
    view.offers.forEach((offer, index) => {
      offers.append(buyOfferNode(doc, offer, row.offers[index], { ...handlers, materialKey: row.material_key }));
    });
    card.append(offers);
  } else {
    card.append(buyEl(doc, "p", "field-help", "No shop price for this one yet."));
  }
  return card;
}

// The rate field: "1 US$ = [__] ฿ [Save]", with its message beside it.
function buyRateForm(doc, banner, onSave) {
  const form = buyEl(doc, "form", "make-left-form buy-rate");
  form.append(buyEl(doc, "p", "make-verdict", buyRateBannerText(banner)));
  const label = buyEl(doc, "label", "", "1 US$ = ");
  const input = buyEl(doc, "input");
  Object.assign(input, { name: "rate", inputMode: "decimal", autocomplete: "off", required: true });
  label.append(input, buyEl(doc, "span", "", " ฿"));
  const save = buyEl(doc, "button", "quiet-button", "Save");
  save.type = "submit";
  const message = buyEl(doc, "p", "make-left-message");
  message.setAttribute("role", "status");
  form.append(label, save, message);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = String(input.value || "").trim();
    if (!/^\d+(\.\d+)?$/.test(text)) {
      message.textContent = "Type how many baht one US$ buys, such as 33.55.";
      input.focus();
      return;
    }
    save.disabled = true;
    message.textContent = "Saving…";
    try {
      await onSave(text);
    } catch (error) {
      message.textContent = error?.status === 422 ? (error.message || "Not saved.") : `Not saved: ${error?.message || error}`;
      save.disabled = false;
    }
  });
  return form;
}

// With a current rate: "1 US$ = 33.55 ฿, set 15 Oct. [Change]". Change shows the rate
// field, so a mistyped rate can be put right before it goes stale.
function buyRateChange(doc, fx, onSave) {
  const box = buyEl(doc, "div", "buy-rate-current");
  const line = buyEl(doc, "p", "field-help");
  const set = fx.set_on ? `, set ${buyDayLabel(fx.set_on)}` : "";
  const change = buyButton(doc, "Change");
  line.append(buyEl(doc, "span", "", `1 US$ = ${fx.rate} ฿${set}. `), change);
  const form = buyRateForm(doc, { reason: "change" }, onSave);
  form.hidden = true;
  change.addEventListener("click", () => {
    line.hidden = true;
    form.hidden = false;
    form.querySelector("input")?.focus();
  });
  box.append(line, form);
  return box;
}

// The budget: "Budget ฿ [____] [Save] [Clear]"; Clear only when one is set.
function buyBudgetForm(doc, budget, onSave) {
  const form = buyEl(doc, "form", "make-left-form buy-budget");
  if (budget?.amount_thb) form.append(buyEl(doc, "p", "field-help", `Budget: ${buyThbText(budget.amount_thb)}`));
  const label = buyEl(doc, "label", "", "Budget ฿");
  const input = buyEl(doc, "input");
  Object.assign(input, { name: "budget", inputMode: "numeric", autocomplete: "off", value: budget?.amount_thb || "" });
  label.append(input);
  const save = buyButton(doc, "Save", "submit");
  const message = buyEl(doc, "p", "make-left-message");
  message.setAttribute("role", "status");
  form.append(label, save);
  const send = async (event) => {
    save.disabled = true;
    message.textContent = "Saving…";
    try {
      await onSave(event);
    } catch (error) {
      message.textContent = `Not saved: ${error?.message || error}`;
      save.disabled = false;
    }
  };
  if (budget?.amount_thb) {
    const clear = buyButton(doc, "Clear");
    clear.addEventListener("click", () => send(buyBudgetEvent(null)));
    form.append(clear);
  }
  form.append(message);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const entry = buyBudgetEvent(input.value);
    if (!entry) {
      message.textContent = "Type your budget in baht, such as 1600.";
      input.focus();
      return;
    }
    send(entry);
  });
  return form;
}

// Draw the whole page into `target` from the buy-list payload. `ticks` (material_key
// -> offer_key) sets the tick boxes; onTick, onAnswer and saveBudget take Kenny's input.
// On the way: onWay(action, group, line) answers an order line, `walk` is the "It
// arrived" walk (buyWalkStart) and onWalk(answer, detail) takes its answers.
function buyRender(doc, target, data, {
  saveRate = async () => {}, saveBudget = async () => {}, ticks = new Map(), onTick = () => {}, onAnswer = async () => {},
  onWay = async () => {}, onWalk = async () => {}, walk = null,
} = {}) {
  target.replaceChildren();
  target.append(buyEl(doc, "p", "make-shopping-for", data.price_header || ""));
  if (data.rate_banner) target.append(buyRateForm(doc, data.rate_banner, saveRate));
  else if (data.fx?.rate) target.append(buyRateChange(doc, data.fx, saveRate));
  target.append(buyBudgetForm(doc, data.budget, saveBudget));

  const first = buySection(doc, "Buy first", "from your cards and stock");
  const rows = data.buy_first || [];
  if (!rows.length) first.append(buyEl(doc, "p", "make-verdict", "Nothing on your saved cards is missing from your stock."));
  for (const row of rows) first.append(buyRowNode(doc, row, { ticks, onTick, onAnswer }));
  target.append(first);

  if ((data.check_stock || []).length) {
    const check = buySection(doc, "Check stock", BUY_CHECK_STOCK_TEXT);
    const list = buyEl(doc, "ul", "make-rows");
    for (const item of data.check_stock) {
      const entry = buyEl(doc, "li", "make-row");
      entry.dataset.status = "unknown";
      entry.append(buyEl(doc, "strong", "", item.material),
        buyEl(doc, "span", "", `Cards: ${buyCardNames(item.cards).join(", ")}`));
      if (item.reason) entry.append(buyEl(doc, "span", "", item.reason));
      list.append(entry);
    }
    check.append(list);
    target.append(check);
  }

  if ((data.unreadable || []).length) {
    target.append(buyEl(doc, "p", "field-help", `Couldn't read: ${buyCardNames(data.unreadable).join(", ")}.`));
  }

  const tiers = data.tiers || {};
  for (const tier of ["1", "2"]) {
    const section = buySection(doc, `Tier ${tier}`);
    const picks = tiers[tier] || [];
    if (!picks.length) section.append(buyEl(doc, "p", "field-help", "No picks."));
    const list = buyEl(doc, "ul", "make-rows");
    for (const pick of picks) list.append(buyEl(doc, "li", "make-row", buyPickText(pick)));
    if (picks.length) section.append(list);
    target.append(section);
  }
  const third = buySection(doc, "Tier 3");
  third.append(buyEl(doc, "p", "field-help", tiers["3"]?.note || "needs fresh shop prices"));
  target.append(third);

  if ((data.skip || []).length) {
    const skip = buySection(doc, "Skip");
    const list = buyEl(doc, "ul", "make-rows");
    for (const item of data.skip) list.append(buyEl(doc, "li", "make-row", `${item.material}: ${item.reason}`));
    skip.append(list);
    target.append(skip);
  }

  if ((data.on_the_way || []).length) {
    const way = buySection(doc, "On the way");
    const walkView = buyWalkView(data, walk);
    for (const group of data.on_the_way) {
      const walking = walkView && walkView.shop === group.shop && walkView.orderId === group.order_id ? walkView : null;
      way.append(buyGroupNode(doc, group, { onWay, onWalk, walk: walking }));
    }
    target.append(way);
  }
}

// A 44 px tap target.
function buyTapButton(doc, text, action) {
  const button = buyButton(doc, text);
  button.dataset.action = action;
  button.setAttribute("style", "min-height: 44px;");
  return button;
}

// One order on the way: the day-10 nudge with [Still coming] [Didn't come] for the
// whole order, each line with [Didn't come] [Already have it], then [It arrived], or
// the walk's current step when Kenny is walking this order.
function buyGroupNode(doc, group, { onWay = async () => {}, onWalk = async () => {}, walk = null } = {}) {
  const box = buyEl(doc, "div", "make-ask buy-way");
  box.setAttribute("style", "max-width: 100%; box-sizing: border-box; overflow-wrap: anywhere;");
  box.append(buyEl(doc, "h3", "", `${group.shop}, ordered ${buyDayLabel(group.ordered_on)}`));
  const message = buyEl(doc, "p", "make-left-message");
  message.setAttribute("role", "status");
  const buttons = [];
  const act = async (run) => {
    for (const button of buttons) button.disabled = true;
    message.textContent = "Saving…";
    try {
      await run();
      message.textContent = "";
    } catch (error) {
      message.textContent = `Not saved: ${error?.message || error}`;
    } finally {
      for (const button of buttons) button.disabled = false;
    }
  };
  const tap = (text, action, run) => {
    const button = buyTapButton(doc, text, action);
    button.addEventListener("click", () => act(run));
    buttons.push(button);
    return button;
  };
  if (group.nudge) {
    box.append(buyEl(doc, "p", "make-verdict", group.nudge_text));
    const nudge = buyEl(doc, "div", "make-left-form");
    nudge.append(tap("Still coming", "still-coming", () => onWay("still-coming", group)),
      tap("Didn't come", "didnt-come-all", () => onWay("didnt-come-all", group)));
    box.append(nudge);
  }
  const lines = buyEl(doc, "ul", "make-rows");
  for (const line of group.lines || []) {
    const row = buyEl(doc, "li", "make-row");
    const answers = buyEl(doc, "div", "make-left-form");
    answers.append(tap("Didn't come", "didnt-come", () => onWay("didnt-come", group, line)),
      tap("Already have it", "already-have", () => onWay("already-have", group, line)));
    row.append(buyEl(doc, "span", "", buyOrderLineText(line)), answers);
    lines.append(row);
  }
  box.append(lines);
  if (!walk) {
    const start = buyEl(doc, "div", "make-left-form");
    start.append(tap("It arrived", "arrived", () => onWay("arrived", group)));
    box.append(start);
  } else {
    const panel = buyEl(doc, "div", "panel buy-walk");
    panel.append(buyEl(doc, "p", "make-verdict", walk.text));
    if (walk.note) panel.append(buyEl(doc, "p", "field-help", walk.note));
    const row = buyEl(doc, "div", "make-left-form");
    if (walk.stage === "price") {
      const label = buyEl(doc, "label", "", walk.question);
      const input = buyEl(doc, "input");
      Object.assign(input, { name: "paid", inputMode: "decimal", autocomplete: "off", value: walk.amount });
      input.setAttribute("aria-label", walk.question);
      input.setAttribute("style", "max-width: 9em; min-height: 44px; box-sizing: border-box;");
      label.append(input);
      panel.append(label);
      row.append(tap("Save", "save", () => onWalk("save", { amount: input.value })),
        tap("Skip", "skip", () => onWalk("skip")));
    } else {
      row.append(tap("It matches", "matches", () => onWalk("matches")),
        tap("Something differs", "differs", () => onWalk("differs")),
        tap("Stop", "stop", () => onWalk("stop")));
    }
    panel.append(row);
    box.append(panel);
  }
  box.append(message);
  return box;
}

// "Paste picks from a Claude thread": [Preview] checks the block without saving it,
// [Save] records it. preview(text) answers { summary, lines }; save(text) records.
function buyPasteTray(doc, { preview, save }) {
  const tray = buyEl(doc, "details", "optional-details buy-paste");
  tray.append(buyEl(doc, "summary", "", "Paste picks from a Claude thread"));
  const text = buyEl(doc, "textarea");
  Object.assign(text, { rows: 6, spellcheck: false });
  text.setAttribute("aria-label", "LABPICKS/1 block from a Claude thread");
  text.setAttribute("style", "width: 100%; max-width: 100%; box-sizing: border-box;");
  const buttons = buyEl(doc, "div", "make-left-form");
  const show = buyButton(doc, "Preview");
  const keep = buyButton(doc, "Save");
  buttons.append(show, keep);
  const message = buyEl(doc, "p", "make-left-message");
  message.setAttribute("role", "status");
  const lines = buyEl(doc, "ul", "make-rows");
  tray.append(text, buttons, message, lines);
  const run = async (action) => {
    const pasted = String(text.value || "");
    lines.replaceChildren();
    if (!pasted.trim()) {
      message.textContent = "Paste the LABPICKS/1 block first.";
      return;
    }
    show.disabled = true;
    keep.disabled = true;
    message.textContent = action === "preview" ? "Checking…" : "Saving…";
    try {
      if (action === "preview") {
        const view = await preview(pasted);
        message.textContent = `${view.summary}:`;
        for (const line of view.lines) lines.append(buyEl(doc, "li", "make-row", line));
      } else {
        await save(pasted);
        text.value = "";
        message.textContent = "Saved.";
      }
    } catch (error) {
      message.textContent = `${action === "preview" ? "Can't read it" : "Not saved"}: ${error?.message || error}`;
    } finally {
      show.disabled = false;
      keep.disabled = false;
    }
  };
  show.addEventListener("click", () => run("preview"));
  keep.addEventListener("click", () => run("save"));
  return tray;
}

// The bar's contents from buyBarView: totals, shipping, budget, then [I ordered these] per shop.
function buyBarFill(doc, bar, view, onOrdered) {
  bar.replaceChildren();
  bar.hidden = !view;
  if (!view) return;
  bar.append(buyEl(doc, "strong", "make-total", view.totals));
  if (view.shipping) bar.append(buyEl(doc, "span", "", view.shipping));
  if (view.budget) bar.append(buyEl(doc, "span", "make-verdict", view.budget));
  const message = buyEl(doc, "p", "make-left-message");
  message.setAttribute("role", "status");
  for (const { shop, count } of view.shops) {
    const line = buyEl(doc, "div", "make-left-form");
    const button = buyButton(doc, "I ordered these");
    button.setAttribute("style", "min-height: 44px;");
    button.setAttribute("aria-label", `I ordered these ${count} from ${shop}`);
    button.addEventListener("click", async () => {
      button.disabled = true;
      message.textContent = "Saving…";
      try {
        await onOrdered(shop);
      } catch (error) {
        message.textContent = `Not saved: ${error?.message || error}`;
        button.disabled = false;
      }
    });
    line.append(buyEl(doc, "span", "", `${shop}: ${count} ticked`), button);
    bar.append(line);
  }
  bar.append(message);
}

function buyLocalDay(now = new Date()) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function buyRandomHex() {
  const bytes = new Uint8Array(3);
  globalThis.crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

// openStockAdd(prefill, { onAdded, onClosed }) opens the Stock page's add form
// (lab/stock.js openInventoryAddition); showPage() brings the Buy page back.
function attachBuyList({ doc, root, request, notify = () => {}, openStockAdd = null, showPage = () => {} }) {
  // Ticks live in page memory only and outlast a reload for offers still listed.
  // walk: the "It arrived" walk in progress (buyWalkStart), page memory only.
  const view = { data: null, loading: null, ticks: new Map(), walk: null };
  const status = root.querySelector("#buy-status");
  const content = root.querySelector("#buy-content");

  async function post(body) {
    return request("/v2/workbench/buy-events", { method: "POST", body: JSON.stringify(body) });
  }

  async function saveRate(rate) {
    await post({ events: [{ kind: "fx_rate", rate, pair: "USD/THB" }] });
    notify(`Saved: 1 US$ = ${rate} ฿.`);
    await load();
  }

  async function saveBudget(entry) {
    await post({ events: [entry] });
    notify(entry.clear ? "Budget cleared." : `Saved: budget ${buyThbText(entry.amount_thb)}.`);
    await load();
  }

  async function onAnswer(materialKey, offer, answer) {
    await post({ events: [buyMatchEvent(materialKey, offer, answer)] });
    if (answer === "SAME") view.ticks = buyTick(view.ticks, materialKey, offer.offer_key, true);
    notify(answer === "SAME" ? `Saved: ${offer.title} is your material.` : `Saved: ${offer.title} is a different material.`);
    await load();
  }

  async function ordered(shop) {
    const events = buyOrderEvents(view.data, view.ticks, shop, buyOrderId(shop, buyLocalDay(), buyRandomHex()));
    await post({ events });
    for (const entry of events) view.ticks = buyTick(view.ticks, entry.material_key, entry.offer_key, false);
    notify(`Saved: ${buyCount(events.length, "line")} ordered from ${shop}.`);
    await load();
  }

  async function postOrders(events, saved) {
    await post({ events });
    notify(saved);
    await load();
  }

  // The Stock page's add form for one line; onAdded runs after Kenny's Add succeeds.
  // Only Arrived and Already have it write stock, and only through the Stock routes.
  function addToStock(group, line, { onAdded, onClosed = () => {} }) {
    if (typeof openStockAdd !== "function") throw new Error("the Stock page's add form is not loaded");
    openStockAdd(buyStockPrefill(group, line), {
      onAdded: (added) => {
        showPage();
        Promise.resolve(onAdded(added)).catch((error) => notify(`Not saved: ${error?.message || error}`, true));
      },
      onClosed: () => {
        onClosed();
        showPage();
      },
    });
  }

  async function onWay(action, group, line) {
    if (action === "still-coming") {
      await postOrders(buyGroupStateEvents(group, "STILL_COMING"), `Saved: your ${group.shop} parcel is still coming.`);
    } else if (action === "didnt-come-all") {
      await postOrders(buyGroupStateEvents(group, "DIDNT_COME"), `Saved: your ${group.shop} parcel didn't come. Back on Buy first.`);
    } else if (action === "didnt-come") {
      await postOrders([buyOrderStateEvent(group, line, "DIDNT_COME")], `Saved: ${line.material} didn't come. Back on Buy first.`);
    } else if (action === "already-have") {
      addToStock(group, line, {
        onAdded: () => postOrders([buyOrderStateEvent(group, line, "ALREADY_HAVE")], `Saved: you already have ${line.material}.`),
      });
    } else if (action === "arrived") {
      view.walk = buyWalkStart(group);
      render();
    }
  }

  async function onWalk(answer, detail = {}) {
    const step = buyWalkLine(view.data, view.walk);
    if (!step || answer === "stop") {
      view.walk = null;
      render();
      return;
    }
    const { group, line } = step;
    if (answer === "differs") {
      await post({ events: [buyOrderStateEvent(group, line, "NOT_THIS")] });
      view.walk = buyWalkNext(view.walk, "differs");
      notify(`Saved: not this ${line.material}. Back on Buy first.`);
      await load();
    } else if (answer === "matches") {
      view.walk = buyWalkNext(view.walk, "matches", { line });
      render();
      const walk = view.walk;
      addToStock(group, line, {
        onAdded: ({ stock_id: stockId }) => {
          if (view.walk !== walk) return;
          view.walk = buyWalkNext(walk, "added", { stockId });
          render();
        },
        onClosed: () => {
          if (view.walk !== walk) return;
          view.walk = buyWalkNext(walk, "closed");
          render();
        },
      });
    } else if (answer === "save" || answer === "skip") {
      if (answer === "save") {
        const body = buyStockPriceBody(view.walk.stockId, group, line, detail.amount);
        if (!body) throw new Error("type what you paid, such as 37.40");
        await request("/v2/workbench/stock-prices", { method: "POST", body: JSON.stringify(body) });
      }
      await post({ events: [buyOrderStateEvent(group, line, "ARRIVED")] });
      view.walk = buyWalkNext(view.walk, answer === "save" ? "saved" : "skipped");
      notify(`Saved: ${line.material} arrived.`);
      await load();
    }
  }

  // The bar sits after the panel, sticky at the foot of the screen: it stays in the
  // page flow, so at the bottom of the page it sits below the last row, not over it.
  const bar = buyEl(doc, "div", "panel buy-bar");
  bar.hidden = true;
  bar.setAttribute("role", "region");
  bar.setAttribute("aria-label", "Ticked to buy");
  bar.setAttribute("style", "position: sticky; bottom: 0; z-index: 4; display: grid; gap: 4px; max-width: 100%; "
    + "box-sizing: border-box; margin: 12px 0 0; padding: 10px 14px; overflow: visible; overflow-wrap: anywhere;");
  root.append(bar);

  const tray = buyPasteTray(doc, {
    preview: async (text) => buyPicksPreview(await post({ labpicks: text, dry_run: true }), buyMaterialNames(view.data)),
    save: async (text) => {
      const saved = await post({ labpicks: text, dry_run: false });
      notify(`Saved ${saved.count} from the pasted block.`);
      await load();
    },
  });
  content.after(tray);

  function showBar() {
    buyBarFill(doc, bar, view.data ? buyBarView(view.data, view.ticks) : null, ordered);
  }

  function onTick(materialKey, offerKey, checked) {
    view.ticks = buyTick(view.ticks, materialKey, offerKey, checked);
    for (const box of content.querySelectorAll(".buy-tick input")) {
      box.checked = view.ticks.get(box.dataset.materialKey) === box.dataset.offerKey;
    }
    showBar();
  }

  function render() {
    if (!view.data) return;
    // The walk ends when its order has no line left on the way.
    if (view.walk && !buyWalkLine(view.data, view.walk)) view.walk = null;
    buyRender(doc, content, view.data, { saveRate, saveBudget, ticks: view.ticks, onTick, onAnswer, onWay, onWalk, walk: view.walk });
    showBar();
  }

  async function load() {
    status.textContent = "Reading what your cards need…";
    try {
      view.data = await request("/v2/workbench/buy-list");
      view.ticks = buyKeepTicks(view.data, view.ticks);
      status.textContent = "";
      render();
    } catch (error) {
      status.textContent = `Could not read the buy list: ${error?.message || error}`;
    }
  }

  root.querySelector("#buy-refresh").addEventListener("click", load);

  return {
    // The page is shown: read the list once; Refresh reads it again.
    shown() {
      if (!view.data && !view.loading) view.loading = load().finally(() => { view.loading = null; });
    },
    changed: render,
  };
}

if (typeof module === "object" && module.exports) {
  module.exports = {
    buyRound, buyThbText, buyUsdText, buyBottleThbText, buyBottleRangeText, buyDayLabel, buyRateBannerText,
    buyShownPriceText, buyOfferView, buyRowView, buyPickText, buyOrderLineText, buyRender,
    buyDecimalSum, buyDecimalTimes, buyDecimalCompare, buyTick, buyTicked, buyKeepTicks, buyBarView,
    buyOrderId, buyOrderEvents, buyMatchEvent, buyBudgetEvent, buyMaterialNames, buyPicksPreview,
    BUY_CHECK_STOCK_TEXT, BUY_PW_SHIPPING_USD, BUY_PW_FREE_SHIPPING_FROM_USD,
    buyOrderStateEvent, buyGroupStateEvents, buyPackGrams, buyPercentText, buyStockPrefill, buyPaidQuestion,
    buyStockPriceBody, buyWalkStart, buyWalkLine, buyWalkNext, buyWalkView, buyGroupNode, buyRateChange,
  };
}
