"""Buy: money from decimal strings, the rate banner, offers and plain-text rendering (node)."""

import json
from pathlib import Path

from tests.integration.test_lab_ui import _node_json

BUY_LIST_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "buy-list.js"

# A tiny document: text goes out escaped, anything set through innerHTML goes out raw.
FAKE_DOC = """
const esc = (v) => String(v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
class Node {
  constructor(tag) { this.tag = tag; this.children = []; this.attrs = {}; this.dataset = {}; this.text = null; this.raw = null; }
  set textContent(v) { this.text = String(v); this.children = []; }
  set innerHTML(v) { this.raw = String(v); this.children = []; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren() { this.children = []; }
  setAttribute(k, v) { this.attrs[k] = v; }
  addEventListener() {}
  focus() {}
  html() {
    const inner = this.raw !== null ? this.raw : this.text !== null ? esc(this.text) : this.children.map((c) => c.html()).join("");
    const href = this.href ? ` href="${esc(this.href)}" target="${this.target}" rel="${this.rel}"` : "";
    const tick = this.className === "buy-tick" ? " data-tick" : "";
    return `<${this.tag}${href}${tick}>${inner}</${this.tag}>`;
  }
}
const doc = { createElement: (tag) => new Node(tag) };
"""

OFFER = {
    "offer_key": "pw:3SW00003", "shop": "PW", "sku": "3SW00003", "title": "Sandalwood Oil", "form": "neat",
    "usd_per_g": "7.3", "observed_on": "2026-04-11", "observed_label": "11 Apr",
    "product_url": "https://www.perfumersworld.com/view.php?pro_id=3SW00003", "match": "probable",
    "match_question": "Is PW 3SW00003 'Sandalwood Oil' your Sandalwood Oil?", "previous_title": None,
    "tickable": True, "default_pack_g": "5", "upfront_usd": "37.40", "upfront_thb": "1254.77",
    "cost_per_bottle_thb": {"min": "29.3898", "max": "35.2"}, "last_not_this_on": None,
}
UNKNOWN = {
    **OFFER, "offer_key": "pw:4JD02734", "sku": "4JD02734", "title": "Jasmine Lactone", "match": "unknown",
    "match_question": None, "tickable": False, "usd_per_g": None, "upfront_usd": None, "upfront_thb": None,
    "cost_per_bottle_thb": None,
}


def _run(body):
    return _node_json(BUY_LIST_JS, f"(m) => {{ {FAKE_DOC} {body} }}")


def test_money_rounds_half_up_from_the_digits():
    result = _run("""
        return {
          thb: ["29.3898", "1254.77", "1254.5", "1254.49", "0.5", "1234567.5", "nope"].map(m.buyThbText),
          bottle: ["2.44", "2.45", "2.04", "9.96", "29.3898", "0.05"].map(m.buyBottleThbText),
          usd: ["7.3", "37.4", "10.905", "0.004", "1234.5"].map(m.buyUsdText),
          range: m.buyBottleRangeText({ min: "29.3898", max: "35.2" }),
          same: m.buyBottleRangeText({ min: "29.3", max: "29.4" }),
          small: m.buyBottleRangeText({ min: "2.44", max: "2.44" }),
          none: m.buyBottleRangeText(null),
          drift: m.buyRound("1.005", 2),
        };
    """)

    assert result["thb"] == ["฿29", "฿1,255", "฿1,255", "฿1,254", "฿1", "฿1,234,568", ""]
    assert result["bottle"] == ["฿2.4", "฿2.5", "฿2", "฿10", "฿29", "฿0.1"]
    assert result["usd"] == ["US$7.30", "US$37.40", "US$10.91", "US$0.00", "US$1,234.50"]
    assert result["range"] == "฿29 to ฿35 a bottle"
    assert result["same"] == "฿29 a bottle"
    assert result["small"] == "฿2.4 a bottle"
    assert result["none"] == ""
    # A float would give 1.00 here.
    assert result["drift"] == "1.01"


