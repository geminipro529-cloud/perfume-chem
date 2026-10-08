import json
import shutil
import subprocess
from pathlib import Path

import pytest

LAB_DRAFTS_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "lab-drafts.js"


@pytest.mark.asyncio
async def test_offline_lab_app_and_assets_are_served_without_external_dependencies(client):
    page = await client.get("/app")
    css = await client.get("/static/lab.css")
    javascript = await client.get("/static/lab.js")

    assert page.status_code == 200
    assert css.status_code == 200
    assert javascript.status_code == 200
    assert "Perfume Chem Laboratory" in page.text
    for view in (
        "improve",
        "dashboard",
        "materials",
        "formulas",
        "bottles",
        "experiments",
        "perfumery",
        "assistant",
    ):
        assert f'data-view="{view}"' in page.text
    assert 'aria-live="polite"' in page.text
    assert "Evidence posture" in page.text
    assert "http://" not in page.text
    assert "https://" not in page.text
    assert "@media (max-width: 760px)" in css.text
    assert "prefers-reduced-motion" in css.text
    assert 'const API = "/api/v1/lab"' in javascript.text
    assert 'id="hypothesis-form"' in page.text
    assert 'id="trial-plan-form"' in page.text
    assert 'id="component-editor"' in page.text
    assert 'id="add-component-row"' in page.text
    assert 'data-component-row' in page.text
    assert 'components: componentRows()' in javascript.text
    assert 'request("/intervention-hypotheses"' in javascript.text
    assert 'request("/intervention-trials/plan"' in javascript.text
    assert "Safety remains unverified" in page.text
    assert "addEventListener" in javascript.text


@pytest.mark.asyncio
async def test_guided_improvement_ui_is_default_local_and_authority_safe(client):
    page = await client.get("/app")
    css = await client.get("/static/lab.css")
    javascript = await client.get("/static/lab.js")

    assert page.status_code == 200
    assert 'class="nav-item is-active" data-view="improve"' in page.text
    assert 'class="view is-visible" data-panel="improve"' in page.text
    assert 'id="improve-form"' in page.text
    assert 'value="EVOLVING_BOTTLE" checked' in page.text
    assert 'value="GLOBAL_CROWD_PLEASING"' in page.text
    assert "No photos or receipts required" in page.text
    assert "One clear direction is enough" in page.text
    assert "Analysis never changes the bottle by itself" in page.text
    assert 'id="physical-addition-confirmed"' in page.text
    assert 'id="quick-reaction-form"' in page.text
    assert "Personal evidence" in page.text
    assert 'name="formula_source_kind"' in page.text
    assert 'id="project-formula-options"' in page.text

    assert 'job_type: "FORMULA_ANALYSIS"' in javascript.text
    assert 'schema_version: "lab-engine-job-request-v2"' in javascript.text
    assert 'request("/v2/engine-jobs"' in javascript.text
    assert 'goal_analysis_sha256: state.improve.analysis.analysis_sha256' in javascript.text
    assert 'hypothesis_variant: state.improve.selectedVariant' in javascript.text
    assert "/quick-evaluations" in javascript.text
    assert 'request("/v2/workbench/formula-library")' in javascript.text
    assert "/v2/workbench/formula-source?source_path=" in javascript.text
    assert 'navigate(location.hash.slice(1) || "improve")' in javascript.text
    assert "window.setTimeout(resolve, 1000)" in javascript.text
    assert "http://" not in javascript.text
    assert "https://" not in javascript.text
    assert "Research behind this design · optional details" in javascript.text
    assert "sourceURL = parsed.href" in javascript.text
    assert 'parsed.protocol === "https:"' in javascript.text
    assert 'link.rel = "noopener noreferrer"' in javascript.text
    assert "paragraph.textContent = label" in javascript.text
    assert "knowledge.construction_context?.dossiers" in javascript.text
    assert "knowledge.subtype_context?.cards" in javascript.text
    assert "knowledge.subtype_context?.campaign_identity_holds" in javascript.text
    assert "result.architecture_planning?.implementation_coverage" in javascript.text
    assert "Coverage and remaining prerequisites" in javascript.text
    assert "line.textContent" in javascript.text
    assert "no completeness claim is made" in javascript.text
    assert "Reference identity unresolved:" in javascript.text
    assert "Design hypothesis:" in javascript.text
    assert "untested construction options" in javascript.text
    assert "Question to resolve:" in javascript.text
    assert "title.textContent" in javascript.text

    assert ".workflow-strip" in css.text
    assert ".hypothesis-grid" in css.text
    assert ".delta-line-editor" in css.text
    assert ".physical-line" in css.text
    assert "[hidden] { display: none !important; }" in css.text


