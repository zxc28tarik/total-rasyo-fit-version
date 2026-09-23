"""A licensed export must be copied faithfully and never enter tracked files."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tr2.ingest import SnapshotError, capture_csv


def _capture(source: Path, root: Path, **changes):
    args = dict(exported_at="2026-09-23T15:30:00+03:00",
                universe_definition="BIST primary shares", filters="Trading Region: Turkey")
    return capture_csv(source, root, **(args | changes))


def test_raw_bytes_and_two_snapshots_are_immutable(tmp_path):
    source = tmp_path / "export.csv"
    raw = b"ticker,value\r\nABC,1\r\nDEF,2\r\n"
    source.write_bytes(raw)
    root = tmp_path / "private"
    first = _capture(source, root)
    second = _capture(source, root)
    assert first["sha256"] == hashlib.sha256(raw).hexdigest()
    assert (root / first["object_relative_path"]).read_bytes() == raw
    assert first["row_count"] == 2 and first["column_count"] == 2
    assert first["columns"] == ["ticker", "value"]
    assert first["exported_at"] == "2026-09-23T12:30:00Z"
    assert first["manifest_path"] != second["manifest_path"]
    assert json.loads(Path(first["manifest_path"]).read_text())["sha256"] == first["sha256"]
    source.write_text("ticker,value\nABC,9\n")
    assert (root / first["object_relative_path"]).read_bytes() == raw
    assert _capture(source, root)["sha256"] != first["sha256"]


@pytest.mark.parametrize("raw", [b"ticker,value\nABC\n", b"ticker,ticker\nABC,1\n",
                                      b"ticker,value\nABC,1,extra\n", b"\xff\xfe"])
def test_malformed_export_never_gets_manifest(tmp_path, raw):
    source = tmp_path / "bad.csv"
    source.write_bytes(raw)
    root = tmp_path / "private"
    with pytest.raises(SnapshotError):
        _capture(source, root)
    assert not list((root / "manifests").glob("*.json"))


def test_missing_time_zone_and_unsafe_repository_location_rejected(tmp_path):
    source = tmp_path / "export.csv"
    source.write_text("ticker,value\nABC,1\n")
    with pytest.raises(SnapshotError, match="timezone"):
        _capture(source, tmp_path / "private", exported_at="2026-09-23T15:30:00")
    with pytest.raises(SnapshotError, match="future"):
        _capture(source, tmp_path / "private", exported_at="2999-01-01T00:00:00Z")
    repo_root = Path(__file__).resolve().parents[2]
    with pytest.raises(SnapshotError, match="data/private"):
        _capture(source, repo_root / "research" / "vendor")


def test_csv_separator_and_schema_fingerprint(tmp_path):
    source = tmp_path / "export.csv"
    source.write_text("ticker;value\nABC;1\n")
    root = tmp_path / "private"
    receipt = _capture(source, root, delimiter=";")
    assert receipt["columns"] == ["ticker", "value"]
    assert receipt["row_count"] == 1
    assert len(receipt["schema_fingerprint"]) == 64