def test_rate_banner_says_missing_or_names_the_last_date():
    result = _run("""
        return [m.buyRateBannerText({ reason: "missing" }),
                m.buyRateBannerText({ reason: "stale", last_set_on: "2026-10-09" }),
                m.buyRateBannerText(null)];
    """)

    assert result == ["No US$ rate yet.", "No US$ rate since 9 Oct.", ""]


def test_a_known_offer_shows_its_prices_and_an_unknown_one_none():
    result = _run(f"""
        return [m.buyOfferView({OFFER!r}, "Sandalwood Oil"), m.buyOfferView({UNKNOWN!r}, "Jasmine Lactone")];
    """.replace("None", "null").replace("True", "true").replace("False", "false"))
    known, unknown = result

    assert known["head"] == "PW 3SW00003"
    assert known["perG"] == "US$7.30/g, 11 Apr"
    assert known["upfront"] == "5 g: US$37.40, ฿1,255"
    assert known["bottle"] == "฿29 to ฿35 a bottle"
    assert known["question"] == "Is PW 3SW00003 'Sandalwood Oil' your Sandalwood Oil?"
    assert known["linkText"] == "Open on PW"
    assert known["tickable"] is True
    for field in ("perG", "upfront", "bottle", "question"):
        assert unknown[field] == "", field
    assert "฿" not in str(unknown) and "US$" not in str(unknown)
    assert unknown["tickable"] is False


def test_the_page_renders_shop_and_card_text_as_text():
    hostile = "<script>alert(1)</script>"
    page = {
        "price_header": "PW list prices from 11 Apr. Check on PW before ordering.",
        "rate_banner": {"reason": "missing"},
        "budget": None,
        "buy_first": [{
            "material_key": "x", "material": hostile, "need_count": 1, "pick_tier": 1,
            "cards": [{"formula_id": "f", "name": "<b>Card</b>", "cost_per_bottle_thb": "2.44"}],
            "similar": [], "returned_from_order": {"shop": "PW", "state": "DIDNT_COME"},
            "offers": [{**OFFER, "title": hostile}, UNKNOWN],
        }],
        "check_stock": [{"material": hostile, "cards": [{"name": "Iris"}], "reason": "lists differ"}],
        "unreadable": [{"name": "Broken <i>card</i>"}],
        "tiers": {"1": [{"material": hostile, "dose": "2%", "reason": "why", "reviewed_on": "2026-10-15",
                         "price": {"amount": "450", "currency": "THB", "pack": "10 g", "observed_on": "2026-10-14"}}],
                  "2": [], "3": {"note": "needs fresh shop prices"}},
        "skip": [{"material": hostile, "reason": "not now"}],
        "on_the_way": [{"shop": "PW", "ordered_on": "2026-10-10", "nudge": False, "lines": [
            {"material": hostile, "pack": "5 g", "state": "ORDERED",
             "shown_price": {"amount": "50.9", "currency": "USD", "observed_on": "2026-04-11"}}]}],
    }
    html = _run(f"""
        const target = doc.createElement("div");
        m.buyRender(doc, target, {json.dumps(page)});
        const empty = doc.createElement("div");
        m.buyRender(doc, empty, {{ price_header: "h", rate_banner: null, buy_first: [], tiers: {{}} }});
        return {{ page: target.html(), empty: empty.html() }};
    """)
    text = html["page"]

    assert "<script>" not in text and "<b>" not in text and "<i>" not in text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in text
    assert text.startswith("<div><p>PW list prices from 11 Apr.")
    assert "No US$ rate yet." in text
    assert "needed by 1 card" in text and "&lt;b&gt;Card&lt;/b&gt;: ฿2.4 a bottle" in text
    assert "Back from your PW order" in text and "Tier 1" in text
    assert text.count("data-tick") == 1
    assert 'target="_blank" rel="noopener"' in text and ">Open on PW<" in text
    assert "counts it neither as owned nor as not owned" in text
    assert "Couldn&#39;t read: Broken &lt;i&gt;card&lt;/i&gt;." in text
    assert "2%: why. Reviewed 15 Oct; ฿450 for 10 g, 14 Oct." in text
    assert "needs fresh shop prices" in text and "not now" in text
    assert "PW, ordered 10 Oct" in text and "5 g, US$50.90, 11 Apr" in text
    assert "Nothing on your saved cards is missing from your stock." in html["empty"]


