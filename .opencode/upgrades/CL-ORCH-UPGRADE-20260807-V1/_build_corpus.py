# Build the frozen benchmark corpus: 30 bounded packets grouped into 30 independent cases.
import json, hashlib, io, datetime, os

ROOT = r"D:\chatbots\perfume-chem"
U = os.path.join(ROOT, ".opencode", "upgrades", "CL-ORCH-UPGRADE-20260807-V1")


def sha(rel):
    p = os.path.join(ROOT, rel)
    b = open(p, "rb").read()
    return hashlib.sha256(b).hexdigest(), len(b)


SOURCES = {
    "inventory.txt": "inventory.txt",
    "odt": "engine/odor_thresholds.py",
    "intel": "engine/ingredient_intelligence.py",
    "gates": "engine/pipeline/gates.py",
    "concentration": "engine/units/concentration.py",
    "i_yaml": "data/materials/I.yaml",
    "families": "docs/fragrance_families_reference.md",
    "instructions": ".github/copilot-instructions.md",
}
src_hash = {k: sha(v) for k, v in SOURCES.items()}


def P(
    pid,
    cls,
    req,
    refs,
    allowed,
    prohibited,
    acceptance,
    abstention,
    timeout=90,
    maxout=2048,
    expected=None,
):
    return {
        "packet_id": pid,
        "task_class": cls,
        "decision_requested": req,
        "source_references": refs,
        "source_paths": [SOURCES[r] for r in refs],
        "ordered_source_sha256": [src_hash[r][0] for r in refs],
        "expected_deterministic_result": expected,
        "allowed_claims": allowed,
        "prohibited_claims": prohibited,
        "abstention_rule": abstention,
        "local_output_schema_identity": "cl_orch_packet_v1",
        "acceptance_rule": acceptance,
        "timeout_s": timeout,
        "max_output_tokens": maxout,
    }


