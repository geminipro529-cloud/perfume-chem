"""Kenny's own stock prices: the log, the routes and the bench-sheet cost (node)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from engine import stock_prices

PRICES = "/api/v1/lab/v2/workbench/stock-prices"
INVENTORY = "/api/v1/lab/v2/workbench/current-inventory"
STOCK_PRICES_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "stock-prices.js"


@pytest.fixture
def price_log(tmp_path, monkeypatch):
    path = tmp_path / "prices.jsonl"
    monkeypatch.setenv(stock_prices.PRICE_PATH_ENV, str(path))
    return path


def test_latest_entry_per_stock_wins_and_clear_removes_it(price_log):
    stock_prices.record_stock_price(stock_id="s1", per_unit="g", price_decimal="12.50")
    stock_prices.record_stock_price(stock_id="s1", per_unit="mL", pack_price="1000", pack_size="3")
    stock_prices.record_stock_price(stock_id="ethanol", per_unit="mL", price_decimal="0.4")
    stock_prices.record_stock_price(stock_id="ethanol", per_unit="mL", clear=True)

    latest = stock_prices.latest_prices()
    assert set(latest) == {"s1"}
    assert latest["s1"]["per_unit"] == "mL"
    assert latest["s1"]["pack_price"] == "1000"
    assert latest["s1"]["pack_size"] == "3"
    assert latest["s1"]["price_decimal"] == "333.333333"
    assert latest["s1"]["currency"] == "THB"
    assert len(price_log.read_text(encoding="utf-8").splitlines()) == 4


@pytest.mark.parametrize(
    "fields",
    [
        {"stock_id": "s1", "per_unit": "kg", "price_decimal": "1"},
        {"stock_id": "s1", "per_unit": "g", "price_decimal": "0"},
        {"stock_id": "s1", "per_unit": "g", "price_decimal": "-2"},
        {"stock_id": "s1", "per_unit": "g", "price_decimal": "abc"},
        {"stock_id": "s1", "per_unit": "g"},
        {"stock_id": "s1", "per_unit": "g", "pack_price": "100"},
        {"stock_id": "s1", "per_unit": "g", "price_decimal": "1", "pack_price": "1", "pack_size": "1"},
        {"stock_id": "s1", "per_unit": "g", "price_decimal": "1", "currency": "baht"},
        {"stock_id": "ethanol", "per_unit": "g", "price_decimal": "1"},
        {"stock_id": "packaging_per_bottle", "per_unit": "mL", "price_decimal": "1"},
        {"stock_id": "s1", "per_unit": "bottle", "price_decimal": "1"},
    ],
)
def test_invalid_entries_are_refused_and_nothing_is_written(price_log, fields):
    with pytest.raises(stock_prices.StockPriceError):
        stock_prices.record_stock_price(**fields)
    assert not price_log.exists()


def test_an_edited_line_breaks_the_chain(price_log):
    stock_prices.record_stock_price(stock_id="s1", per_unit="g", price_decimal="5")
    event = json.loads(price_log.read_text(encoding="utf-8"))
    event["price_decimal"] = "1"
    price_log.write_text(json.dumps(event) + "\n", encoding="utf-8")

    with pytest.raises(stock_prices.StockPriceLogCorruptError):
        stock_prices.latest_prices()


def test_the_default_log_sits_in_data_user_and_is_gitignored(monkeypatch):
    monkeypatch.delenv(stock_prices.PRICE_PATH_ENV, raising=False)
    monkeypatch.delenv("PERFUME_INVENTORY_COMPLETION_PATH", raising=False)
    path = stock_prices.price_log_path()
    assert path.name == "user_stock_price_events.jsonl"
    assert path.parent.name == "user" and path.parent.parent.name == "data"


@pytest.mark.asyncio
async def test_price_routes_save_read_and_refuse(client, price_log):
    stock_id = (await client.get(INVENTORY)).json()["stocks"][0]["stock_id"]

    saved = await client.post(PRICES, json={"stock_id": stock_id, "per_unit": "g", "price_decimal": "25"})
    ethanol = await client.post(PRICES, json={"stock_id": "ethanol", "per_unit": "mL", "price_decimal": "0.35"})
    packaging = await client.post(
        PRICES, json={"stock_id": "packaging_per_bottle", "per_unit": "bottle", "pack_price": "1200", "pack_size": "10"}
    )
    unknown = await client.post(PRICES, json={"stock_id": "no-such-stock", "per_unit": "g", "price_decimal": "1"})
    bad = await client.post(PRICES, json={"stock_id": stock_id, "per_unit": "g", "price_decimal": "0"})
    extra = await client.post(PRICES, json={"stock_id": stock_id, "per_unit": "g", "price_decimal": "1", "x": 1})
    listed = await client.get(PRICES)

    assert saved.status_code == ethanol.status_code == packaging.status_code == 200
    assert saved.json()["receipt"]["price_decimal"] == "25"
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "STOCK_PRICE_STOCK_NOT_IN_INVENTORY"
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "INVALID_STOCK_PRICE"
    assert extra.status_code == 422
    prices = listed.json()["prices"]
    assert set(prices) == {stock_id, "ethanol", "packaging_per_bottle"}
    assert prices["packaging_per_bottle"]["price_decimal"] == "120"
    assert listed.json()["compounding_authority"] is False


@pytest.mark.asyncio
async def test_a_damaged_log_is_reported_not_overwritten(client, price_log):
    price_log.write_text("not json\n", encoding="utf-8")

    listed = await client.get(PRICES)
    saved = await client.post(PRICES, json={"stock_id": "ethanol", "per_unit": "mL", "price_decimal": "1"})

    assert listed.status_code == saved.status_code == 409
    assert price_log.read_text(encoding="utf-8") == "not json\n"


# ---- stock-prices.js --------------------------------------------------------


def _js(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the stock-prices logic test needs it")
    program = f"const p = require({json.dumps(str(STOCK_PRICES_JS))});\nprocess.stdout.write(JSON.stringify(({script})(p)));"
    completed = subprocess.run([node, "-e", program], capture_output=True, text=True, encoding="utf-8", timeout=60, check=True)
    return json.loads(completed.stdout)


ROWS = [
    {"material": "Hedione", "stock_id": "hed", "amount_decimal": "1200", "amount_unit": "uL"},
    {"material": "Ambrox", "stock_id": "amb", "amount_decimal": "300", "amount_unit": "mg"},
    {"material": "Iso E Super", "stock_id": "iso", "amount_decimal": "800", "amount_unit": "µL"},
    {"material": "Rose Oxide", "stock_id": None, "amount_decimal": "6", "amount_unit": "µL"},
]
PRICE_MAP = {
    "hed": {"price_decimal": "3", "per_unit": "mL", "currency": "THB"},
    "amb": {"pack_price": "1000", "pack_size": "3", "price_decimal": "333.333333", "per_unit": "g", "currency": "THB"},
    "iso": {"price_decimal": "2", "per_unit": "g", "currency": "THB"},
    "ethanol": {"price_decimal": "0.35", "per_unit": "mL", "currency": "THB"},
    "packaging_per_bottle": {"price_decimal": "45.5", "per_unit": "bottle", "currency": "THB"},
}


def test_bench_cost_is_exact_and_says_when_it_is_partial():
    result = _js(
        "(p) => { const c = p.benchCost({ rows: "
        + json.dumps(ROWS)
        + ", prices: "
        + json.dumps(PRICE_MAP)
        + ", ethanolMl: '24', bottles: '3' });"
        " const m = (v) => v ? p.stockPriceMoneyText(v, c.currency) : null;"
        " return { lines: c.lines.map((l) => [m(l.cost), l.reason]), extras: c.extras.map((e) => m(e.cost)),"
        " bottle: m(c.bottle), batch: m(c.batch), partial: c.partial, missing: c.missing,"
        " estimate: p.benchCostEthanolEstimate(" + json.dumps(ROWS) + ", '30') }; }"
    )

    # 1.2 mL x 3 = 3.60; 0.3 g x 1000/3 = 100 exactly (not 99.9999999 from the rounded unit price).
    assert result["lines"] == [
        ["3.60 THB", ""],
        ["100.00 THB", ""],
        [None, "not costed: price is per g, row is in µL, no density"],
        [None, "no price: not matched to a stock"],
    ]
    assert result["extras"] == ["8.40 THB", "45.50 THB"]
    assert result["bottle"] == "157.50 THB"
    assert result["batch"] == "472.50 THB"
    assert result["partial"] is True
    assert result["missing"] == ["Iso E Super", "Rose Oxide"]
    # 30 mL less 1.2 + 0.8 + 0.006 mL of liquid stock; the 300 mg solid adds none.
    assert result["estimate"] == "27.994"


def test_bench_cost_refuses_mixed_currencies_and_a_bad_bottle_count():
    result = _js(
        "(p) => { const prices = { hed: { price_decimal: '3', per_unit: 'mL', currency: 'THB' },"
        " ethanol: { price_decimal: '1', per_unit: 'mL', currency: 'USD' } };"
        " const rows = [{ material: 'Hedione', stock_id: 'hed', amount_decimal: '1000', amount_unit: 'µL' }];"
        " const mixed = p.benchCost({ rows, prices, ethanolMl: '1', bottles: '1' });"
        " const thb = { hed: prices.hed };"
        " const zero = p.benchCost({ rows, prices: thb, ethanolMl: '', bottles: '0' });"
        " return { mixed: [mixed.problem, mixed.bottle], zero: [zero.problem, zero.batch === null, zero.partial,"
        " p.stockPriceMoneyText(zero.bottle, zero.currency)] }; }"
    )

    assert result["mixed"] == ["Prices are in more than one currency (THB, USD); totals are not added.", None]
    assert result["zero"] == ["Number of bottles must be a whole number from 1 to 99999.", True, True, "3.00 THB"]


def test_price_request_body_sends_either_a_unit_price_or_a_pack():
    result = _js(
        "(p) => [p.stockPriceRequestBody('s1', { mode: 'unit', per_unit: 'g', price_decimal: ' 12.5 ', pack_price: '9', currency: 'thb' }),"
        " p.stockPriceRequestBody('s1', { mode: 'pack', per_unit: 'mL', price_decimal: '4', pack_price: '1000', pack_size: '100', currency: '' })]"
    )

    assert result[0] == {"stock_id": "s1", "per_unit": "g", "price_decimal": "12.5", "pack_price": None, "pack_size": None, "currency": "THB", "note": ""}
    assert result[1] == {"stock_id": "s1", "per_unit": "mL", "price_decimal": None, "pack_price": "1000", "pack_size": "100", "currency": "THB", "note": ""}