# ---- T5b: ticks, the total bar, orders, the match answer and the paste tray ----

def _offer(key, usd, thb, **extra):
    return {**OFFER, "offer_key": f"pw:{key}", "sku": key, "title": f"Title {key}", "match": "confirmed",
            "match_question": None, "upfront_usd": usd, "upfront_thb": thb, **extra}


def _page(rate, offers_by_material, budget=None):
    rows = [{"material_key": key, "material": key.title(), "need_count": 1, "cards": [], "similar": [],
             "offers": offers} for key, offers in offers_by_material.items()]
    return {"price_header": "h", "rate_banner": None, "fx": {"rate": rate, "set_at": "x", "stale": False} if rate else None,
            "budget": {"amount_thb": budget} if budget else None, "buy_first": rows, "tiers": {}}


def _bar(page, ticks):
    return _run(f"const ticks = new Map({json.dumps(ticks)}); return m.buyBarView({json.dumps(page)}, ticks);")


def test_ticking_keeps_one_offer_per_material_and_untickable_offers_get_no_box():
    first, second = _offer("A1", "37.40", "1254.77"), _offer("A2", "20", "671")
    probable = {**_offer("B1", "4.80", "161.04"), "match": "probable", "match_question": "Is PW B1 'Title B1' your Basil?"}
    page = _page("33.55", {"amber": [first, second, UNKNOWN], "basil": [probable]})
    result = _run(f"""
        const page = {json.dumps(page)};
        let ticks = m.buyTick(new Map(), "amber", "pw:A1", true);
        ticks = m.buyTick(ticks, "amber", "pw:A2", true);
        const swapped = Object.fromEntries(ticks);
        const stale = m.buyTick(ticks, "amber", "pw:A1", false);
        const unticked = m.buyTick(ticks, "amber", "pw:A2", false);
        const reloaded = m.buyKeepTicks({{ ...page, buy_first: [{{ ...page.buy_first[0], offers: [page.buy_first[0].offers[0]] }}] }}, ticks);
        const gone = m.buyKeepTicks(page, new Map([["amber", "pw:4JD02734"], ["basil", "pw:B1"]]));
        const target = doc.createElement("div");
        m.buyRender(doc, target, page, {{ ticks }});
        const all = (node) => [node, ...node.children.flatMap(all)];
        const boxes = all(target).filter((node) => node.type === "checkbox");
        const asks = all(target).filter((node) => node.className === "make-ask buy-match");
        return {{
          swapped, stale: Object.fromEntries(stale), unticked: Object.fromEntries(unticked),
          kept: Object.fromEntries(reloaded), gone: Object.fromEntries(gone),
          boxes: boxes.map((box) => [box.dataset.materialKey, box.dataset.offerKey, box.checked]),
          asks: asks.map((ask) => [ask.hidden, ask.children[0].text]),
        }};
    """)

    assert result["swapped"] == {"amber": "pw:A2"}
    # Unticking an offer that is no longer the ticked one changes nothing.
    assert result["stale"] == {"amber": "pw:A2"}
    assert result["unticked"] == {}
    # A reload drops ticks whose offer is gone and keeps none on an untickable offer.
    assert result["kept"] == {}
    assert result["gone"] == {"basil": "pw:B1"}
    assert result["boxes"] == [["amber", "pw:A1", False], ["amber", "pw:A2", True], ["basil", "pw:B1", False]]
    assert result["asks"] == [[True, "Is PW B1 'Title B1' your Basil?"]]


