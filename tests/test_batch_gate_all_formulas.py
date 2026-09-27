from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import batch_gate_all_formulas as batch


def _gate_output(status: str = "PASS") -> dict:
    gates = []
    if status == "FAIL":
        gates = [{"gate": "test_failure", "status": "FAIL"}]
    return {"overall": status, "formulas": [{"gates": gates}]}


def _jobs(tmp_path: Path, count: int) -> list[batch.GateJob]:
    return [
        batch.GateJob(
            index=index,
            filepath=tmp_path / f"formula_{index}.md",
            concentrate_ul=1000 + index,
            brief=f"brief_{index}",
        )
        for index in range(count)
    ]


def test_run_gate_preserves_inputs_and_disables_all_worker_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    formula = tmp_path / "formula.md"
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            stdout=json.dumps(_gate_output()),
            stderr="",
            returncode=0,
        )

    monkeypatch.setattr(batch.subprocess, "run", fake_run)

    result = batch.run_gate(formula, 4321, "vetiver_woody", 17)

    assert result["overall"] == "PASS"
    assert captured["cmd"] == [
        sys.executable,
        str(batch.ROOT / "scripts" / "formula_release_gate.py"),
        "--formula-file",
        str(formula),
        "--expected-concentrate-ul",
        "4321",
        "--brief",
        "vetiver_woody",
        "--json",
        "--no-append-analysis",
        "--no-audit",
    ]
    assert captured["kwargs"] == {
        "capture_output": True,
        "text": True,
        "timeout": 17,
        "cwd": str(batch.ROOT),
        "env": batch._worker_environment(),
    }


def test_worker_environment_prevents_nested_numerical_oversubscription(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENBLAS_NUM_THREADS", "8")
    monkeypatch.setenv("UNRELATED_BATCH_SETTING", "preserved")

    environment = batch._worker_environment()

    assert environment["UNRELATED_BATCH_SETTING"] == "preserved"
    assert all(
        environment[key] == batch.WORKER_NUMERICAL_THREAD_LIMIT
        for key in batch._NUMERICAL_THREAD_ENV_KEYS
    )
    assert batch.WORKER_NUMERICAL_THREAD_LIMIT == "1"


def test_batch_runner_direct_cli_help_is_import_safe() -> None:
    result = subprocess.run(
        [sys.executable, str(batch.ROOT / "scripts" / "batch_gate_all_formulas.py"), "--help"],
        cwd=batch.ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0
    assert "Batch-gate all formula" in result.stdout


def test_valid_failure_json_is_not_misclassified_as_transport_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        batch.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout=json.dumps(_gate_output("FAIL")),
            stderr="",
            returncode=1,
        ),
    )

    result = batch.run_gate(tmp_path / "formula.md", 6000, "generic", 10)

    assert batch.classify_overall(result) == "FAIL"
    assert not result.get("_error")


