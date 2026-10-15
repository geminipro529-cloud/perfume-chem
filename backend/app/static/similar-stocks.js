// "Similar you own" and the shelf map (plan item F6): owned stocks whose written
// character is close to another one (POST /v2/workbench/similar-stocks), and every
// owned material placed by character (GET /v2/workbench/shelf-map). Both compare
// the profiles written for each stock, never smell, so every list says "similar,
// not the same".
//
// Edit a formula previews a swap from the list; What can I make lists it beside a
// stock that runs short; the Stock page draws the map. Names and text go in through
// textContent only, never HTML strings. Node loads the same file in the tests.

const SIMILAR_LABEL = "similar, not the same";
const SIMILAR_SVG = "http://www.w3.org/2000/svg";
// A facet led by this many materials or fewer is thin on the shelf.
const SHELF_THIN_MAX = 5;

function similarJoin(words) {
  const list = (words || []).map(String).filter(Boolean);
  if (list.length < 2) return list.join("");
  return `${list.slice(0, -1).join(", ")} and ${list[list.length - 1]}`;
}

// One material's line: what the two profiles share and where they differ.
function similarLineText(item) {
  const parts = [];
  if (item?.shares?.length) parts.push(`Both ${similarJoin(item.shares)}`);
  if (item?.differs?.length) parts.push(item.differs.join(", "));
  let text = parts.length ? `${parts.join("; ")}.` : "";
  if (item?.profile_from_category) text = `${text}${text ? " " : ""}Its profile is only its category's.`;
  if (text) text = `${text[0].toUpperCase()}${text.slice(1)}`;
  return text;
}

function similarClosenessText(item) {
  return item?.closeness === "close" ? "Close" : "Some likeness";
}

// What a list shows, as plain data. `choice(line)` says how one stock fits:
// { label, stockId } to offer it, { label, why } to say why not, or null to leave it out.
function similarView(answer, choice) {
  const fit = (lines) => (lines || []).map((line) => (choice ? choice(line) : { label: String(line.stock_label || ""), why: "" }))
    .filter(Boolean);
  const name = String(answer?.stock?.identity_name || "");
  let empty = "";
  if (answer?.no_profile) empty = `${name || "This stock"} has no written character in the Lab yet, so nothing can be compared with it.`;
  else if (!(answer?.similar || []).length) empty = "Nothing else on your shelf is written alike enough.";
  return {
    name,
    basis: String(answer?.basis || ""),
    label: String(answer?.label || SIMILAR_LABEL),
    same: fit(answer?.same_material),
    similar: (answer?.similar || []).map((item) => ({
      name: String(item.identity_name || ""),
      closeness: similarClosenessText(item),
      line: similarLineText(item),
      stocks: fit(item.stocks),
    })),
    empty,
  };
}

function similarNode(doc, tag, text = "", className = "") {
  const node = doc.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  return node;
}

// One stock under a material: a button to pick it when `pick` names the action, else its label.
function similarStockNode(doc, stock, pick) {
  if (pick && stock.stockId) {
    const button = similarNode(doc, "button", stock.label, "quiet-button similar-pick");
    button.type = "button";
    button.dataset.similarStock = stock.stockId;
    button.setAttribute("aria-label", `${pick} ${stock.label}`);
    return button;
  }
  return similarNode(doc, "span", stock.why ? `${stock.label}: ${stock.why}` : stock.label, "similar-stock");
}

function similarStocksNode(doc, stocks, pick) {
  const box = similarNode(doc, "div", "", "similar-stocks");
  stocks.forEach((stock) => box.append(similarStockNode(doc, stock, pick)));
  return box;
}