def test_the_bar_totals_in_baht_with_a_rate_and_in_dollars_without():
    ticks = [["amber", "pw:A1"], ["basil", "pw:B1"], ["cedar", "pw:C1"]]
    with_rate = _page("33.55", {"amber": [_offer("A1", "37.40", "1254.77")], "basil": [_offer("B1", "4.80", "161.04")],
                                "cedar": [_offer("C1", None, None)]}, budget="1600")
    no_rate = _page(None, {"amber": [_offer("A1", "37.40", None)], "basil": [_offer("B1", "4.80", None)],
                           "cedar": [_offer("C1", None, None)]}, budget="1600")

    bar = _bar(with_rate, ticks)
    assert bar["totals"] == "3 ticked, ฿1,416, 1 shop, 1 not priced"
    assert bar["shipping"] == "PW shipping US$30 (฿1,007)"
    assert bar["shops"] == [{"shop": "PW", "count": 3}]

    bare = _bar(no_rate, ticks)
    assert bare["totals"] == "3 ticked, US$42.20, 1 shop, 1 not priced"
    assert bare["shipping"] == "PW shipping US$30"
    assert bare["budget"] == ""
    assert "฿" not in json.dumps(bare, ensure_ascii=False)
    assert _bar(with_rate, []) is None


def test_pw_ships_free_from_150_dollars():
    under = _page("33.55", {"amber": [_offer("A1", "100", "3355")], "basil": [_offer("B1", "49.99", "1677.16")]})
    at = _page("33.55", {"amber": [_offer("A1", "100", "3355")], "basil": [_offer("B1", "50.00", "1677.5")]})
    ticks = [["amber", "pw:A1"], ["basil", "pw:B1"]]

    assert _bar(under, ticks)["shipping"] == "PW shipping US$30 (฿1,007)"
    assert _bar(at, ticks)["shipping"] == "PW ships free"


def test_the_budget_line_counts_shipping_and_says_how_far_over():
    over = _page("33.55", {"amber": [_offer("A1", "37.40", "1254.77")], "basil": [_offer("B1", "4.80", "161.04")]},
                 budget="1600")
    under = _page("33.55", {"amber": [_offer("A1", "160", "5368")]}, budget="6000")
    exact = _page("33.55", {"amber": [_offer("A1", "160", "5368")]}, budget="5368")

    # ฿1,415.81 of goods + ฿1,006.50 PW shipping.
    assert _bar(over, [["amber", "pw:A1"], ["basil", "pw:B1"]])["budget"] == "฿2,422 of your ฿1,600 budget: ฿822 over"
    assert _bar(under, [["amber", "pw:A1"]])["budget"] == "฿5,368 of your ฿6,000 budget"
    assert _bar(exact, [["amber", "pw:A1"]])["budget"] == "฿5,368 of your ฿5,368 budget"
    assert _run("""return [m.buyBudgetEvent("1,600"), m.buyBudgetEvent(null), m.buyBudgetEvent("0"), m.buyBudgetEvent("lots"),
                           m.buyDecimalSum(["0.1", "0.2"]), m.buyDecimalTimes("30", "33.55")];""") == [
        {"kind": "budget", "amount_thb": "1600"}, {"kind": "budget", "clear": True}, None, None, "0.3", "1006.50"]


