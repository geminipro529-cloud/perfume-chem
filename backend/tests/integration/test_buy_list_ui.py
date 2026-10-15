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