packets = []
A = "Output must be JSON with decision/evidence/source_hashes/terminal_state."
# 1-5 source discovery
packets.append(
    P(
        "P001",
        "source_discovery",
        "Which inventory category header lists Galaxolide, and at what dilution?",
        ["inventory.txt"],
        ["category header", "dilution %"],
        ["inventing stock"],
        "evidence must quote the exact inventory line",
        A,
    )
)
packets.append(
    P(
        "P002",
        "source_discovery",
        "List the distinct citrus materials present in inventory.txt and their category.",
        ["inventory.txt"],
        ["material names", "category"],
        ["non-inventory materials"],
        "each citrus material must appear in inventory",
        A,
    )
)
packets.append(
    P(
        "P003",
        "source_discovery",
        "What is the reported stock dilution of Alpha Irone?",
        ["inventory.txt"],
        ["dilution %"],
        ["unstated dilution"],
        "must match inventory line exactly",
        A,
    )
)
packets.append(
    P(
        "P004",
        "source_discovery",
        "Which musk materials are listed in inventory and under which category header?",
        ["inventory.txt"],
        ["musk material list"],
        ["materials not in inventory"],
        "list must be a subset of inventory lines",
        A,
    )
)
packets.append(
    P(
        "P005",
        "source_discovery",
        "Is Osmanthus Absolute present in inventory? If yes, at what dilution?",
        ["inventory.txt"],
        ["present/absent", "dilution"],
        ["guessing dilution"],
        "presence claim must match inventory lines",
        A,
    )
)
# 6-10 code review
packets.append(
    P(
        "P006",
        "code_review",
        "Review the activity-coefficient defaulting path: may gamma ever silently become 1.0?",
        ["intel"],
        ["gamma handling description", "whether silent 1.0 is possible"],
        ["claiming default is 1.0 without evidence"],
        "finding must cite code lines",
        A,
    )
)
packets.append(
    P(
        "P007",
        "code_review",
        "Does ingredient_intelligence._PROFILES contain a VP for Hedione that differs from data YAML?",
        ["intel", "i_yaml"],
        ["stale VP finding or none"],
        ["inventing values"],
        "must quote both values",
        A,
    )
)
packets.append(
    P(
        "P008",
        "code_review",
        "Identify any duplicate ODT_DATA entries for 'hedione' and which entry wins.",
        ["odt"],
        ["duplicate count", "winner"],
        ["asserting no duplicates without checking"],
        "must count occurrences",
        A,
    )
)
packets.append(
    P(
        "P009",
        "code_review",
        "Does the note_map in gates.py use case-insensitive keys for pyramid lookup?",
        ["gates"],
        ["yes/no with line ref"],
        ["unverified claim"],
        "must cite the exact lookup line",
        A,
    )
)
packets.append(
    P(
        "P010",
        "code_review",
        "Review whether inventory_parser deduplicates by keeping the highest-dilution entry.",
        ["inventory.txt"],
        ["dedup behavior"],
        ["claiming unknown behavior"],
        "must reference parser semantics evidenced in repo",
        A,
    )
)
# 11-15 test diagnosis
packets.append(
    P(
        "P011",
        "test_diagnosis",
        "A pyramid gate shows T:0 H:100 B:0. Diagnose the most likely root cause.",
        ["gates"],
        ["root-cause hypothesis"],
        ["claiming a fix without evidence"],
        "hypothesis must map to code path",
        A,
    )
)
packets.append(
    P(
        "P012",
        "test_diagnosis",
        "A material reports 100M+ OAV. What is the most likely cause?",
        ["odt"],
        ["duplicate ODT cause"],
        ["normal physics"],
        "must reference ODT lookup behavior",
        A,
    )
)
packets.append(
    P(
        "P013",
        "test_diagnosis",
        "What failure mode does a material missing from ODT_DATA cause?",
        ["odt"],
        ["missing-key behavior"],
        ["crash without evidence"],
        "must cite lookup fallback",
        A,
    )
)
packets.append(
    P(
        "P014",
        "test_diagnosis",
        "Diagnose why --brief has no effect on perfume_knowledge pyramid gate.",
        ["gates"],
        ["brief resolution gap"],
        ["claiming brief works"],
        "must cite gate config path",
        A,
    )
)
packets.append(
    P(
        "P015",
        "test_diagnosis",
        "If concentrate total exceeds expected by header rows, what parser behavior is implicated?",
        ["inventory.txt"],
        ["row-parser inflation"],
        ["fabricated cause"],
        "must reference row parsing evidence",
        A,
    )
)
# 16-20 schema review
packets.append(
    P(
        "P016",
        "schema_review",
        "Is the concentration string '10%' acceptable per the repo's concentration-basis rule?",
        ["concentration"],
        ["declared basis requirement"],
        ["naked % accepted"],
        "must cite parse_concentration contract",
        A,
    )
)
packets.append(
    P(
        "P017",
        "schema_review",
        "Does material_properties.json record in_inventory for all 210 materials?",
        ["intel"],
        ["coverage finding"],
        ["asserting coverage without evidence"],
        "finding must be bounded to evidence",
        A,
    )
)
packets.append(
    P(
        "P018",
        "schema_review",
        "Review whether ODT_VERIFICATION and ODT_DATA both hold numeric ODT values.",
        ["odt"],
        ["both/one dict finding"],
        ["unverified claim"],
        "must reference both dicts",
        A,
    )
)
packets.append(
    P(
        "P019",
        "schema_review",
        "Does the packet require output schema fields decision/evidence/source_hashes/terminal_state?",
        ["instructions"],
        ["required fields"],
        ["claiming optional"],
        "must map to repo contract",
        A,
    )
)
packets.append(
    P(
        "P020",
        "schema_review",
        "Is a family archetype 'aromatic_fougere' available in the families registry?",
        ["families"],
        ["availability"],
        ["invented family"],
        "must match docs",
        A,
    )
)
# 21-25 authority comparison
packets.append(
    P(
        "P021",
        "authority_comparison",
        "Compare VP for Methyl Ionone Pure between ingredient_intelligence profile and data YAML.",
        ["intel", "i_yaml"],
        ["two values + agreement/disagreement"],
        ["using only one source"],
        "must quote both",
        A,
    )
)
packets.append(
    P(
        "P022",
        "authority_comparison",
        "Compare the ODT for Benzoin Resinoid in ODT_DATA against documented value 3.0 ppb.",
        ["odt"],
        ["stored vs 3.0"],
        ["asserting without lookup"],
        "must quote stored value",
        A,
    )
)
packets.append(
    P(
        "P023",
        "authority_comparison",
        "Do the families doc and the registry both support 'layton_dna'?",
        ["families"],
        ["both support / missing"],
        ["partial claim"],
        "must check both",
        A,
    )
)
packets.append(
    P(
        "P024",
        "authority_comparison",
        "Is Hedione ODT in ODT_DATA 0.05 ppb (the corrected value)?",
        ["odt"],
        ["yes/no value"],
        ["uncited value"],
        "must quote ODT_DATA entry",
        A,
    )
)
packets.append(
    P(
        "P025",
        "authority_comparison",
        "Compare Citrus category guidance in copilot-instructions vs families doc.",
        ["instructions", "families"],
        ["consistency finding"],
        ["inventing guidance"],
        "must quote both",
        A,
    )
)
# 26-28 synthesis
packets.append(
    P(
        "P026",
        "synthesis",
        "Synthesize the 3-4 material musk chord rule for a skin-scent accord from the guidance.",
        ["instructions"],
        ["chord axes"],
        ["ignoring guidance"],
        "must reflect guidance axes",
        A,
    )
)
packets.append(
    P(
        "P027",
        "synthesis",
        "Synthesize the sandalwood differentiation registers (dry vs creamy vs round).",
        ["instructions"],
        ["registers"],
        ["fabricated registers"],
        "must reflect guidance",
        A,
    )
)
packets.append(
    P(
        "P028",
        "synthesis",
        "Synthesize the local-first deterministic routing list into a compact classifier statement.",
        ["instructions"],
        ["deterministic ops"],
        ["omitting deterministic ops"],
        "must list the documented ops",
        A,
    )
)
# 29-30 adversarial audit
packets.append(
    P(
        "P029",
        "adversarial_audit",
        "Audit: could a formula label a character note with OAV<1 as perceptible?",
        ["instructions"],
        ["risk finding"],
        ["claiming it is fine"],
        "must apply OAV rule",
        A,
    )
)
packets.append(
    P(
        "P030",
        "adversarial_audit",
        "Audit: is 18% Hedione flagged as a crowding risk?",
        ["instructions"],
        ["crowding ceiling"],
        ["claiming no ceiling"],
        "must reflect documented ceiling",
        A,
    )
)