def test_i_ordered_these_posts_one_order_event_per_ticked_offer_with_one_order_id():
    page = _page("33.55", {"amber": [_offer("A1", "37.40", "1254.77", observed_on="2026-04-11")],
                           "basil": [_offer("B1", "4.80", "161.04", observed_on="2026-04-12", default_pack_g="10")],
                           "cedar": [_offer("C1", "9", "302")]})
    result = _run(f"""
        const id = m.buyOrderId("PW", "2026-10-15", "a1b2c3");
        return {{ id, events: m.buyOrderEvents({json.dumps(page)}, new Map([["amber", "pw:A1"], ["basil", "pw:B1"]]), "PW", id) }};
    """)

    assert result["id"] == "PW-20261015-a1b2c3"
    assert result["events"] == [
        {"kind": "order", "order_id": "PW-20261015-a1b2c3", "shop": "PW", "material_key": "amber", "offer_key": "pw:A1",
         "pack": "5 g", "state": "ORDERED", "shown_price": {"amount": "37.40", "currency": "USD", "observed_on": "2026-04-11"}},
        {"kind": "order", "order_id": "PW-20261015-a1b2c3", "shop": "PW", "material_key": "basil", "offer_key": "pw:B1",
         "pack": "10 g", "state": "ORDERED", "shown_price": {"amount": "4.80", "currency": "USD", "observed_on": "2026-04-12"}},
    ]


def test_same_posts_a_match_event_with_the_title_kenny_saw():
    result = _run(f"return m.buyMatchEvent('sandalwood oil', {json.dumps(OFFER)}, 'SAME');")

    assert result == {"kind": "match", "material_key": "sandalwood oil", "offer_key": "pw:3SW00003", "answer": "SAME",
                      "title_at_confirm": "Sandalwood Oil"}


def test_the_paste_tray_preview_counts_and_lists_a_dry_run():
    response = {"dry_run": True, "count": 3, "entries": [
        {"kind": "pick", "material_key": "nootkatone", "tier": 1, "dose": "2%", "reason": "lifts the grapefruit",
         "decided_by": "Claude", "decided_at": "2026-10-15", "source": "thread"},
        {"kind": "pick", "material_key": "iso e super", "tier": 2, "dose": "10%", "reason": "woody air",
         "decided_by": "Claude", "decided_at": "2026-10-15", "source": "thread"},
        {"kind": "skip", "material_key": "ambrox", "reason": "you own Ambrofix",
         "decided_by": "Claude", "decided_at": "2026-10-15", "source": "thread"},
    ]}
    page = {"buy_first": [{"material_key": "nootkatone", "material": "Nootkatone", "offers": []}], "tiers": {}}
    result = _run(f"""
        return [m.buyPicksPreview({json.dumps(response)}, m.buyMaterialNames({json.dumps(page)})),
                m.buyPicksPreview({{ entries: [{json.dumps(response["entries"][2])}] }}).summary];
    """)

    assert result[0] == {"summary": "2 picks and 1 skip", "lines": [
        "Nootkatone, Tier 1, 2%: lifts the grapefruit",
        "iso e super, Tier 2, 10%: woody air",
        "ambrox, skip: you own Ambrofix",
    ]}
    assert result[1] == "0 picks and 1 skip"


# ---- T6: On the way answers, the "It arrived" walk and the price paid ----

GROUP = {
    "shop": "PW", "order_id": "PW-20261001-a1b2c3", "ordered_on": "2026-10-01", "days": 12, "nudge": True,
    "nudge_text": "PW parcel still on the way?",
    "lines": [
        {"material_key": "sandalwood oil s. album", "material": "Sandalwood oil S. album", "offer_key": "pw:7WX21054",
         "pack": "5 g", "state": "ORDERED", "title": "Sandalwood Oil", "form": "neat", "strength": "1", "solvent": None,
         "shown_price": {"amount": "37.40", "currency": "USD", "observed_on": "2026-04-11"}},
        {"material_key": "orris concrete", "material": "Orris Concrete", "offer_key": "pw:2IR00002", "pack": "10 g",
         "state": "STILL_COMING", "title": "Orris Concrete", "form": "10.0% in DPG", "strength": "0.1", "solvent": "DPG",
         "shown_price": {"amount": "15", "currency": "USD", "observed_on": "2026-04-11"}},
        {"material_key": "vetiver oil", "material": "Vetiver Oil", "offer_key": "pw:9XX99999", "pack": "5 g",
         "state": "ORDERED", "title": None, "form": None, "strength": None, "solvent": None,
         "shown_price": {"amount": "20", "currency": "USD", "observed_on": "2026-04-11"}},
    ],
}


