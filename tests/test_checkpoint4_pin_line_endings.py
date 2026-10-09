import hashlib

from engine.experiments.checkpoint4_readiness import _pinned_bytes_match

CRLF_TEXT = b"<html>\r\n<body>pinned</body>\r\n</html>\r\n"
LF_TEXT = CRLF_TEXT.replace(b"\r\n", b"\n")
PIN = hashlib.sha256(CRLF_TEXT).hexdigest()


def test_lf_file_matches_pin_taken_on_crlf_form(tmp_path):
    path = tmp_path / "page.html"
    path.write_bytes(LF_TEXT)
    assert _pinned_bytes_match(path, PIN)


def test_crlf_file_matches_pin_taken_on_lf_form(tmp_path):
    path = tmp_path / "page.html"
    path.write_bytes(CRLF_TEXT)
    assert _pinned_bytes_match(path, hashlib.sha256(LF_TEXT).hexdigest())


def test_exact_bytes_match(tmp_path):
    path = tmp_path / "page.html"
    path.write_bytes(CRLF_TEXT)
    assert _pinned_bytes_match(path, PIN)


def test_one_changed_byte_is_rejected(tmp_path):
    path = tmp_path / "page.html"
    path.write_bytes(LF_TEXT.replace(b"pinned", b"pinneD"))
    assert not _pinned_bytes_match(path, PIN)


def test_bare_carriage_return_is_not_line_ending_equivalence(tmp_path):
    path = tmp_path / "page.html"
    path.write_bytes(LF_TEXT.replace(b"<body>", b"<body>\r"))
    assert not _pinned_bytes_match(path, PIN)
