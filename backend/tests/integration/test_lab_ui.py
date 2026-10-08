import json
import shutil
import subprocess
from pathlib import Path

import pytest

LAB_DRAFTS_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "lab-drafts.js"
BENCH_SHEET_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "bench-sheet.js"


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
    assert '? startView : "improve")' in javascript.text
    assert "waitForEngineJob(jobId, { area, intervalMs = 1000" in javascript.text
    assert 'request("/v2/engine-workers/status"' in javascript.text
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
async def test_formula_result_fits_prints_and_offers_a_bench_sheet(client):
    page = await client.get("/app")
    css = await client.get("/static/lab.css")
    javascript = await client.get("/static/lab.js")

    header = page.text.split('class="formula-design-table"', 1)[1].split("</thead>", 1)[0]
    headings = [cell.split("</th>", 1)[0] for cell in header.split("<th>")[1:]]
    assert headings[1] == "Dose"
    assert headings[0].startswith("Material")
    assert "min-width: 790px" not in css.text
    assert '<td class="formula-dose">' in javascript.text.split("formula-why", 1)[1].split("</tr>", 1)[0]

    print_css = css.text.split("@media print {", 1)[1]
    assert ".formula-table-wrap { overflow: visible; }" in print_css
    assert ".formula-design-table { min-width: 0; }" in print_css
    hidden_in_print = print_css.split("{ display: none !important; }", 1)[0].rsplit("}", 1)[1]
    for hidden in (".masthead", ".rail", "#status", ".formula-variant-picker"):
        assert hidden in hidden_in_print
    # Forms, summaries and action buttons are hidden only in the Create view, so
    # other views (an omission plan inside its form) still print; the Create
    # disclaimer paragraph stays in the print.
    for scoped in ('[data-panel="formulas"] form', '[data-panel="formulas"] .request-actions button', '[data-panel="formulas"] details > summary'):
        assert scoped in hidden_in_print
    for selector in (part.strip() for part in hidden_in_print.split(",")):
        if any(token in selector.split() for token in ("form", ".request-actions", "summary")):
            assert selector.startswith('[data-panel="formulas"] '), selector
    assert "body.printing-bench-sheet .bench-sheet { display: block;" in print_css

    actions = page.text.split('id="formula-download"', 1)[1].split("</div>", 1)[0]
    assert '<button id="formula-print-bench" type="button">Print bench sheet</button>' in actions
    assert 'id="bench-sheet"' in page.text
    assert page.text.index('src="/static/bench-sheet.js"') < page.text.index('src="/static/lab.js"')
    assert 'id="formula-result-variant"' in page.text
    assert "window.print()" in javascript.text
    assert "benchSheetHtml(" in javascript.text
    assert "formula-dose-hold" in javascript.text
    assert "benchBasisText(row.fraction_basis)" in javascript.text
    bench = await client.get("/static/bench-sheet.js")
    assert bench.status_code == 200
    # Design order without basket data; Kenny's basket order when the inventory
    # payload carries baskets (the node tests below check which one shows).
    assert "Order as designed" in bench.text
    assert "Basket order 1 to 17, largest pour first in each basket." in bench.text
    assert "bench-tick" in bench.text