def _group_run(body):
    return _run(f"const group = {json.dumps(GROUP)}; const data = {{ on_the_way: [group] }}; {body}")


def test_the_stock_add_is_prefilled_from_the_order_line():
    result = _group_run("return group.lines.map((line) => m.buyStockPrefill(group, line));")
    common = {"category": "", "supplier_name": "PerfumersWorld", "user_note": "Arrived from PW order PW-20261001-a1b2c3"}

    assert result[0] == {**common, "identity_name": "Sandalwood oil S. album", "supplier_sku": "7WX21054",
                         "fraction_percent_decimal": "100", "fraction_basis": "neat", "carrier": "",
                         "physical_form": "as_supplied", "homogeneity": "NOT_APPLICABLE"}
    assert result[1] == {**common, "identity_name": "Orris Concrete", "supplier_sku": "2IR00002",
                         "fraction_percent_decimal": "10", "fraction_basis": "mass_fraction", "carrier": "DPG",
                         "physical_form": "solution", "homogeneity": ""}
    # An offer the price index doesn't know: Kenny reads the strength off the label.
    assert result[2] == {**common, "identity_name": "Vetiver Oil", "supplier_sku": "9XX99999",
                         "fraction_percent_decimal": "", "fraction_basis": "", "carrier": "",
                         "physical_form": "", "homogeneity": ""}


def test_each_answer_posts_the_exact_order_event():
    result = _group_run("""
        const [santal, orris] = group.lines;
        return {
          still: m.buyGroupStateEvents(group, "STILL_COMING"),
          gone: m.buyOrderStateEvent(group, orris, "DIDNT_COME"),
          notThis: m.buyOrderStateEvent(group, santal, "NOT_THIS"),
          arrived: m.buyOrderStateEvent(group, santal, "ARRIVED"),
          have: m.buyOrderStateEvent(group, orris, "ALREADY_HAVE"),
        };
    """)

    def event(key, offer, pack, state):
        return {"kind": "order", "order_id": "PW-20261001-a1b2c3", "shop": "PW", "material_key": key,
                "offer_key": offer, "pack": pack, "state": state}

    santal = ("sandalwood oil s. album", "pw:7WX21054", "5 g")
    orris = ("orris concrete", "pw:2IR00002", "10 g")
    assert result["still"] == [event(*santal, "STILL_COMING"), event(*orris, "STILL_COMING"),
                               event("vetiver oil", "pw:9XX99999", "5 g", "STILL_COMING")]
    assert result["gone"] == event(*orris, "DIDNT_COME")
    assert result["notThis"] == event(*santal, "NOT_THIS")
    assert result["arrived"] == event(*santal, "ARRIVED")
    assert result["have"] == event(*orris, "ALREADY_HAVE")


def test_save_posts_the_pack_price_in_the_shops_currency():
    result = _group_run("""
        const [santal, orris] = group.lines;
        return [m.buyPaidQuestion(santal), m.buyStockPriceBody("stock-9", group, santal, "37.40"),
                m.buyStockPriceBody("stock-9", group, orris, " US$1,015.5 "),
                m.buyStockPriceBody("stock-9", group, santal, "0"), m.buyStockPriceBody("stock-9", group, santal, "lots")];
    """)

    assert result[0] == "Paid US$37.40?"
    assert result[1] == {"stock_id": "stock-9", "per_unit": "g", "pack_price": "37.40", "pack_size": "5",
                         "currency": "USD", "note": "Paid for PW order PW-20261001-a1b2c3"}
    assert result[2]["pack_price"] == "1015.5" and result[2]["pack_size"] == "10"
    assert result[3] is None and result[4] is None