// Fills `panel` with the list. `pick` is the word before a stock's name on its
// button ("Preview"); without it the stocks are named, not offered.
function renderSimilarList(panel, answer, { choice = null, pick = "" } = {}) {
  const doc = panel.ownerDocument;
  const view = similarView(answer, choice);
  const nodes = [];
  if (view.same.length) {
    nodes.push(similarNode(doc, "h4", "Your other bottles of it"));
    nodes.push(similarStocksNode(doc, view.same, pick));
  }
  nodes.push(similarNode(doc, "h4", `${view.label[0].toUpperCase()}${view.label.slice(1)}`));
  if (view.empty) nodes.push(similarNode(doc, "p", view.empty, "similar-empty"));
  if (view.similar.length) {
    const list = similarNode(doc, "ul", "", "similar-items");
    view.similar.forEach((item) => {
      const li = similarNode(doc, "li", "", "similar-item");
      const head = similarNode(doc, "p", "", "similar-head");
      head.append(similarNode(doc, "strong", item.name), " ", similarNode(doc, "span", item.closeness, "similar-closeness"));
      li.append(head);
      if (item.line) li.append(similarNode(doc, "p", item.line, "similar-line"));
      if (item.stocks.length) li.append(similarStocksNode(doc, item.stocks, pick));
      list.append(li);
    });
    nodes.push(list);
  }
  if (view.basis) nodes.push(similarNode(doc, "p", view.basis, "field-help"));
  panel.replaceChildren(...nodes);
  return view;
}

// The shelf map as plain data: dots in a square of `size`, the thin facets and
// the pairs written alike.
function shelfView(answer, size = 300) {
  const pad = 12;
  const span = size - 2 * pad;
  const dots = (answer?.stocks || []).map((dot) => ({
    name: String(dot.identity_name || ""),
    x: Math.round((pad + Number(dot.x) * span) * 10) / 10,
    y: Math.round((pad + (1 - Number(dot.y)) * span) * 10) / 10,
    leads: String(dot.leads_with_word || ""),
    facet: String(dot.leads_with || ""),
    fromCategory: Boolean(dot.profile_from_category),
  }));
  const facets = (answer?.facets || []).map((facet) => ({
    facet: String(facet.facet || ""),
    word: String(facet.word || facet.facet || ""),
    count: Number(facet.count) || 0,
    leaders: (facet.leaders || []).map(String),
  }));
  return {
    dots,
    thin: facets.filter((facet) => facet.count <= SHELF_THIN_MAX).sort((a, b) => a.count - b.count || a.word.localeCompare(b.word)),
    facets,
    alike: (answer?.written_alike || []).map((pair) => ({
      a: String(pair.a || ""), b: String(pair.b || ""), shares: (pair.shares || []).map(String),
    })),
    unplaced: (answer?.unplaced || []).map(String),
    axes: shelfAxesText(answer?.axes),
    basis: String(answer?.basis || ""),
  };
}

// What the map's two directions mean, from the facet each runs towards.
function shelfAxesText(axes) {
  const x = axes?.x;
  const y = axes?.y;
  if (!x?.low || !x?.high || !y?.low || !y?.high) return "";
  return `Left to right: more ${x.low} to more ${x.high}. Bottom to top: more ${y.low} to more ${y.high}.`;
}

function shelfThinText(facet) {
  if (!facet.count) return `${facet.word}: none of your materials leads with it.`;
  return `${facet.word}: only ${similarJoin(facet.leaders)}.`;
}

function shelfAlikeText(pair) {
  return `${pair.a} and ${pair.b}${pair.shares.length ? `: both ${similarJoin(pair.shares)}` : ""}.`;
}