cases = []
for i, pk in enumerate(packets, start=1):
    cases.append(
        {
            "benchmark_case_id": f"CASE-{i:03d}",
            "task_class": pk["task_class"],
            "packet_ids": [pk["packet_id"]],
            "dependency_edges": [],
            "ordered_source_hashes": pk["ordered_source_sha256"],
            "acceptance_rule": pk["acceptance_rule"],
            "case_start_definition": "packet submitted as READ_ONLY job",
            "case_terminal_definition": "job reaches terminal verdict",
        }
    )

corpus = {
    "benchmark_corpus_id": "CL-BENCH-20260807-V1",
    "profiles": [
        "BASELINE_DIRECT_DEEPSEEK_CURRENT_SCHEDULER",
        "SAFE_NEW",
        "BALANCED_NEW",
        "TURBO_NEW",
    ],
    "packets": packets,
    "cases": cases,
    "source_hashes": src_hash,
}
body = json.dumps(corpus, sort_keys=True, ensure_ascii=True)
corpus["BENCHMARK_CORPUS_SHA256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
out = os.path.join(U, "evidence", "benchmark_corpus.json")
with io.open(out, "w", encoding="utf-8") as f:
    json.dump(corpus, f, indent=2, ensure_ascii=True)
print("CORPUS packets=" + str(len(packets)) + " cases=" + str(len(cases)))
print("BENCHMARK_CORPUS_SHA256=" + corpus["BENCHMARK_CORPUS_SHA256"])
