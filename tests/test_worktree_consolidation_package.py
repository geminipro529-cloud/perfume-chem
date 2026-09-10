"""Consolidation preservation is data, never implicit runtime admission."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'incoming_review/worktree_candidates'


def _records():
    manifest = json.loads((PACKAGE / 'manifest.json').read_text(encoding='utf-8'))
    ledger = json.loads((ROOT / manifest['ledger']).read_text(encoding='utf-8'))
    return manifest, ledger


def test_every_source_record_has_a_final_disposition_and_provenance():
    _, ledger = _records()
    assert len(ledger['sources']) == 19
    assert {s['source_index'] for s in ledger['sources']} == set(range(19))
    assert ledger['release_ready'] is False
    allowed = {'Integrated', 'Reconciled', 'Already present', 'Superseded',
               'Preserved disabled', 'Excluded', 'Deletion reconciled'}
    ids = set()
    for row in ledger['entries']:
        assert row['entry_id'] not in ids
        ids.add(row['entry_id'])
        assert row['source_index'] in range(19)
        assert row['disposition'] in allowed
        assert row['path'] and row['rationale'] and row['verification']
        assert row.get('recovery') or row['disposition'] == 'Deletion reconciled'
        if row['disposition'] == 'Preserved disabled':
            assert row['destination'].endswith('.payload')
            assert row['source_sha256']


def test_candidate_package_has_no_executable_entrypoints_and_exact_bytes():
    manifest, ledger = _records()
    assert manifest['runtime_enabled'] is False
    assert manifest['imports'] == manifest['routes'] == []
    assert manifest['payloads'] == ledger['payloads']
    expected = set()
    for record in manifest['payloads']:
        path = ROOT / record['path']
        assert path.resolve().is_relative_to(PACKAGE.resolve())
        assert path.name == record['sha256'] + '.payload'
        assert importlib.util.spec_from_file_location('candidate', path) is None
        raw = path.read_bytes()
        assert len(raw) == record['bytes']
        assert hashlib.sha256(raw).hexdigest() == record['sha256']
        expected.add(path.resolve())
    assert {p.resolve() for p in (PACKAGE / 'payloads').iterdir()} == expected
    assert not list(PACKAGE.rglob('*.py'))
    assert not list(PACKAGE.rglob('__init__.*'))


def test_disabled_records_resolve_to_packaged_content_without_hidden_imports():
    manifest, ledger = _records()
    by_path = {r['path']: r['sha256'] for r in manifest['payloads']}
    for row in ledger['entries']:
        if row['disposition'] == 'Preserved disabled':
            assert by_path[row['destination']] == row['source_sha256']