@pytest.mark.asyncio
async def test_current_project_inventory_is_primary_and_not_reentered(client):
    before_materials = await client.get("/api/v1/lab/materials")
    before_stocks = await client.get("/api/v1/lab/stocks")
    response = await client.get("/api/v1/lab/v2/workbench/current-inventory")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "workbench-current-inventory-v3"
    assert payload["authority"] == "PERSONAL_DESIGN_INVENTORY_PROJECTION_READ_ONLY"
    assert payload["counts"]["stocks"] == len(payload["stocks"])
    assert payload["counts"]["stocks"] > 100
    assert payload["counts"]["execution_ready"] > 100
    assert payload["counts"]["design_ready"] >= payload["counts"]["execution_ready"]
    assert payload["counts"]["details_incomplete"] > 0
    assert len(payload["snapshot_sha256"]) == 64
    assert len(payload["canonical_effective_inventory_sha256"]) == 64
    assert len(payload["effective_inventory_sha256"]) == 64
    assert payload["inventory_modified"] is False
    assert payload["compounding_authority"] is False
    assert any(stock["identity_name"] == "Ambrox Super" for stock in payload["stocks"])
    assert any(
        stock["normalized_identity"] == "ambrox super crystals"
        for stock in payload["stocks"]
    )
    assert any(
        stock["normalized_identity"] == "sandalwood base x3"
        and stock["source_class"] == "LIVE_INVENTORY_TEXT"
        for stock in payload["stocks"]
    )
    assert payload["counts"]["live_inventory_text"] >= 60

    after_materials = await client.get("/api/v1/lab/materials")
    after_stocks = await client.get("/api/v1/lab/stocks")
    assert after_materials.json() == before_materials.json()
    assert after_stocks.json() == before_stocks.json()