def test_exact_family_archetype_uses_dedicated_gate_argument(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    formula = tmp_path / "formula.md"
    formula.write_text(
        "**Family archetype:** `citrus_classical.4711_reference`\n",
        encoding="utf-8",
    )
    job = batch.GateJob(
        index=0,
        filepath=formula,
        concentrate_ul=1700,
        brief=None,
    )
    captured: dict[str, object] = {}

    def fake_run_gate(
        filepath,
        concentrate_ul,
        brief,
        timeout_s,
        family_archetype=None,
    ):
        captured.update(
            filepath=filepath,
            concentrate_ul=concentrate_ul,
            brief=brief,
            timeout_s=timeout_s,
            family_archetype=family_archetype,
        )
        return _gate_output()

    monkeypatch.setattr(batch, "run_gate", fake_run_gate)

    execution = batch._execute_gate_job(job, timeout_s=120)

    assert captured["brief"] == "generic"
    assert captured["family_archetype"] == "citrus_classical.4711_reference"
    assert execution.family_archetype == "citrus_classical.4711_reference"


def test_metadata_is_resolved_immediately_before_the_one_gate_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    formula = tmp_path / "formula.md"
    formula.write_text("**Concentrate Volume:** 1,000 uL\n", encoding="utf-8")
    job = batch.GateJob(index=0, filepath=formula, concentrate_ul=None, brief=None)
    seen: list[tuple[int, str]] = []

    def fake_run_gate(filepath, concentrate_ul, brief, timeout_s):
        del filepath, timeout_s
        seen.append((concentrate_ul, brief))
        return _gate_output()

    monkeypatch.setattr(batch, "run_gate", fake_run_gate)
    executions = batch._ordered_gate_executions([job], timeout_s=5, workers=1)
    formula.write_text(
        "**Concentrate Volume:** 2,000 uL\n**Family archetype:** `vetiver_woody`\n",
        encoding="utf-8",
    )

    result = next(executions)

    assert seen == [(2000, "vetiver_woody")]
    assert result.concentrate_ul == 2000
    assert result.brief == "vetiver_woody"


def test_discovery_excludes_table_false_positive_rejected_by_authoritative_parser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    formulas_dir = tmp_path / "formulas"
    formulas_dir.mkdir()
    mixing_card = formulas_dir / "mixing_card.md"
    mixing_card.write_text(
        "| Material | Dilution | Amount |\n"
        "|---|---:|---:|\n"
        "| A | neat | 10 uL |\n"
        "| B | neat | 20 uL |\n"
        "| C | neat | 30 uL |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(batch, "ROOT", tmp_path)
    monkeypatch.setattr(batch, "FORMULAS_DIR", formulas_dir)
    monkeypatch.setattr(batch, "parse_formula_markdown", lambda _path: [])

    discovered, skipped = batch.discover_formula_files()

    assert discovered == []
    assert skipped == [
        {
            "file": str(Path("formulas") / "mixing_card.md"),
            "reason": "authoritative parser found no formulas",
        }
    ]


def test_discovery_excludes_collection_collapsed_to_duplicate_materials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    formulas_dir = tmp_path / "formulas"
    formulas_dir.mkdir()
    collection = formulas_dir / "collection.md"
    collection.write_text(
        "| Material | Dilution | Amount |\n"
        "|---|---:|---:|\n"
        "| A | neat | 10 uL |\n"
        "| a | neat | 20 uL |\n"
        "| C | neat | 30 uL |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(batch, "ROOT", tmp_path)
    monkeypatch.setattr(batch, "FORMULAS_DIR", formulas_dir)
    monkeypatch.setattr(
        batch,
        "parse_formula_markdown",
        lambda _path: [{"ingredients_ul": {"A": 10, "a": 20, "C": 30}}],
    )

    discovered, skipped = batch.discover_formula_files()

    assert discovered == []
    assert skipped == [
        {
            "file": str(Path("formulas") / "collection.md"),
            "reason": (
                "unsupported collection: parser produced duplicate material identities"
            ),
        }
    ]


def test_parallel_results_refill_and_yield_in_completion_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = _jobs(tmp_path, 2)
    second_completed = threading.Event()
    calls: list[str] = []
    completions: list[str] = []

    def fake_run_gate(filepath, concentrate_ul, brief, timeout_s):
        del concentrate_ul, brief, timeout_s
        calls.append(filepath.stem)
        if filepath == jobs[0].filepath:
            assert second_completed.wait(timeout=2)
        else:
            second_completed.set()
        completions.append(filepath.stem)
        return _gate_output()

    monkeypatch.setattr(batch, "run_gate", fake_run_gate)

    results = list(batch._ordered_gate_executions(jobs, timeout_s=5, workers=2))

    assert sorted(calls) == ["formula_0", "formula_1"]
    assert completions == ["formula_1", "formula_0"]
    assert [result.job.index for result in results] == [1, 0]


def test_parallel_lane_is_refilled_before_caller_consumes_next_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = _jobs(tmp_path, 3)
    release_second = threading.Event()
    third_started = threading.Event()

    def fake_execute(job, timeout_s):
        del timeout_s
        if job.index == 1:
            assert release_second.wait(timeout=2)
        if job.index == 2:
            third_started.set()
        return batch.GateExecution(
            job=job,
            concentrate_ul=job.concentrate_ul or batch.DEFAULT_CONCENTRATE_UL,
            brief=job.brief or batch.DEFAULT_BRIEF,
            gate_output=_gate_output(),
            elapsed_s=0.1,
        )

    monkeypatch.setattr(batch, "_execute_gate_job", fake_execute)

    executions = batch._ordered_gate_executions(jobs, timeout_s=5, workers=2)
    first = next(executions)

    assert first.job.index == 0
    assert third_started.wait(timeout=1)
    release_second.set()
    assert sorted(result.job.index for result in executions) == [1, 2]


def test_workers_one_uses_direct_serial_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = _jobs(tmp_path, 3)
    calls: list[int] = []

    class ForbiddenExecutor:
        def __init__(self, *args, **kwargs):
            del args, kwargs
            raise AssertionError("workers=1 must not construct a thread pool")

    def fake_run_gate(filepath, concentrate_ul, brief, timeout_s):
        del filepath, brief, timeout_s
        calls.append(concentrate_ul)
        return _gate_output()

    monkeypatch.setattr(batch, "ThreadPoolExecutor", ForbiddenExecutor)
    monkeypatch.setattr(batch, "run_gate", fake_run_gate)

    results = list(batch._ordered_gate_executions(jobs, timeout_s=5, workers=1))

    assert calls == [1000, 1001, 1002]
    assert [result.job.index for result in results] == [0, 1, 2]


def test_unexpected_future_exception_isolated_to_its_formula(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = _jobs(tmp_path, 2)
    calls: list[int] = []

    def fake_execute(job, timeout_s):
        del timeout_s
        calls.append(job.index)
        if job.index == 0:
            raise RuntimeError("unexpected worker failure")
        return batch.GateExecution(
            job=job,
            concentrate_ul=job.concentrate_ul or batch.DEFAULT_CONCENTRATE_UL,
            brief=job.brief or batch.DEFAULT_BRIEF,
            gate_output=_gate_output(),
            elapsed_s=0.1,
        )

    monkeypatch.setattr(batch, "_execute_gate_job", fake_execute)

    results = list(batch._ordered_gate_executions(jobs, timeout_s=5, workers=2))

    assert sorted(calls) == [0, 1]
    assert results[0].job == jobs[0]
    assert results[0].gate_output["_error_type"] == "exception"
    assert results[0].gate_output["_exception"] == "unexpected worker failure"
    assert results[1].gate_output["overall"] == "PASS"


def test_timeout_and_exception_are_isolated_without_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = _jobs(tmp_path, 3)
    calls: list[str] = []

    def fake_subprocess_run(cmd, **kwargs):
        del kwargs
        formula = Path(cmd[cmd.index("--formula-file") + 1])
        calls.append(formula.stem)
        if formula == jobs[0].filepath:
            raise subprocess.TimeoutExpired(cmd, 5)
        if formula == jobs[1].filepath:
            raise OSError("isolated test failure")
        return SimpleNamespace(
            stdout=json.dumps(_gate_output()),
            stderr="",
            returncode=0,
        )

    monkeypatch.setattr(batch.subprocess, "run", fake_subprocess_run)

    results = list(batch._ordered_gate_executions(jobs, timeout_s=5, workers=3))

    assert sorted(calls) == ["formula_0", "formula_1", "formula_2"]
    results_by_index = {result.job.index: result for result in results}
    assert results_by_index[0].gate_output == {
        "_error": True,
        "_error_type": "timeout",
        "_timeout_s": 5,
    }
    assert results_by_index[1].gate_output["_error_type"] == "exception"
    assert results_by_index[1].gate_output["_exception"] == "isolated test failure"
    assert results_by_index[2].gate_output["overall"] == "PASS"


def test_main_writes_isolated_deterministic_manifest_and_ignores_stale_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    formulas_dir = tmp_path / "formulas"
    output_dir = tmp_path / "results"
    formulas_dir.mkdir()
    output_dir.mkdir()
    first = formulas_dir / "z_first.md"
    second = formulas_dir / "a_second.md"
    first.write_text(
        "**Concentrate Volume:** 1,500 uL\n**Family archetype:** `vetiver_woody`\n",
        encoding="utf-8",
    )
    second.write_text("no metadata\n", encoding="utf-8")
    stale = output_dir / "z_first.json"
    stale.write_text('{"stale": true}', encoding="utf-8")

    second_completed = threading.Event()
    calls: list[tuple[Path, int, str, int]] = []

    def fake_run_gate(filepath, concentrate_ul, brief, timeout_s):
        calls.append((filepath, concentrate_ul, brief, timeout_s))
        if filepath == first:
            assert second_completed.wait(timeout=2)
            return _gate_output("PASS")
        second_completed.set()
        return _gate_output("FAIL")

    monkeypatch.setattr(batch, "ROOT", tmp_path)
    monkeypatch.setattr(batch, "FORMULAS_DIR", formulas_dir)
    monkeypatch.setattr(batch, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(batch, "discover_formula_files", lambda: ([first, second], []))
    monkeypatch.setattr(batch, "run_gate", fake_run_gate)

    assert (
        batch.main(
            [
                "--workers",
                "2",
                "--timeout",
                "9",
                "--execution-mode",
                "isolated",
            ]
        )
        == 0
    )

    run_dirs = [path for path in output_dir.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert [row["file"] for row in summary["formulas"]] == [
        "formulas/z_first.md",
        "formulas/a_second.md",
    ]
    assert [row["status"] for row in summary["formulas"]] == ["PASS", "FAIL"]
    assert summary["config"]["workers"] == 2
    assert summary["config"]["execution_mode"] == "isolated"
    assert summary["config"]["worker_audit"] == "DISABLED"
    assert summary["memory"]["measurement_state"] in {
        "MEASURED_PROCESS_TREE_RSS",
        "UNAVAILABLE_DEPENDENCY",
    }
    assert sorted((path.name, conc, brief, timeout) for path, conc, brief, timeout in calls) == [
        ("a_second.md", batch.DEFAULT_CONCENTRATE_UL, batch.DEFAULT_BRIEF, 9),
        ("z_first.md", 1500, "vetiver_woody", 9),
    ]
    assert json.loads(stale.read_text(encoding="utf-8")) == {"stale": True}
    manifest = json.loads(
        (run_dir / "result_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["source_drift"] is False
    assert [row["discovery_index"] for row in manifest["entries"]] == [0, 1]
    assert all(
        len(row["scientific_payload_sha256"]) == 64
        and len(row["authority_payload_sha256"]) == 64
        for row in manifest["entries"]
    )
    assert len(list(run_dir.glob("*.json"))) == 6


def test_safe_output_name_includes_source_path_digest(tmp_path: Path) -> None:
    first = batch.FORMULAS_DIR / "a" / "same.md"
    second = batch.FORMULAS_DIR / "b" / "same.md"

    first_name = batch._safe_name(first)
    second_name = batch._safe_name(second)

    assert first_name != second_name
    assert len(first_name.rsplit("__", 1)[1]) == 12
    assert len(second_name.rsplit("__", 1)[1]) == 12


def test_each_invocation_gets_a_new_empty_output_directory(tmp_path: Path) -> None:
    first = batch.create_run_output_dir(tmp_path)
    (first / "sentinel").write_text("old", encoding="utf-8")
    second = batch.create_run_output_dir(tmp_path)

    assert first != second
    assert list(second.iterdir()) == []


def test_scientific_and_authority_hashes_ignore_only_execution_metadata() -> None:
    first = {
        "overall": "PASS",
        "runtime_observability": {
            "total_pre_output_ms": 1.0,
            "stage_ms": {"oav_authority": 2.0},
        },
        "run_evidence_contract": {
            "generated_at_utc": "first",
            "artifact_sha256": "a" * 64,
            "status": "ADVISORY_ONLY",
        },
        "formula": {
            "authority": {"release_authority": False},
            "scientific_value": 1.25,
        },
    }
    second = {
        **first,
        "runtime_observability": {
            "total_pre_output_ms": 999.0,
            "stage_ms": {"oav_authority": 888.0},
        },
        "run_evidence_contract": {
            "generated_at_utc": "second",
            "artifact_sha256": "b" * 64,
            "status": "ADVISORY_ONLY",
        },
    }

    assert batch.scientific_payload_sha256(first) == batch.scientific_payload_sha256(
        second
    )
    assert batch.authority_payload_sha256(first) == batch.authority_payload_sha256(
        second
    )
    assert batch.scientific_and_authority_payload_hashes(first) == (
        batch.scientific_payload_sha256(first),
        batch.authority_payload_sha256(first),
    )
    changed = {**second, "formula": {**second["formula"], "scientific_value": 2.0}}
    assert batch.scientific_payload_sha256(first) != batch.scientific_payload_sha256(
        changed
    )


@pytest.mark.parametrize("raw", ["0", str(batch.MAX_WORKERS + 1), "not-an-int"])
def test_worker_count_rejects_values_outside_the_bound(raw: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        batch._parse_worker_count(raw)


def test_worker_defaults_and_inclusive_bounds() -> None:
    assert batch.DEFAULT_WORKERS == 4
    assert batch._parse_worker_count("1") == 1
    assert batch._parse_worker_count(str(batch.MAX_WORKERS)) == batch.MAX_WORKERS


def test_persistent_lanes_reuse_workers_and_run_each_formula_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = _jobs(tmp_path, 6)
    instances = []

    class FakePersistentWorker:
        def __init__(self, *, startup_timeout_s: int) -> None:
            self.startup_timeout_s = startup_timeout_s
            self.calls: list[str] = []
            self.closed = False
            self.ready_receipt = {
                "repository_evidence_hashes": {
                    "inventory_sha256": "a" * 64,
                    "scientific_inputs_sha256": "b" * 64,
                    "pipeline_source_sha256": "c" * 64,
                },
                "repository_commit": "d" * 40,
            }
            instances.append(self)

        def run_gate(
            self,
            filepath,
            concentrate_ul,
            brief,
            timeout_s,
            family_archetype=None,
        ):
            del concentrate_ul, brief, timeout_s, family_archetype
            self.calls.append(filepath.stem)
            return _gate_output()

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(batch, "PersistentGateWorker", FakePersistentWorker)

    results = list(
        batch._ordered_gate_executions(
            jobs,
            timeout_s=11,
            workers=2,
            persistent=True,
        )
    )

    assert len(instances) == 2
    assert all(instance.startup_timeout_s == 30 for instance in instances)
    assert all(instance.closed for instance in instances)
    assert sorted(
        stem for instance in instances for stem in instance.calls
    ) == [f"formula_{index}" for index in range(6)]
    assert sorted(result.job.index for result in results) == list(range(6))
    assert all(result.gate_output["overall"] == "PASS" for result in results)


def test_persistent_worker_snapshot_disagreement_fails_closed_without_jobs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = _jobs(tmp_path, 2)
    instances = []

    class DivergentPersistentWorker:
        def __init__(self, *, startup_timeout_s: int) -> None:
            del startup_timeout_s
            marker = str(len(instances)) * 64
            self.ready_receipt = {
                "repository_evidence_hashes": {
                    "inventory_sha256": marker,
                    "scientific_inputs_sha256": "b" * 64,
                    "pipeline_source_sha256": "c" * 64,
                },
                "repository_commit": "d" * 40,
            }
            self.closed = False
            self.called = False
            instances.append(self)

        def run_gate(self, *args, **kwargs):
            del args, kwargs
            self.called = True
            return _gate_output()

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(batch, "PersistentGateWorker", DivergentPersistentWorker)

    results = list(
        batch._ordered_gate_executions(
            jobs,
            timeout_s=5,
            workers=2,
            persistent=True,
        )
    )

    assert all(result.gate_output["_error_type"] == "worker_startup" for result in results)
    assert all("same repository snapshot" in result.gate_output["_exception"] for result in results)
    assert all(instance.closed and not instance.called for instance in instances)


def test_process_tree_memory_monitor_returns_bounded_receipt() -> None:
    monitor = batch.ProcessTreeMemoryMonitor(interval_s=0.001)
    monitor.start()
    receipt = monitor.stop()

    if monitor.available:
        assert receipt["measurement_state"] == "MEASURED_PROCESS_TREE_RSS"
        assert receipt["peak_rss_bytes"] > 0
        assert receipt["peak_rss_mib"] > 0
        assert receipt["sample_count"] >= 2
    else:
        assert receipt == {
            "measurement_state": "UNAVAILABLE_DEPENDENCY",
            "peak_rss_bytes": None,
            "peak_rss_mib": None,
            "sample_count": 0,
            "sample_errors": 0,
        }


def test_release_gate_jsonl_worker_reuses_one_bound_snapshot_and_stays_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import formula_release_gate as release_gate

    formulas_dir = tmp_path / "formulas"
    formulas_dir.mkdir()
    formula = formulas_dir / "bounded.md"
    formula.write_text("bounded test formula", encoding="utf-8")
    evidence = {
        "inventory_sha256": "a" * 64,
        "scientific_inputs_sha256": "b" * 64,
        "pipeline_source_sha256": "c" * 64,
    }
    evidence_calls = 0
    main_calls = []

    def fake_evidence_hashes():
        nonlocal evidence_calls
        evidence_calls += 1
        return evidence

    def fake_main(
        argv,
        *,
        repository_evidence_hashes=None,
        repository_commit=None,
    ):
        main_calls.append(
            (list(argv), dict(repository_evidence_hashes), repository_commit)
        )
        print(json.dumps(_gate_output()))
        return 0

    monkeypatch.setattr(release_gate, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        release_gate,
        "current_repository_evidence_hashes",
        fake_evidence_hashes,
    )
    monkeypatch.setattr(release_gate, "_repository_commit", lambda: "d" * 40)
    monkeypatch.setattr(release_gate, "main", fake_main)

    argv = [
        "--formula-file",
        str(formula),
        "--expected-concentrate-ul",
        "6000",
        "--brief",
        "generic",
        "--json",
        "--no-append-analysis",
        "--no-audit",
    ]
    requests = [
        {
            "schema": release_gate._BATCH_WORKER_SCHEMA,
            "type": "RUN",
            "request_id": "one",
            "argv": argv,
        },
        {
            "schema": release_gate._BATCH_WORKER_SCHEMA,
            "type": "RUN",
            "request_id": "two",
            "argv": argv,
        },
        {
            "schema": release_gate._BATCH_WORKER_SCHEMA,
            "type": "SHUTDOWN",
            "request_id": "stop",
        },
    ]
    source = io.StringIO("".join(json.dumps(row) + "\n" for row in requests))
    sink = io.StringIO()

    assert release_gate._batch_worker_jsonl(source, sink) == 0

    receipts = [json.loads(line) for line in sink.getvalue().splitlines()]
    assert [row["type"] for row in receipts] == [
        "READY",
        "RESULT",
        "RESULT",
        "STOPPED",
    ]
    assert evidence_calls == 1
    assert len(main_calls) == 2
    assert all(call[1] == evidence and call[2] == "d" * 40 for call in main_calls)
    assert all(row["gate_output"]["overall"] == "PASS" for row in receipts[1:3])
    assert all(
        len(row["scientific_payload_sha256"]) == 64
        and len(row["authority_payload_sha256"]) == 64
        for row in receipts[1:3]
    )
    assert list(tmp_path.rglob("*")) == [formulas_dir, formula]


def test_release_gate_jsonl_worker_rejects_write_capable_or_unknown_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import formula_release_gate as release_gate

    formulas_dir = tmp_path / "formulas"
    formulas_dir.mkdir()
    formula = formulas_dir / "bounded.md"
    formula.write_text("bounded test formula", encoding="utf-8")
    monkeypatch.setattr(release_gate, "PROJECT_ROOT", tmp_path)

    base = [
        "--formula-file",
        str(formula),
        "--expected-concentrate-ul",
        "6000",
        "--brief",
        "generic",
        "--json",
        "--no-append-analysis",
        "--no-audit",
    ]
    assert release_gate._validate_batch_worker_argv(base) == base
    with pytest.raises(ValueError, match="Unsupported batch worker option"):
        release_gate._validate_batch_worker_argv([*base, "--append-analysis"])
    with pytest.raises(ValueError, match="Unsupported batch worker option"):
        release_gate._validate_batch_worker_argv([*base, "--some-module", "unsafe"])


def test_persistent_worker_timeout_kills_lane_and_does_not_retry(
    tmp_path: Path,
) -> None:
    class FakeProcess:
        pid = 12345

        def __init__(self) -> None:
            self.stdin = io.StringIO()

        @staticmethod
        def poll():
            return None

    worker = object.__new__(batch.PersistentGateWorker)
    worker._process = FakeProcess()
    worker._sequence = 0
    terminations = []

    def timeout_receipt(_timeout_s):
        raise TimeoutError("bounded timeout")

    worker._next_receipt = timeout_receipt
    worker._terminate = lambda: terminations.append(True)

    result = worker.run_gate(
        tmp_path / "formula.md",
        6000,
        "generic",
        7,
    )

    assert result == {
        "_error": True,
        "_error_type": "timeout",
        "_timeout_s": 7,
    }
    assert terminations == [True]
    assert worker._sequence == 1
    assert worker._process.stdin.getvalue().count("\n") == 1


def test_live_worker_pipe_round_trips_unicode_request_ids() -> None:
    process = subprocess.Popen(
        [
            sys.executable,
            str(batch.ROOT / "scripts" / "formula_release_gate.py"),
            "--batch-worker-jsonl",
        ],
        cwd=batch.ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    try:
        assert process.stdout is not None
        assert process.stdin is not None
        ready = json.loads(process.stdout.readline())
        assert ready["type"] == "READY"
        process.stdin.write(
            json.dumps(
                {
                    "schema": batch.PERSISTENT_WORKER_SCHEMA,
                    "type": "SHUTDOWN",
                    "request_id": "Lavande_Sèche_ทดสอบ",
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        process.stdin.flush()
        stopped = json.loads(process.stdout.readline())
        assert stopped == {
            "schema": batch.PERSISTENT_WORKER_SCHEMA,
            "type": "STOPPED",
            "request_id": "Lavande_Sèche_ทดสอบ",
        }
        assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
