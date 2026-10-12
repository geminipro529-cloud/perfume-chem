"""The pipeline audit log is moved aside when it gets large, and never loses events."""

from __future__ import annotations

from engine.pipeline import audit_log


def test_full_log_is_moved_aside_and_a_new_one_started(tmp_path, monkeypatch):
    log = tmp_path / "events.jsonl"
    monkeypatch.setenv(audit_log.MAX_BYTES_ENV, "300")
    for number in range(20):
        audit_log.append_event({"event_type": "gate_formula", "number": number}, log)

    archives = audit_log.archived_audit_paths(log)
    assert archives, "a log past the limit must be rotated"
    assert all(path.name.startswith("events-") and path.suffix == ".jsonl" for path in archives)
    assert log.stat().st_size < 300 + 200  # the current log restarted
    for archive in archives:
        assert archive.stat().st_size >= 300

    numbers = [event["number"] for event in audit_log.load_events(log)]
    assert numbers == list(range(20))  # oldest first, nothing lost or repeated


def test_small_log_is_left_alone(tmp_path):
    log = tmp_path / "events.jsonl"
    audit_log.append_event({"event_type": "gate_formula"}, log)
    assert audit_log.rotate_if_large(log, max_bytes=10_000) is None
    assert audit_log.archived_audit_paths(log) == []
    assert len(audit_log.load_events(log)) == 1


def test_default_limit_and_bad_setting(monkeypatch):
    monkeypatch.delenv(audit_log.MAX_BYTES_ENV, raising=False)
    assert audit_log.max_audit_bytes() == 20 * 1024 * 1024
    monkeypatch.setenv(audit_log.MAX_BYTES_ENV, "not-a-number")
    assert audit_log.max_audit_bytes() == 20 * 1024 * 1024


def test_other_logs_in_the_folder_are_not_read_as_archives(tmp_path):
    log = tmp_path / "events.jsonl"
    (tmp_path / "other.jsonl").write_text('{"event_type": "x"}\n', encoding="utf-8")
    (tmp_path / "events_backup.jsonl").write_text('{"event_type": "y"}\n', encoding="utf-8")
    audit_log.append_event({"event_type": "gate_formula"}, log)
    assert [event["event_type"] for event in audit_log.load_events(log)] == ["gate_formula"]