@pytest.mark.asyncio
async def test_formula_conversation_creates_and_refines_read_only_design(client):
    before = await client.get("/api/v1/lab/dashboard")
    response = await client.post(
        "/api/v1/lab/v2/workbench/formula-chat",
        json={
            "schema_version": "inventory-grounded-formula-chat-request-v1",
            "message": "A clear mineral lavender over dry amber, not sweet",
            "formula_name": "Stone Lavender",
            "liquid_concentrate_ul_decimal": "6000",
            "max_materials": 8,
            "must_preserve": ["lavender identity"],
            "must_avoid": ["vanilla"],
            "previous_stock_ids": [],
            "conversation_context": [],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] in {
        "INVENTORY_GROUNDED_DESIGN_READY",
        "INVENTORY_GROUNDED_DESIGN_READY_WITH_HOLDS",
    }
    assert result["optimized_formula"]["separate_totals"]["liquid_total_ul"] == "6000"
    assert len(result["optimized_formula"]["rows"]) == 8
    assert any("Lavender" in row["material"] for row in result["optimized_formula"]["rows"])
    assert result["formula_action"] == "PROPOSAL_ONLY"
    assert result["inventory_modified"] is False
    assert result["physical_compounding_performed"] is False
    assert result["compounding_authority"] is False
    assert result["optimization"]["objective"] == (
        "REQUEST_CONSTRAINT_AND_NONREDUNDANT_ROLE_FULFILMENT"
    )
    assert result["critic"]["filler_rows_added"] == 0
    construction = result["formulation_knowledge"]["construction_context"]
    assert "AR_LAVENDER" in {row["package_id"] for row in construction["dossiers"]}
    assert construction["coverage"]["empirically_validated_packages"] == 0
    assert len(result["formulation_knowledge"]["construction_library_sha256"]) == 64

    after = await client.get("/api/v1/lab/dashboard")
    assert after.json()["counts"] == before.json()["counts"]


@pytest.mark.asyncio
async def test_formula_chat_exposes_source_bound_subtype_research(client):
    response = await client.post(
        "/api/v1/lab/v2/workbench/formula-chat",
        json={
            "schema_version": "inventory-grounded-formula-chat-request-v1",
            "message": "Lavender incense without Ambroxan",
            "formula_name": "Subtype Research Test",
            "liquid_concentrate_ul_decimal": "6000",
            "max_materials": 8,
            "must_preserve": ["lavender"],
            "must_avoid": ["Ambroxan"],
            "previous_stock_ids": [],
            "conversation_context": [],
        },
    )
    assert response.status_code == 200
    result = response.json()
    knowledge = result["formulation_knowledge"]
    assert len(knowledge["subtype_research_sha256"]) == 64
    assert "LAV_INCENSE" in {
        card["subtype_id"] for card in knowledge["subtype_context"]["cards"]
    }
    assert knowledge["subtype_context"]["coverage"]["empirically_validated_subtypes"] == 0
    assert knowledge["subtype_context"]["network_used"] is False
    assert result["inventory_modified"] is False
    assert result["physical_compounding_performed"] is False
    assert result["compounding_authority"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,expected,campaign_hold",
    [
        ("A dewy peony perfume", "PEONY_DEWY", False),
        ("A pineapple woody perfume", "PINEAPPLE_WOODY", False),
        ("CHIMIE LHOMME, dewy peony", "PEONY_DEWY", True),
        ("Lilac flowers, Syringa vulgaris", "LIGHT_LILAC", False),
        ("Honeysuckle flowers", "LIGHT_HONEYSUCKLE", False),
        ("Sweet pea flowers", "LIGHT_SWEET_PEA", False),
        ("Champaca flowers", "TROP_CHAMPACA", False),
        ("White Michelia alba flowers", "TROP_ALBA", False),
        ("Cananga floral character", "TROP_CANANGA", False),
        ("A smoky tea perfume", "TEA_SMOKED", False),
        ("A sacred lotus perfume", "AQUATIC_NELUMBO", False),
        ("A lychee perfume", "ORCHARD_LYCHEE_CULTIVARS", False),
    ],
)
async def test_formula_chat_exposes_floral_woody_successor(client, message, expected, campaign_hold):
    response = await client.post(
        "/api/v1/lab/v2/workbench/formula-chat",
        json={
            "schema_version": "inventory-grounded-formula-chat-request-v1",
            "message": message,
            "formula_name": "Research Successor Test",
            "liquid_concentrate_ul_decimal": "6000",
            "max_materials": 8,
            "must_preserve": [],
            "must_avoid": [],
            "previous_stock_ids": [],
            "conversation_context": [],
        },
    )
    assert response.status_code == 200
    result = response.json()
    context = result["formulation_knowledge"]["subtype_context"]
    assert expected in {card["subtype_id"] for card in context["cards"]}
    assert context["coverage"]["floral_packages_deepened"] == 13
    assert context["coverage"]["partial_research_cards"] == 179
    assert context["coverage"]["declared_additional_botanical_scopes"] == 24
    assert len(context["predecessor_manifest_sha256"]) == 64
    assert bool(context["campaign_identity_holds"]) is campaign_hold
    assert result["inventory_modified"] is False
    assert result["physical_compounding_performed"] is False
    assert result["compounding_authority"] is False


@pytest.mark.asyncio
async def test_deeper_review_reaches_api_and_text_safe_optional_ui(client):
    response = await client.post(
        "/api/v1/lab/v2/workbench/formula-chat",
        json={
            "schema_version": "inventory-grounded-formula-chat-request-v1",
            "message": "A dewy peony perfume", "formula_name": "Review Addendum Test",
            "liquid_concentrate_ul_decimal": "6000", "max_materials": 8,
            "must_preserve": [], "must_avoid": [], "previous_stock_ids": [],
            "conversation_context": [],
        },
    )
    assert response.status_code == 200
    knowledge = response.json()["formulation_knowledge"]
    peony = next(c for c in knowledge["subtype_context"]["cards"] if c["subtype_id"] == "PEONY_DEWY")
    assert peony["review_addenda"]
    assert "peony_methods_finish" in {s["source_id"] for s in knowledge["sources"]}
    asset = await client.get("/static/lab.js")
    assert "card.review_addenda" in asset.text
    assert "update.textContent = `Deeper source review:" in asset.text
    assert "Research behind this design · optional details" in asset.text


@pytest.mark.asyncio
async def test_source_bound_architecture_comparisons_reach_formula_ui_without_writes(client):
    before = await client.get("/api/v1/lab/dashboard")
    response = await client.post(
        "/api/v1/lab/v2/workbench/formula-chat",
        json={
            "schema_version": "inventory-grounded-formula-chat-request-v1",
            "message": "A peppery freesia perfume", "formula_name": "Architecture test",
            "liquid_concentrate_ul_decimal": "6000", "max_materials": 12,
            "design_mode": "DEEP_COMPOSE", "variant_count": 3,
        },
    )
    assert response.status_code == 200
    result = response.json()
    variants = result["design_variants"]
    assert len(variants) == 3
    assert len({v["role_plan_sha256"] for v in variants}) == 3
    assert variants[0]["architecture"]["kind"] == "UNCHANGED_CONTROL"
    assert result["architecture_planning"]["state"] == "SOURCE_BOUND_COMPARISON_READY"
    for variant in variants[1:]:
        assert variant["architecture"]["subtype_id"] == "FREESIA_PEPPER"
        assert variant["architecture"]["source_bindings"]
        assert variant["architecture"]["comparison_question"]
        assert not any(variant["architecture"]["authority"].values())
    after = await client.get("/api/v1/lab/dashboard")
    assert after.json()["counts"] == before.json()["counts"]
    assert result["inventory_modified"] is False
    assert result["formula_modified"] is False
    assert result["physical_compounding_performed"] is False
    asset = await client.get("/static/lab.js")
    assert "selected.variant?.architecture?.comparison_question" in asset.text
    assert "This is an untested role-plan hypothesis, not a measured improvement." in asset.text
    assert "paragraph.textContent = text;" in asset.text
    assert "selected.variant?.role_plan?.length" in asset.text
    assert "selected.variant?.temporal_hypothesis" in asset.text
    assert 'critic?.state === "WITHHELD" ? null' in asset.text


@pytest.mark.asyncio
async def test_inventory_details_can_be_completed_without_physical_authority(client):
    inventory_response = await client.get(
        "/api/v1/lab/v2/workbench/current-inventory"
    )
    inventory = inventory_response.json()
    stock = next(
        item
        for item in inventory["stocks"]
        if item["identity_name"] == "Cedrat FCF Sicilian"
    )
    response = await client.post(
        "/api/v1/lab/v2/workbench/current-inventory/complete",
        json={
            "schema_version": "personal-inventory-completion-request-v1",
            "stock_id": stock["stock_id"],
            "expected_effective_inventory_sha256": inventory[
                "canonical_effective_inventory_sha256"
            ],
            "idempotency_key": "ui-complete-cedrat",
            "fraction_percent_decimal": "100",
            "fraction_basis": "neat",
            "carrier": "",
            "physical_form": "as_supplied",
            "possession_confirmed": True,
            "homogeneity": "NOT_APPLICABLE",
            "final_fraction_known": True,
            "source_kind": "PERSONAL_CONFIRMATION",
            "user_note": "Current bottle confirmed for personal design.",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "PERSONAL_DESIGN_DETAILS_COMPLETE"
    assert result["design_ready"] is True
    assert result["inventory_quantity_modified"] is False
    assert result["compounding_authority"] is False
    updated = next(
        item
        for item in result["inventory"]["stocks"]
        if item["stock_id"] == stock["stock_id"]
    )
    assert updated["design_ready"] is True
    assert updated["execution_ready"] is False
    assert updated["missing_fields"] == []

    replay = await client.post(
        "/api/v1/lab/v2/workbench/current-inventory/complete",
        json={
            "schema_version": "personal-inventory-completion-request-v1",
            "stock_id": stock["stock_id"],
            "expected_effective_inventory_sha256": inventory[
                "canonical_effective_inventory_sha256"
            ],
            "idempotency_key": "ui-complete-cedrat",
            "fraction_percent_decimal": "100",
            "fraction_basis": "neat",
            "carrier": "",
            "physical_form": "as_supplied",
            "possession_confirmed": True,
            "homogeneity": "NOT_APPLICABLE",
            "final_fraction_known": True,
            "source_kind": "PERSONAL_CONFIRMATION",
            "user_note": "Current bottle confirmed for personal design.",
        },
    )
    assert replay.status_code == 200
    assert replay.json()["receipt"]["event_sha256"] == result["receipt"]["event_sha256"]


@pytest.mark.asyncio
async def test_formula_studio_ui_exposes_inventory_and_conversation(client):
    page = await client.get("/app")
    css = await client.get("/static/lab.css")
    javascript = await client.get("/static/lab.js")

    assert 'id="project-inventory-list"' in page.text
    assert 'id="project-inventory-search"' in page.text
    assert 'id="project-inventory-incomplete-only"' in page.text
    assert 'id="inventory-completion-form"' in page.text
    assert 'id="inventory-addition-form"' in page.text
    assert 'id="inventory-add-open"' in page.text
    assert "No photo, invoice, supplier lot, or density is required" in page.text
    assert "You do not need to enter it again" in page.text
    assert 'id="formula-chat-form"' in page.text
    assert 'id="formula-chat-log"' in page.text
    assert 'id="formula-chat-result"' in page.text
    assert "Create my formula" in page.text
    assert '<option value="60">Maximum — up to 60</option>' in page.text
    assert "Any selected crystal remains a separate mg line" in page.text
    assert 'request("/v2/workbench/current-inventory")' in javascript.text
    assert 'request("/v2/workbench/current-inventory/complete"' in javascript.text
    assert 'request("/v2/workbench/current-inventory/add"' in javascript.text
    assert 'request("/v2/workbench/formula-chat"' in javascript.text
    assert "previous_stock_ids" in javascript.text
    assert "conversation_context" in javascript.text
    assert ".formula-chat-layout" in css.text
    assert ".inventory-grid" in css.text
    assert ".formula-design-table" in css.text


@pytest.mark.asyncio
async def test_create_and_improve_drafts_are_kept_in_browser_storage(client):
    page = await client.get("/app")
    css = await client.get("/static/lab.css")
    javascript = await client.get("/static/lab.js")
    drafts = await client.get("/static/lab-drafts.js")

    assert drafts.status_code == 200
    assert page.text.index('src="/static/lab-drafts.js"') < page.text.index('src="/static/lab.js"')
    assert '"perfume-lab.draft.create.v1"' in drafts.text
    assert '"perfume-lab.draft.improve.v1"' in drafts.text
    assert "const DRAFT_VERSION = 1;" in drafts.text
    assert "const DRAFT_MAX_CHARS = 1000000;" in drafts.text
    assert "`Restored your draft from ${formatDraftTime(iso)}. ${text}`" in javascript.text
    assert "made from your inventory at that time" in javascript.text
    assert "restoreStoredDrafts();\nrefresh()" in javascript.text
    assert 'window.addEventListener("pagehide"' in javascript.text
    # Every storage access is guarded so blocked or full storage cannot break the page.
    lines = drafts.text.splitlines()
    for call in ("storage.getItem(", "storage.setItem(", "storage.removeItem("):
        positions = [index for index, line in enumerate(lines) if call in line]
        assert positions
        assert all(lines[position - 1].strip() == "try {" for position in positions)
    assert "localStorage" not in drafts.text
    lab_lines = javascript.text.splitlines()
    positions = [index for index, line in enumerate(lab_lines) if "window.localStorage" in line]
    assert len(positions) == 1
    assert lab_lines[positions[0] - 1].strip() == "try {"
    # Only what the page draws is stored, not server source paths.
    assert "stock_source_ref" not in javascript.text + drafts.text
    assert 'id="formula-draft-unsaved"' in page.text
    assert 'id="improve-draft-unsaved"' in page.text
    assert 'id="formula-draft-restored"' in page.text
    assert 'id="improve-draft-restored"' in page.text
    assert 'data-discard-draft="create">Discard</button>' in page.text
    assert 'data-discard-draft="improve">Discard</button>' in page.text
    assert ".draft-restored" in css.text


_DRAFT_HARNESS = """
const assert = require("assert");
const D = require(process.argv[1]);
function fakeStorage({ failGet = false, failSet = false } = {}) {
  const items = new Map();
  return {
    items,
    getItem(key) { if (failGet) throw new Error("blocked"); return items.has(key) ? items.get(key) : null; },
    setItem(key, value) { if (failSet) throw new Error("QuotaExceededError"); items.set(key, String(value)); },
    removeItem(key) { if (failGet) throw new Error("blocked"); items.delete(key); },
  };
}
const KEY = D.DRAFT_KEYS.create;
const body = (text) => ({ fields: { message: text } });
"""


def _run_draft_case(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed, so the browser draft rules cannot be run")
    completed = subprocess.run(
        [node, "-e", _DRAFT_HARNESS + script, str(LAB_DRAFTS_JS)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout


def test_unusable_stored_drafts_are_removed_and_ignored():
    _run_draft_case(r"""
    const now = new Date().toISOString();
    const cases = {
      corrupt: "{not json",
      older_version: JSON.stringify({ version: 0, saved_at: now, fields: { message: "old" } }),
      bad_saved_at: JSON.stringify({ version: 1, saved_at: "yesterday-ish", fields: {} }),
      bad_designed_at: JSON.stringify({ version: 1, saved_at: now, designed_at: "not a date", fields: {} }),
      oversize: JSON.stringify({ version: 1, saved_at: now, fields: { message: "x".repeat(D.DRAFT_MAX_CHARS) } }),
    };
    for (const [name, raw] of Object.entries(cases)) {
      const storage = fakeStorage();
      storage.items.set(KEY, raw);
      const read = D.readDraft(storage, "create");
      assert.strictEqual(read.draft, null, name);
      assert.strictEqual(read.outcome, "removed", name);
      assert.ok(!storage.items.has(KEY), name);
    }
    const blocked = D.readDraft(fakeStorage({ failGet: true }), "create");
    assert.deepStrictEqual(blocked, { draft: null, outcome: "unavailable" });
    assert.strictEqual(D.readDraft(null, "create").outcome, "unavailable");
    const good = fakeStorage();
    const saved = D.writeDraft(good, "create", body("kept"), { writer: "a" });
    assert.strictEqual(saved.outcome, "saved");
    const restored = D.readDraft(good, "create");
    assert.strictEqual(restored.draft.fields.message, "kept");
    assert.strictEqual(D.draftStamp(restored.draft), saved.stamp);
    """)


def test_a_failed_or_oversize_save_removes_the_older_draft():
    _run_draft_case(r"""
    const storage = fakeStorage();
    const first = D.writeDraft(storage, "create", body("older brief"), { writer: "a" });
    assert.strictEqual(first.outcome, "saved");
    storage.setItem = () => { throw new Error("QuotaExceededError"); };
    const failed = D.writeDraft(storage, "create", body("newer brief"), { writer: "a", lastSeen: first.stamp });
    assert.deepStrictEqual(failed, { outcome: "failed", stamp: null });
    assert.ok(!storage.items.has(KEY), "the older draft must not come back");

    const big = fakeStorage();
    const kept = D.writeDraft(big, "create", body("older brief"), { writer: "a" });
    const tooLarge = D.writeDraft(big, "create", body("x".repeat(D.DRAFT_MAX_CHARS)), { writer: "a", lastSeen: kept.stamp });
    assert.deepStrictEqual(tooLarge, { outcome: "too_large", stamp: null });
    assert.ok(!big.items.has(KEY));

    const blocked = D.writeDraft(fakeStorage({ failGet: true }), "create", body("x"), { writer: "a" });
    assert.strictEqual(blocked.outcome, "failed");
    """)


def test_a_stale_tab_cannot_undo_a_discard_or_overwrite_a_newer_draft():
    _run_draft_case(r"""
    const storage = fakeStorage();
    const original = D.writeDraft(storage, "create", body("design"), { writer: "a" });
    // Tabs A and B both restore the same draft.
    const seenByA = D.draftStamp(D.readDraft(storage, "create").draft);
    const seenByB = D.draftStamp(D.readDraft(storage, "create").draft);
    assert.strictEqual(seenByA, original.stamp);
    // A discards; B then types.
    D.removeDraft(storage, "create");
    const fromB = D.writeDraft(storage, "create", body("design plus one"), { writer: "b", lastSeen: seenByB });
    assert.strictEqual(fromB.outcome, "stale");
    assert.ok(!storage.items.has(KEY), "Discard must not be undone");
    // A, having discarded, may start again.
    const fresh = D.writeDraft(storage, "create", body("new idea"), { writer: "a", lastSeen: null });
    assert.strictEqual(fresh.outcome, "saved");

    // Reverse: B opened before any design; A then creates one; B types.
    const second = fakeStorage();
    const newer = D.writeDraft(second, "create", body("newer design"), { writer: "a", lastSeen: null });
    const old = D.writeDraft(second, "create", body("old text"), { writer: "b", lastSeen: null });
    assert.strictEqual(old.outcome, "stale");
    assert.strictEqual(JSON.parse(second.items.get(KEY)).fields.message, "newer design");
    const cleared = D.writeDraft(second, "create", null, { writer: "b", lastSeen: null });
    assert.strictEqual(cleared.outcome, "stale");
    assert.ok(second.items.has(KEY));
    // The writer that saw the newest draft keeps saving over it.
    const next = D.writeDraft(second, "create", body("newer design, edited"), { writer: "a", lastSeen: newer.stamp });
    assert.strictEqual(next.outcome, "saved");
    """)


def test_stored_copy_has_no_hashes_or_source_paths_and_keeps_bench_fields():
    out = _run_draft_case(r"""
    const row = {
      material: "Linalool", stock_id: "stock-1", stock_source_ref: "inventory.txt:12", source_ref: "data/x.json",
      amount_decimal: "120", amount_unit: "uL", operation: "PREPARE_DILUTION_FIRST", execution_ready: false,
      stock_authority: "PERSONAL_INVENTORY",
    };
    const result = {
      formula_name: "Cold Lavender", request_sha256: "a".repeat(64), design_sha256: "b".repeat(64),
      inventory: { source_path: "/home/user/inventory.txt" },
      critic: { state: "PASS", issues: ["hold"], limitations: [], strongest_clue: "clue", source_ref: "x" },
      optimized_formula: { rows: [row], separate_totals: { liquid_total_ul: "120" } },
      design_variants: [{ label: "A", formula: { rows: [row] }, critic: { state: "PASS", issues: [] } }],
    };
    const copy = D.draftDisplayCopy(result);
    process.stdout.write(JSON.stringify(copy));
    """)
    copy = json.loads(out)
    text = json.dumps(copy)
    for forbidden in ("request_sha256", "design_sha256", "stock_source_ref", "source_ref", "source_path", "stock_authority"):
        assert forbidden not in text
    row = copy["optimized_formula"]["rows"][0]
    assert row["operation"] == "PREPARE_DILUTION_FIRST"
    assert row["execution_ready"] is False
    assert row["stock_id"] == "stock-1"
    assert copy["design_variants"][0]["formula"]["rows"][0]["operation"] == "PREPARE_DILUTION_FIRST"
    assert copy["critic"] == {"state": "PASS", "issues": ["hold"], "limitations": [], "strongest_clue": "clue"}


def test_restored_download_is_labelled_as_a_trimmed_browser_copy():
    out = _run_draft_case(r"""
    process.stdout.write(JSON.stringify([
      D.draftDownload({ formula_name: "Cold Lavender!" }, false),
      D.draftDownload({ formula_name: "Cold Lavender!" }, true),
    ]));
    """)
    fresh, restored = json.loads(out)
    assert fresh == {"filename": "cold-lavender.json", "message": "Read-only formula draft downloaded."}
    assert restored["filename"] == "cold-lavender-restored-browser-copy.json"
    assert "trimmed browser copy of a restored draft" in restored["message"]
    assert "not the full server result" in restored["message"]


@pytest.mark.asyncio
async def test_missing_owned_material_can_be_added_for_personal_design(client):
    inventory_response = await client.get(
        "/api/v1/lab/v2/workbench/current-inventory"
    )
    inventory = inventory_response.json()
    response = await client.post(
        "/api/v1/lab/v2/workbench/current-inventory/add",
        json={
            "schema_version": "personal-inventory-addition-request-v1",
            "expected_design_inventory_sha256": inventory[
                "effective_inventory_sha256"
            ],
            "idempotency_key": "backend-add-hindinol",
            "identity_name": "Hindinol",
            "category": "woods / amber / structure",
            "fraction_percent_decimal": "100",
            "fraction_basis": "neat",
            "carrier": "",
            "physical_form": "as_supplied",
            "possession_confirmed": True,
            "homogeneity": "NOT_APPLICABLE",
            "source_kind": "PERSONAL_CONFIRMATION",
            "supplier_name": "PerfumersWorld",
            "supplier_sku": "4WX24656",
            "user_note": "Direct user confirmation.",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "PERSONAL_INVENTORY_MATERIAL_ADDED"
    assert result["compounding_authority"] is False
    hindinol = next(
        stock
        for stock in result["inventory"]["stocks"]
        if stock["identity_name"] == "Hindinol"
    )
    assert hindinol["source_class"] == "PERSONAL_ADDITION"
    assert hindinol["design_ready"] is True
    assert hindinol["execution_ready"] is False

    formula_response = await client.post(
        "/api/v1/lab/v2/workbench/formula-chat",
        json={
            "schema_version": "inventory-grounded-formula-chat-request-v2",
            "message": (
                "Create a dry sandalwood perfume that must use Hindinol and "
                "Sandalwood Base X3 as separate owned materials."
            ),
            "formula_name": "Inventory Alias Check",
            "liquid_concentrate_ul_decimal": "6000",
            "max_materials": 8,
            "must_preserve": ["Hindinol", "Sandalwood Base X3"],
            "must_avoid": [],
            "previous_stock_ids": [],
            "conversation_context": [],
        },
    )
    assert formula_response.status_code == 200
    selected = {
        row["identity_name"]
        for row in formula_response.json()["optimized_formula"]["rows"]
    }
    assert {"Hindinol", "Sandalwood Base 3X"} <= selected


@pytest.mark.asyncio
async def test_project_formula_library_is_read_only_and_preserves_mixed_units(client):
    library_response = await client.get("/api/v1/lab/v2/workbench/formula-library")

    assert library_response.status_code == 200
    library = library_response.json()
    assert library["inventory_modified"] is False
    assert library["compounding_authority"] is False
    source_path = "Lavande_Ambre_Profond_Parallel_A_30mL_EDP.md"
    assert source_path in {source["source_path"] for source in library["sources"]}

    source_response = await client.get(
        "/api/v1/lab/v2/workbench/formula-source",
        params={"source_path": source_path},
    )

    assert source_response.status_code == 200
    source = source_response.json()
    assert source["formula_name"].startswith("Lavande Ambre Profond")
    assert len(source["rows"]) == 24
    assert source["separate_totals"] == {
        "liquid_total_ul": "5600",
        "mass_total_mg": "300",
    }
    ambrox = next(row for row in source["rows"] if row["material"] == "Ambrox Super Crystals")
    assert ambrox["amount_decimal"] == "300"
    assert ambrox["amount_unit"] == "mg"
    assert ambrox["operation"] == "MASS_ADD"
    assert source["design_only"] is True
    assert source["inventory_modified"] is False
    assert source["release_authority"] is False
    assert source["safety_authority"] is False
    assert source["compounding_authority"] is False


@pytest.mark.asyncio
async def test_project_formula_library_rejects_path_escape(client):
    response = await client.get(
        "/api/v1/lab/v2/workbench/formula-source",
        params={"source_path": "../inventory.txt"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_LAB_COMMAND"


@pytest.mark.asyncio
async def test_application_default_dose_is_valid_for_its_html_step(client):
    page = await client.get("/app")

    assert (
        '<input name="mass_mg" type="number" value="20" min="0.1" step="0.1" required>'
        in page.text
    )


@pytest.mark.asyncio
async def test_bottle_addition_default_mass_is_valid_for_its_html_step(client):
    page = await client.get("/app")

    assert (
        '<input name="mass_g" type="number" value="0.1" min="0.001" step="0.001" required>'
        in page.text
    )


@pytest.mark.asyncio
async def test_science_authority_view_preserves_labels_modes_and_unknowns(client):
    page = await client.get("/app")
    css = await client.get("/static/lab.css")
    javascript = await client.get("/static/lab.js")

    assert page.status_code == 200
    assert 'data-view="science"' in page.text
    assert 'data-panel="science"' in page.text
    assert 'id="science-view-mode"' in page.text
    assert '<option value="strict">Strict science</option>' in page.text
    assert '<option value="exploratory">Exploratory science</option>' in page.text
    assert 'id="science-summary"' in page.text
    assert 'id="science-sections"' in page.text
    assert 'id="science-json-download"' in page.text
    assert 'id="science-markdown-download"' in page.text
    assert "Strict-withheld records remain visible" in page.text
    assert "READ_ONLY_NON_PROMOTING" in page.text

    evidence_classes = (
        "MEASURED",
        "LITERATURE_DERIVED",
        "SUPPLIER_PROVIDED",
        "EMPIRICALLY_CALIBRATED",
        "MODEL_ESTIMATED",
        "HEURISTIC",
        "SPECULATIVE",
        "UNKNOWN",
    )
    for label in evidence_classes:
        assert f'data-evidence-class="{label}"' in page.text
        assert f"evidence-{label.lower().replace('_', '-')}" in css.text

    assert 'request(`/science/authority?view=${view}`)' in javascript.text
    assert 'scienceSections.replaceChildren(fragment)' in javascript.text
    assert "textContent" in javascript.text
    assert "strict_reason_codes" in javascript.text
    assert "evidence_class" in javascript.text
    assert "/api/v1/lab/science/report.md?view=" in javascript.text
    assert "confidence percentage" not in page.text.casefold()
    assert "confidence percentage" not in javascript.text.casefold()