// Fills `panel` with the map (an SVG whose dots name their material), a field to
// find a material on it, the thin facets, the pairs written alike and what has no
// profile to place.
function renderShelfMap(panel, answer) {
  const doc = panel.ownerDocument;
  const view = shelfView(answer);
  const nodes = [];
  const svg = doc.createElementNS(SIMILAR_SVG, "svg");
  svg.setAttribute("viewBox", "0 0 300 300");
  svg.setAttribute("class", "shelf-svg");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", `${view.dots.length} materials placed by their written character. Close dots are written alike.`);
  const circles = new Map();
  view.dots.forEach((dot) => {
    const circle = doc.createElementNS(SIMILAR_SVG, "circle");
    circle.setAttribute("cx", String(dot.x));
    circle.setAttribute("cy", String(dot.y));
    circle.setAttribute("r", "4");
    circle.setAttribute("class", "shelf-dot");
    const title = doc.createElementNS(SIMILAR_SVG, "title");
    title.textContent = dot.leads ? `${dot.name}, leads with ${dot.leads}` : dot.name;
    circle.append(title);
    svg.append(circle);
    circles.set(dot.name.toLowerCase(), { circle, dot });
  });
  nodes.push(svg);
  if (view.axes) nodes.push(similarNode(doc, "p", view.axes, "shelf-axes"));
  const find = similarNode(doc, "label", "Find a material on the map", "shelf-find");
  const input = doc.createElement("input");
  input.type = "search";
  input.autocomplete = "off";
  const listId = `${panel.id || "shelf"}-names`;
  input.setAttribute("list", listId);
  const names = doc.createElement("datalist");
  names.id = listId;
  view.dots.forEach((dot) => names.append(Object.assign(doc.createElement("option"), { value: dot.name })));
  find.append(input, names);
  const found = similarNode(doc, "p", "", "shelf-found");
  found.setAttribute("aria-live", "polite");
  let marked = null;
  input.addEventListener("input", () => {
    const hit = circles.get(input.value.trim().toLowerCase());
    if (marked) {
      marked.setAttribute("r", "4");
      marked.classList.remove("is-found");
    }
    marked = hit ? hit.circle : null;
    if (hit) {
      hit.circle.setAttribute("r", "8");
      hit.circle.classList.add("is-found");
      svg.append(hit.circle);
    }
    found.textContent = hit ? `${hit.dot.name} is the ringed dot${hit.dot.leads ? `; it leads with ${hit.dot.leads}` : ""}.` : "";
  });
  nodes.push(find, found);
  nodes.push(similarNode(doc, "p", view.basis, "field-help"));
  nodes.push(similarNode(doc, "h4", "Thin on your shelf"));
  const thin = similarNode(doc, "ul", "", "shelf-list");
  view.thin.forEach((facet) => thin.append(similarNode(doc, "li", shelfThinText(facet))));
  if (!view.thin.length) thin.append(similarNode(doc, "li", `Every main facet is led by more than ${SHELF_THIN_MAX} of your materials.`));
  nodes.push(thin);
  const alike = similarNode(doc, "details", "", "shelf-more");
  alike.append(similarNode(doc, "summary", `Written almost alike (${view.alike.length})`));
  const pairs = similarNode(doc, "ul", "", "shelf-list");
  view.alike.forEach((pair) => pairs.append(similarNode(doc, "li", shelfAlikeText(pair))));
  if (!view.alike.length) pairs.append(similarNode(doc, "li", "No two materials are written almost alike."));
  alike.append(pairs);
  if (view.alike.length) {
    alike.append(similarNode(doc, "p", "The Lab cannot tell these apart; your nose can. If two do smell alike, one may be enough.", "field-help"));
  }
  nodes.push(alike);
  if (view.unplaced.length) {
    const unplaced = similarNode(doc, "details", "", "shelf-more");
    unplaced.append(similarNode(doc, "summary", `No written character yet (${view.unplaced.length})`));
    unplaced.append(similarNode(doc, "p", `${similarJoin(view.unplaced)}.`, "shelf-unplaced"));
    nodes.push(unplaced);
  }
  panel.replaceChildren(...nodes);
  return view;
}

if (typeof module === "object" && module.exports) {
  module.exports = {
    SIMILAR_LABEL, SHELF_THIN_MAX, similarJoin, similarLineText, similarClosenessText, similarView,
    shelfView, shelfAxesText, shelfThinText, shelfAlikeText,
  };
}
