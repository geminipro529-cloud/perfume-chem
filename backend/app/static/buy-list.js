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
  return `${pick.material}, ${pick.dose}: ${String(pick.reason || "").replace(/\.$/, "")}.${reviewed}`;
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

// After the data is read again: keep the ticks whose offers are still there.
function buyKeepTicks(data, ticks) {
  return new Map(buyTicked(data, ticks).map((entry) => [entry.materialKey, entry.offer.offer_key]));
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
function buyRender(doc, target, data, {
  saveRate = async () => {}, saveBudget = async () => {}, ticks = new Map(), onTick = () => {}, onAnswer = async () => {},
} = {}) {
  target.replaceChildren();
  target.append(buyEl(doc, "p", "make-shopping-for", data.price_header || ""));
  if (data.rate_banner) target.append(buyRateForm(doc, data.rate_banner, saveRate));
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
    for (const group of data.on_the_way) {
      const box = buyEl(doc, "div", "make-ask");
      box.append(buyEl(doc, "h3", "", `${group.shop}, ordered ${buyDayLabel(group.ordered_on)}`));
      if (group.nudge) box.append(buyEl(doc, "p", "make-verdict", group.nudge_text));
      const lines = buyEl(doc, "ul", "make-rows");
      for (const line of group.lines || []) lines.append(buyEl(doc, "li", "make-row", buyOrderLineText(line)));
      box.append(lines);
      way.append(box);
    }
    target.append(way);
  }
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

function attachBuyList({ doc, root, request, notify = () => {} }) {
  // Ticks live in page memory only and outlast a reload for offers still listed.
  const view = { data: null, loading: null, ticks: new Map() };
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
    buyRender(doc, content, view.data, { saveRate, saveBudget, ticks: view.ticks, onTick, onAnswer });
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
  };
}
