"""Immutable local capture of a vendor CSV export, without feature mapping.

The raw bytes remain unmodified. The manifest records observable CSV shape and
provenance; it makes no claim that current vendor data was known in the past.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


PARSER_VERSION = "tr2-csv-snapshot-v1"


class SnapshotError(ValueError):
    """Input cannot be captured without misleading provenance."""


def _aware_utc(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotError("exported_at must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SnapshotError("exported_at must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _csv_shape(path: Path, delimiter: str) -> tuple[list[str], int]:
    if len(delimiter) != 1 or delimiter in ('"', "\r", "\n"):
        raise SnapshotError("delimiter must be a single CSV separator")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter, strict=True)
            header = next(reader, None)
            if not header or any(not name.strip() for name in header):
                raise SnapshotError("CSV must have a nonempty header")
            if len(header) != len(set(header)):
                raise SnapshotError("CSV contains duplicate column names")
            rows = 0
            for row in reader:
                if len(row) != len(header):
                    raise SnapshotError(f"CSV row {reader.line_num} has {len(row)} columns; expected {len(header)}")
                rows += 1
    except (UnicodeError, csv.Error) as exc:
        raise SnapshotError("CSV could not be parsed as UTF-8") from exc
    return header, rows


def capture_csv(
    source_file: str | Path,
    private_root: str | Path,
    *,
    exported_at: str,
    universe_definition: str,
    filters: str,
    source: str = "InvestingPro+",
    delimiter: str = ",",
) -> dict:
    """Capture one export, rejecting ambiguous provenance and malformed CSV.

    `private_root` must be outside the public tracked tree or inside an ignored
    private data directory. The caller owns access control and retention.
    """
    source_file = Path(source_file)
    private_root = Path(private_root)
    if not source_file.is_file() or source_file.suffix.lower() != ".csv":
        raise SnapshotError("source_file must be an existing CSV export")
    if not source.strip() or not universe_definition.strip() or not filters.strip():
        raise SnapshotError("source, universe_definition and filters are required")
    exported_at_utc = _aware_utc(exported_at)
    if datetime.fromisoformat(exported_at_utc.replace("Z", "+00:00")) > datetime.now(timezone.utc):
        raise SnapshotError("exported_at cannot be in the future")
    # Never allow a caller to accidentally place licensed exports in a
    # tracked directory of this public repository.
    repository_root = Path(__file__).resolve().parents[2]
    resolved_root = private_root.resolve()
    if resolved_root.is_relative_to(repository_root) and not resolved_root.is_relative_to(repository_root / "data" / "private"):
        raise SnapshotError("private_root inside this repository must be under data/private")
    digest = _hash_file(source_file)
    object_path = private_root / "objects" / digest[:2] / digest
    manifest_dir = private_root / "manifests"
    object_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    # Stage a copy, check its hash, then publish without replacing an existing
    # object. A second capture of identical bytes reuses the verified object.
    fd, staged_name = tempfile.mkstemp(prefix=".tr2-", dir=object_path.parent)
    try:
        with os.fdopen(fd, "wb") as staged, source_file.open("rb") as original:
            shutil.copyfileobj(original, staged)
            staged.flush()
            os.fsync(staged.fileno())
        staged_path = Path(staged_name)
        if _hash_file(staged_path) != digest:
            raise SnapshotError("source changed during capture")
        columns, row_count = _csv_shape(staged_path, delimiter)
        schema = hashlib.sha256(json.dumps(columns, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
        try:
            os.link(staged_path, object_path)
        except FileExistsError:
            if _hash_file(object_path) != digest:
                raise SnapshotError("existing object does not match its SHA256")
    finally:
        Path(staged_name).unlink(missing_ok=True)

    manifest = {
        "parser_version": PARSER_VERSION,
        "source": source,
        "original_filename": source_file.name,
        "sha256": digest,
        "schema_fingerprint": schema,
        "columns": columns,
        "row_count": row_count,
        "column_count": len(columns),
        "delimiter": delimiter,
        "universe_definition": universe_definition,
        "filters": filters,
        "exported_at": exported_at_utc,
        "snapshot_at": exported_at_utc,
        "ingested_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "object_relative_path": str(object_path.relative_to(private_root)),
    }
    manifest_name = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}-{digest[:12]}-{uuid4().hex}.json"
    manifest_path = manifest_dir / manifest_name
    with manifest_path.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return manifest | {"manifest_path": str(manifest_path)}


def _hash_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture an immutable private TR2 CSV export")
    parser.add_argument("source_file", type=Path)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--exported-at", required=True, help="ISO 8601 timestamp with timezone")
    parser.add_argument("--universe", required=True)
    parser.add_argument("--filters", required=True)
    parser.add_argument("--source", default="InvestingPro+")
    parser.add_argument("--delimiter", default=",")
    args = parser.parse_args()
    try:
        receipt = capture_csv(args.source_file, args.private_root, exported_at=args.exported_at,
                              universe_definition=args.universe, filters=args.filters,
                              source=args.source, delimiter=args.delimiter)
    except SnapshotError as exc:
        parser.error(str(exc))
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