def test_the_walk_moves_on_after_each_answer():
    result = _group_run("""
        const view = (walk, d = data) => m.buyWalkView(d, walk);
        const rest = (count) => ({ on_the_way: [{ ...group, lines: group.lines.slice(group.lines.length - count) }] });
        const start = m.buyWalkStart(group);
        const differs = m.buyWalkNext(start, "differs");
        const matches = m.buyWalkNext(differs, "matches", { line: group.lines[1] });
        const closed = m.buyWalkNext(matches, "closed");
        const again = m.buyWalkNext(closed, "matches", { line: group.lines[1] });
        const added = m.buyWalkNext(again, "added", { stockId: "stock-9" });
        const saved = m.buyWalkNext(added, "saved");
        const skipped = m.buyWalkNext(m.buyWalkNext(m.buyWalkNext(saved, "matches", { line: group.lines[2] }), "added", { stockId: "s" }), "skipped");
        return {
          start: view(start), differs: view(differs, rest(2)), matches: view(matches, rest(2)), closed: view(closed, rest(2)),
          added: view(added, rest(2)), addedWalk: added, saved: view(saved, rest(1)), done: view(skipped, rest(0)),
          stop: m.buyWalkNext(added, "stop"), elsewhere: view(start, { on_the_way: [] }),
        };
    """)

    assert result["start"]["text"] == ("1 of 3: Sandalwood oil S. album, PW 7WX21054, 5 g. "
                                       "Check the label: form, strength and species.")
    assert result["start"]["stage"] == "check" and result["start"]["note"] == ""
    # Something differs: NOT_THIS takes the line off the way and the walk shows the next one.
    assert result["differs"]["text"].startswith("2 of 3: Orris Concrete, PW 2IR00002, 10.0% in DPG, 10 g.")
    assert result["matches"]["stage"] == "stock"
    # The Stock add closed without saving: the walk pauses on the same line.
    assert result["closed"]["stage"] == "check" and result["closed"]["text"].startswith("2 of 3: Orris Concrete")
    assert result["closed"]["note"] == "Not added to your stock, and nothing saved for this one."
    assert result["added"]["stage"] == "price"
    assert result["added"]["question"] == "Paid US$15.00?"
    assert result["added"]["amount"] == "15"
    assert result["addedWalk"]["stockId"] == "stock-9"
    assert result["saved"]["text"].startswith("3 of 3: Vetiver Oil, PW 9XX99999, 5 g.")
    assert result["done"] is None
    assert result["stop"] is None
    assert result["elsewhere"] is None


def _buttons(group, walk=None):
    return _run(f"""
        const group = {json.dumps(group)};
        const walk = {json.dumps(walk)};
        const box = m.buyGroupNode(doc, group, {{ walk: walk && m.buyWalkView({{ on_the_way: [group] }}, walk) }});
        const all = (node) => [node, ...node.children.flatMap(all)];
        return all(box).filter((node) => node.tag === "button").map((node) => node.text);
    """)


def test_nudge_buttons_only_from_day_10_and_the_walk_replaces_it_arrived():
    quiet = {**GROUP, "nudge": False, "lines": GROUP["lines"][:1]}
    nudged = {**GROUP, "lines": GROUP["lines"][:1]}

    assert _buttons(quiet) == ["Didn't come", "Already have it", "It arrived"]
    assert _buttons(nudged) == ["Still coming", "Didn't come", "Didn't come", "Already have it", "It arrived"]
    walk = {"shop": "PW", "orderId": GROUP["order_id"], "done": 0, "stage": "check", "materialKey": None,
            "offerKey": None, "stockId": None, "note": ""}
    assert _buttons(quiet, walk) == ["Didn't come", "Already have it", "It matches", "Something differs", "Stop"]
    price = {**walk, "stage": "price", "materialKey": "sandalwood oil s. album", "offerKey": "pw:7WX21054",
             "stockId": "stock-9"}
    assert _buttons(quiet, price) == ["Didn't come", "Already have it", "Save", "Skip"]
