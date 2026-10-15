// Buy: what the saved cards need and the stock lists don't own, priced from
// PerfumersWorld list prices (GET /v2/workbench/buy-list, schema workbench-buy-list-v1,
// built by engine/buy_list.py). Read only, except the US$ rate, saved as an fx_rate
// buy event (POST /v2/workbench/buy-events) before the page data is read again.
//
// Money arrives as unrounded decimal strings and is rounded here on the digits
// (BigInt), never through floats. Shop titles, card names and every other text go in
// through textContent only, never HTML strings. lab/stock.js attaches it; node loads
// the same file in the tests.

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

function buyOfferNode(doc, view) {
  const box = buyEl(doc, "li", "make-row buy-offer");
  box.dataset.offerKey = view.offerKey;
  const head = buyEl(doc, "div", "make-card-head");
  head.append(buyEl(doc, "strong", "", view.head));
  if (view.tickable) {
    // T5b puts the tick box here.
    const tick = buyEl(doc, "span", "buy-tick");
    tick.dataset.offerKey = view.offerKey;
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
  if (view.question) box.append(buyEl(doc, "p", "field-help", view.question));
  return box;
}

function buyRowNode(doc, row) {
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
    for (const offer of view.offers) offers.append(buyOfferNode(doc, offer));
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

// Draw the whole page into `target` from the buy-list payload.
function buyRender(doc, target, data, { saveRate = async () => {} } = {}) {
  target.replaceChildren();
  target.append(buyEl(doc, "p", "make-shopping-for", data.price_header || ""));
  if (data.rate_banner) target.append(buyRateForm(doc, data.rate_banner, saveRate));
  if (data.budget?.amount_thb) target.append(buyEl(doc, "p", "field-help", `Budget: ${buyThbText(data.budget.amount_thb)}`));

  const first = buySection(doc, "Buy first", "from your cards and stock");
  const rows = data.buy_first || [];
  if (!rows.length) first.append(buyEl(doc, "p", "make-verdict", "Nothing on your saved cards is missing from your stock."));
  for (const row of rows) first.append(buyRowNode(doc, row));
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

function attachBuyList({ doc, root, request, notify = () => {} }) {
  const view = { data: null, loading: null };
  const status = root.querySelector("#buy-status");
  const content = root.querySelector("#buy-content");

  async function saveRate(rate) {
    await request("/v2/workbench/buy-events", {
      method: "POST",
      body: JSON.stringify({ events: [{ kind: "fx_rate", rate, pair: "USD/THB" }] }),
    });
    notify(`Saved: 1 US$ = ${rate} ฿.`);
    await load();
  }

  function render() {
    if (!view.data) return;
    buyRender(doc, content, view.data, { saveRate });
  }

  async function load() {
    status.textContent = "Reading what your cards need…";
    try {
      view.data = await request("/v2/workbench/buy-list");
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
    BUY_CHECK_STOCK_TEXT,
  };
}