def _run_bench_sheet(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the bench-sheet logic test needs it")
    program = f"const bench = require({json.dumps(str(BENCH_SHEET_JS))});\nprocess.stdout.write(JSON.stringify(({script})(bench)));"
    completed = subprocess.run([node, "-e", program], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(completed.stdout)


def _row(material, amount, unit="uL", **extra):
    return {
        "material": material, "stock_label": f"{material} stock", "stock_fraction_decimal": "0.005",
        "fraction_basis": "w/w", "carrier": "DPG", "amount_decimal": amount, "amount_unit": unit,
        "operation": "MASS_ADD" if unit == "mg" else "DIRECT_ADD", "execution_ready": True, **extra,
    }


def test_bench_sheet_writes_the_basis_as_w_w_or_v_v():
    rows = [
        _row("Ambrox Super", "840", stock_fraction_decimal="0.25", fraction_basis="mass_fraction"),
        _row("Bergamot", "100", stock_fraction_decimal="0.1", fraction_basis="volume_fraction", carrier="ethanol"),
        _row("Lavender EO", "1061", stock_fraction_decimal="1", fraction_basis="neat", carrier=None),
    ]
    strengths = _run_bench_sheet(
        "(b) => b.benchSheetLines(ROWS).lines.map((line) => line.strength)".replace("ROWS", json.dumps(rows))
    )

    assert strengths == ["25% w/w in DPG", "10% v/v in ethanol", "100% neat"]


def test_bench_sheet_logic_keeps_exact_per_unit_totals_and_flags_prepared_dilutions():
    rows = [
        _row("Iso E Super", "20.0"),
        _row("Ambrox crystals", "0.1", "mg"),
        _row("Hedione", "30", "\u00b5L"),
        _row("Cetalox", "0.2", "mg"),
        _row("Ethyl <b>Maltol</b>", "4", operation="PREPARED_DILUTION_REQUIRED", execution_ready=False),
        _row("Calone", "a few", "\u03bcL"),
        _row("Vetiver", "15"),
    ]
    critic = {"issues": ["ONE_OR_MORE_ROWS_REQUIRE_STOCK_OR_DILUTION_BINDING"]}
    result = _run_bench_sheet(
        "(b) => ({ sum: b.addDecimalText('0.1', '0.2'), lines: b.benchSheetLines(ROWS),"
        " hold: b.benchSheetHold(ROWS, CRITIC), clear: b.benchSheetHold([ROWS[0]], { issues: [] }),"
        " html: b.benchSheetHtml({ formulaName: 'Test <Iris>', variantLabel: 'B', dateText: 'today', totals: {}, rows: ROWS, critic: CRITIC }) })"
        .replace("ROWS", json.dumps(rows)).replace("CRITIC", json.dumps(critic))
    )

    assert result["sum"] == "0.3"
    lines = result["lines"]["lines"]
    assert [line["runningTotal"] for line in lines] == [
        "20 \u00b5L", "0.1 mg", "50 \u00b5L", "0.3 mg", None, "check by hand", "check by hand",
    ]
    assert [line["strength"] for line in lines][0] == "0.5% w/w in DPG"
    assert [line["amount"] for line in lines][:3] == ["20.0", "0.1", "30"]

    flagged = lines[4]
    assert flagged["pipettable"] is False
    assert flagged["mark"] == "Prepare a dilution first: 4 uL of this stock is under 10 uL, too small to pipette as written."
    assert result["lines"]["leftOut"] == 1
    assert [line["pipettable"] for line in lines] == [True, True, True, True, False, True, True]

    assert result["hold"] == {
        "onHold": True,
        "stateText": "Proposal \u00b7 check hold",
        "issues": ["one or more rows require stock or dilution binding"],
    }
    assert result["clear"]["stateText"] == "Proposal only"

    html = result["html"]
    body_rows = html.split("<tbody>", 1)[1].split("</tr>")[:-1]
    assert len(body_rows) == len(rows)
    assert "bench-tick" not in body_rows[4]
    assert "not in total" in body_rows[4]
    assert all("bench-tick" in row for index, row in enumerate(body_rows) if index != 4)
    assert "Running totals leave out 1 row that needs a prepared dilution first." in html
    assert "Proposal \u00b7 check hold" in html
    assert "Ethyl &lt;b&gt;Maltol&lt;/b&gt;" in html
    assert "<b>Maltol" not in html
    assert "Test &lt;Iris&gt; \u00b7 B" in html


_BASKET_INVENTORY = {
    "baskets": [{"number": number, "name": name} for number, name in (
        (1, "Always used"), (3, "Woods"), (6, "Musks"), (10, "Rose"),
    )],
    "stocks": [
        {"stock_id": "s-hed", "material": "Hedione", "basket": 1, "basket_status": "confirmed"},
        {"stock_id": "s-iso", "material": "Iso E Super", "basket": 1, "basket_status": "confirmed"},
        {"stock_id": "s-ced", "material": "Cedarwood Atlas", "basket": 3, "basket_status": "from_past_cards"},
        {"stock_id": "s-san", "material": "Sandalore", "basket": 3, "basket_status": "confirmed"},
        {"stock_id": "s-gal", "material": "Galaxolide", "identity_name": "Galaxolide 50", "basket": 6, "basket_status": "confirmed"},
        {"stock_id": "s-ros", "material": "Rose Oxide", "basket": 10, "basket_status": "confirmed"},
        {"stock_id": "s-new", "material": "Calone", "basket": None, "basket_status": "none"},
        {"stock_id": "s-cfl", "material": "Ambroxan", "basket": 1, "basket_status": "conflicting"},
    ],
}


def _basket_rows():
    return [
        _row("Rose Oxide", "30", stock_id="s-ros"),
        _row("Calone", "15", stock_id="s-new"),
        _row("Sandalore", "120", stock_id="s-san"),
        _row("Hedione", "40", stock_id="s-hed"),
        _row("Ethanol", "500", stock_id="s-eth", operation="PRECHARGE"),
        _row("Cedarwood Atlas", "120", stock_id="s-ced"),
        _row("Iso E Super", "250", stock_id="s-iso"),
        _row("galaxolide 50", "60.0"),
        _row("Ambroxan", "25", stock_id="s-cfl"),
        _row("Ambrox crystals", "0.5", "mg", stock_id="s-hed-mg", identity_name="Hedione"),
        _row("DPG", "80", stock_id="s-dpg"),
    ]


def test_basket_order_follows_kennys_baskets_and_pours_largest_first():
    rows = _basket_rows()
    result = _run_bench_sheet(
        "(b) => { const rows = ROWS; const lookup = b.benchBasketLookup(INV); const order = b.benchBasketOrder(rows, lookup);"
        " return { order: order.map((e) => [e.row.material, e.row.amount_decimal, e.basket, e.heading, e.check]),"
        " same: order.length === rows.length && order.every((e) => rows.includes(e.row)), legacy: b.benchBasketLookup({ stocks: INV.stocks }),"
        " plain: b.benchBasketOrder(rows, null).map((e) => [e.row.material, e.group]) }; }"
        .replace("ROWS", json.dumps(rows)).replace("INV", json.dumps(_BASKET_INVENTORY))
    )

    assert result["order"] == [
        # Carriers and solvents first, largest pour first.
        ["Ethanol", "500", None, "Carriers and solvents · pre-charge", False],
        ["DPG", "80", None, "Carriers and solvents · pre-charge", False],
        # Basket 1: uL high to low, then the mg solid matched by identity name.
        ["Iso E Super", "250", 1, "Basket 1 · Always used", False],
        ["Hedione", "40", 1, "Basket 1 · Always used", False],
        ["Ambrox crystals", "0.5", 1, "Basket 1 · Always used", False],
        # Basket 3: equal pours tie-break on name; one row from past cards flags the basket.
        ["Cedarwood Atlas", "120", 3, "Basket 3 · Woods", True],
        ["Sandalore", "120", 3, "Basket 3 · Woods", True],
        # Basket 6 reached by a case-insensitive identity-name match.
        ["galaxolide 50", "60.0", 6, "Basket 6 · Musks", False],
        ["Rose Oxide", "30", 10, "Basket 10 · Rose", False],
        # No basket yet (none assigned, or a conflicting assignment) comes last.
        ["Ambroxan", "25", None, "No basket yet", False],
        ["Calone", "15", None, "No basket yet", False],
    ]
    assert result["same"] is True
    assert result["legacy"] is None
    assert result["plain"] == [[row["material"], None] for row in rows]


def test_basket_order_never_changes_an_amount_and_keeps_a_postcharge_last():
    rows = _basket_rows() + [_row("Ethanol make-up", "900", operation="POSTCHARGE")]
    result = _run_bench_sheet(
        "(b) => { const rows = ROWS; const before = JSON.stringify(rows); const order = b.benchBasketOrder(rows, b.benchBasketLookup(INV));"
        " return { unchanged: JSON.stringify(rows) === before, last: order.at(-1).row.material, heading: order.at(-1).heading,"
        " amounts: order.map((e) => e.row.amount_decimal).sort() }; }"
        .replace("ROWS", json.dumps(rows)).replace("INV", json.dumps(_BASKET_INVENTORY))
    )

    assert result["unchanged"] is True
    assert result["last"] == "Ethanol make-up"
    assert result["heading"] == "Final make-up"
    assert result["amounts"] == sorted(row["amount_decimal"] for row in rows)


def test_pours_from_10_to_under_20_ul_are_flagged_for_a_one_to_one_dilution():
    rows = [
        _row("A", "9.99"), _row("B", "10"), _row("C", "19.999"), _row("D", "20"),
        _row("E", "15", "mg"), _row("F", "15", "µL"), _row("G", "12", operation="PREPARED_DILUTION_REQUIRED"),
    ]
    flags = _run_bench_sheet("(b) => ROWS.map((row) => b.benchSmallPour(row))".replace("ROWS", json.dumps(rows)))

    assert flags == [False, True, True, False, False, True, False]


def test_bench_sheet_follows_basket_order_with_headings_and_running_totals():
    rows = _basket_rows()
    result = _run_bench_sheet(
        "(b) => { const lookup = b.benchBasketLookup(INV);"
        " return { html: b.benchSheetHtml({ formulaName: 'T', dateText: 'd', totals: {}, rows: ROWS, critic: {}, basketLookup: lookup }),"
        " plain: b.benchSheetHtml({ formulaName: 'T', dateText: 'd', totals: {}, rows: ROWS, critic: {} }) }; }"
        .replace("ROWS", json.dumps(rows)).replace("INV", json.dumps(_BASKET_INVENTORY))
    )

    html = result["html"]
    assert "Basket order 1 to 17, largest pour first in each basket. Baskets marked &#39;check&#39; come from past cards." in html
    assert "Order as designed" not in html
    headings = [part.split("</th>", 1)[0] for part in html.split('<th colspan="6" scope="colgroup">')[1:]]
    assert headings == [
        "Carriers and solvents · pre-charge", "Basket 1 · Always used", "Basket 3 · Woods · check",
        "Basket 6 · Musks", "Basket 10 · Rose", "No basket yet",
    ]
    material_rows = [row for row in html.split("<tbody>", 1)[1].split("</tr>")[:-1] if "bench-basket-row" not in row]
    names = [row.split("<strong>", 1)[1].split("</strong>", 1)[0] for row in material_rows]
    assert names[:4] == ["Ethanol", "DPG", "Iso E Super", "Hedione"]
    # The running total follows the new pour order: 500, then 500 + 80, then + 250.
    assert ">580 µL<" in material_rows[1].replace("</td>", "<")
    assert ">830 µL<" in material_rows[2].replace("</td>", "<")
    calone = next(row for row in material_rows if "<strong>Calone</strong>" in row)
    assert "Under 20 µL: dilute 1:1 in ethanol, pipette double" in calone
    assert 'class="bench-basket-tag">Basket 1<' in material_rows[2]

    plain = result["plain"]
    assert "Order as designed. Use your own basket order at the balance." in plain
    assert "bench-basket-row" not in plain
    plain_names = [row.split("<strong>", 1)[1].split("</strong>", 1)[0] for row in plain.split("<tbody>", 1)[1].split("</tr>")[:-1]]
    assert plain_names == [row["material"] for row in rows]


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

    assert 'request(`/science/authority?view=${view}`, { timeoutMs: 0 })' in javascript.text
    assert 'scienceSections.replaceChildren(fragment)' in javascript.text
    assert "textContent" in javascript.text
    assert "strict_reason_codes" in javascript.text
    assert "evidence_class" in javascript.text
    assert "/api/v1/lab/science/report.md?view=" in javascript.text
    assert "confidence percentage" not in page.text.casefold()
    assert "confidence percentage" not in javascript.text.casefold()


@pytest.mark.asyncio
async def test_engine_job_wait_uses_current_server_states_and_failure_words(client):
    javascript = await client.get("/static/lab.js")

    assert "FAILED_CLOSED_WORKER_STOPPED" in javascript.text
    assert "the server restarted or shut down, so it has no result" in javascript.text
    # The same request coalesces onto the stopped job, so the page must not
    # promise that asking again re-runs it.
    assert "run it again" not in javascript.text.casefold()
    assert "EXPIRED" not in javascript.text


@pytest.mark.asyncio
async def test_omission_loader_translates_design_fraction_bases_and_shows_percentages(client):
    javascript = await client.get("/static/lab.js")

    assert javascript.status_code == 200
    assert 'mass_fraction: "w/w"' in javascript.text
    assert 'volume_fraction: "v/v"' in javascript.text
    assert 'mass_per_volume: "w/v"' in javascript.text
    assert 'OMISSION_BASIS[value] || "unknown"' in javascript.text
    assert "loaded.fraction_basis = omissionBasis(loaded.fraction_basis)" in javascript.text
    assert "omissionStrength(row)" in javascript.text
    assert "${row.stock_fraction_decimal} ${row.fraction_basis}" not in javascript.text


@pytest.mark.asyncio
async def test_comparison_planning_is_worded_as_a_suggestion_and_uses_safe_request_ids(client):
    page = await client.get("/app")
    javascript = await client.get("/static/lab.js")
    assert "cannot remove anything from your existing bottle" in page.text
    assert "needs separate samples" not in page.text
    submit = javascript.text.split('$("#omission-plan-form").addEventListener("submit"', 1)[1]
    submit = submit.split('$("#sample-form")', 1)[0]
    assert 'newRequestId("comparison")' in submit and "crypto.randomUUID()" not in submit


def test_bench_row_basket_trusts_the_stock_id_over_the_name():
    # Solution and crystals share the material name "Ambrox Super" but sit in different baskets.
    # The row is named like the crystals (a name that matches one stock on its own) yet carries
    # the solution's stock_id: the stock_id decides, so it lands in the solution's basket.
    inventory = {
        "baskets": [{"number": 3, "name": "Woods"}, {"number": 8, "name": "Ambers"}],
        "stocks": [
            {"stock_id": "s-sol", "material": "Ambrox Super", "identity_name": "Ambrox Super 25% w/w in DPG",
             "normalized_identity": "ambrox super", "basket": 3, "basket_status": "confirmed"},
            {"stock_id": "s-cry", "material": "Ambrox Super", "identity_name": "Ambrox Super crystals",
             "normalized_identity": "ambrox super crystals", "basket": 8, "basket_status": "confirmed"},
        ],
    }
    row = _row("Ambrox Super crystals", "40", stock_id="s-sol")
    result = _run_bench_sheet(
        "(b) => { const lookup = b.benchBasketLookup(INV);"
        " return { byId: b.benchRowBasket(ROW, lookup), byName: b.benchRowBasket({ ...ROW, stock_id: undefined }, lookup) }; }"
        .replace("INV", json.dumps(inventory)).replace("ROW", json.dumps(row))
    )

    assert result["byId"]["basket"] == 3
    assert result["byName"]["basket"] == 8  # without the stock_id the name still finds the crystals
