#!/usr/bin/env python3
"""Losslessly package and verify the retained successful and failed SQL queries.

Only ``build`` reads the optional local queries/ cache. ``verify_archive`` reads
the committed ZIP and manifest, so CI needs no cache and makes no network calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import zipfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREFIX = "research/unit_resolution_followup"
ARCHIVE = "queries_evidence.zip"
MANIFEST = "queries_archive_manifest.json"
SUFFIXES = {".sql": "submitted_sql", ".json": "raw_http_response",
            ".provenance.json": "original_provenance"}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def query_metadata(batch_id: str, payloads: dict[str, bytes]) -> dict:
    """Validate original provenance against its exact SQL and response bytes."""
    paths = {suffix: f"queries/{batch_id}{suffix}" for suffix in SUFFIXES}
    meta = json.loads(payloads[paths[".provenance.json"]])
    query = meta["query"]
    assert sha_bytes(query.encode())[:20] == batch_id, (batch_id, "query key")
    assert payloads[paths[".sql"]] == (query + "\n").encode(), (batch_id, "SQL bytes")
    raw = payloads[paths[".json"]]
    assert sha_bytes(raw) == meta["sha256"] and len(raw) == meta["bytes"], batch_id
    assert meta["radius_arcmin"] == 0.5
    rows = meta["row_indices"]
    assert rows and len(rows) == len(set(rows)) and all(type(i) is int for i in rows)
    response = json.loads(raw)
    if meta["status"] == "ok":
        assert meta["http_status"] == 200 and "FROM (VALUES " in query
        assert isinstance(response, list)
        data = [row for table in response for row in table["Rows"] if "row_index" in row]
        assert len(data) == meta["observation_rows"]
        assert {row["row_index"] for row in data} <= set(rows)
        assert all(isinstance(row["specobjid"], str) and row["specobjid"].isdecimal()
                   for row in data)
        # SkyServer includes a separate SqlQuery metadata row. It is preserved,
        # but is not an additional spectrum or a catalogue observation.
        server_queries = [row["query"] for table in response
                          if table["TableName"] == "SqlQuery" for row in table["Rows"]]
        assert server_queries == [query]
        meaning = "successful_values_query"
        count = len(data)
    else:
        assert meta["status"] == "failed" and meta["http_status"] == 500
        assert " UNION ALL SELECT " in query and isinstance(response, dict)
        assert response["ErrorCode"] == 500
        assert "Incorrect syntax near 'ALL#SELECT'" in response["ErrorMessage"]
        meaning = "initial_union_syntax_error"
        count = None  # Failure is not a zero-result catalogue search.
    return dict(batch_id=batch_id, query_status=meta["status"], interpretation=meaning,
                row_indices=rows, radius_arcmin=meta["radius_arcmin"],
                http_status=meta["http_status"], retrieved_utc=meta["retrieved_utc"],
                sql_path=paths[".sql"], response_path=paths[".json"],
                provenance_path=paths[".provenance.json"], observation_rows=count)


def semantic_summary(batches: list[dict]) -> dict:
    counts = Counter(row["query_status"] for row in batches)
    assert counts == {"ok": 79, "failed": 79}
    grouped = {status: [tuple(row["row_indices"]) for row in batches
                        if row["query_status"] == status] for status in counts}
    assert set(grouped["ok"]) == set(grouped["failed"])
    assert len(set(grouped["ok"])) == 79
    target_rows = [i for batch in grouped["ok"] for i in batch]
    assert len(target_rows) == len(set(target_rows)) == 1579
    observation_rows = sum(row["observation_rows"] for row in batches
                           if row["query_status"] == "ok")
    assert observation_rows == 2175
    return dict(query_attempts=158, successful_queries=79, initial_failed_queries=79,
                paired_input_batches=79, input_record_indices=1579,
                successful_observation_rows=observation_rows,
                failed_queries_are_not_nondetections=True)


def verify_archive(base: Path) -> dict:
    """Verify the durable bundle alone, including every original byte and status."""
    base = Path(base).resolve()
    manifest = json.loads((base / MANIFEST).read_text())
    assert manifest["schema_version"] == 1 and manifest["archive_path"] == ARCHIVE
    archive_bytes = (base / ARCHIVE).read_bytes()
    assert sha_bytes(archive_bytes) == manifest["archive_sha256"]
    assert len(archive_bytes) == manifest["archive_bytes"]
    entries = manifest["entries"]
    names = [entry["archive_entry"] for entry in entries]
    assert len(names) == len(set(names)) == 474 and names == sorted(names)
    with zipfile.ZipFile(base / ARCHIVE) as archive:
        assert archive.namelist() == names
        assert archive.testzip() is None
        payloads = {name: archive.read(name) for name in names}
        for entry in entries:
            name = entry["archive_entry"]
            assert re.fullmatch(r"queries/[0-9a-f]{20}(?:\.provenance)?\.(?:sql|json)", name)
            assert entry["original_path"] == f"{PREFIX}/{name}"
            assert len(payloads[name]) == entry["bytes"]
            assert sha_bytes(payloads[name]) == entry["sha256"]
    batch_ids = sorted({entry["batch_id"] for entry in entries})
    batches = [query_metadata(batch_id, payloads) for batch_id in batch_ids]
    assert batches == manifest["batches"]
    by_id = {row["batch_id"]: row for row in batches}
    for entry in entries:
        row = by_id[entry["batch_id"]]
        assert entry["query_status"] == row["query_status"]
        name = entry["archive_entry"]
        suffix = name.removeprefix(f"queries/{entry['batch_id']}")
        assert entry["role"] == SUFFIXES[suffix]
    summary = semantic_summary(batches)
    assert summary == manifest["query_summary"]
    assert sum(entry["bytes"] for entry in entries) == manifest["uncompressed_bytes"]
    # The historical list contains both the failed attempts and the subsequent
    # successful attempts. Its paths are archive member names, not CI files.
    catalogue = json.loads((base / "catalogue_summary.json").read_text())
    provenance = sorted(row["provenance_path"] for row in batches)
    assert catalogue["batch_provenance_files"] == provenance
    assert catalogue["query_batches"] == catalogue["successful_batches"] == 79
    assert catalogue["historical_query_attempts"] == 158
    assert catalogue["successful_historical_query_attempts"] == 79
    assert catalogue["initial_union_failed_query_attempts"] == 79
    assert catalogue["catalogue_observation_rows"] == summary["successful_observation_rows"]
    verified = {f"{PREFIX}/{name}": sha_bytes((base / name).read_bytes()) for name in
                [ARCHIVE, MANIFEST, "archive_queries.py", "catalogue_summary.json"]}
    return dict(status="PASS", checked_files=len(entries),
                checked_original_bytes=manifest["uncompressed_bytes"],
                summary=summary, verified_file_sha256=verified,
                verified_member_sha256={entry["archive_entry"]: entry["sha256"]
                                        for entry in entries})


def build(base: Path) -> dict:
    """Make a deterministic archive; retain the local original cache unchanged."""
    base = Path(base).resolve()
    files = sorted((base / "queries").iterdir())
    assert len(files) == 474 and all(path.is_file() for path in files)
    payloads = {str(path.relative_to(base)): path.read_bytes() for path in files}
    ids = sorted(path.name.removesuffix(".provenance.json") for path in files
                 if path.name.endswith(".provenance.json"))
    batches = [query_metadata(batch_id, payloads) for batch_id in ids]
    summary = semantic_summary(batches)
    by_id = {row["batch_id"]: row for row in batches}
    entries = []
    for name, raw in payloads.items():
        batch_id = Path(name).name[:20]
        suffix = Path(name).name[20:]
        entries.append(dict(original_path=f"{PREFIX}/{name}", archive_entry=name,
                            batch_id=batch_id, query_status=by_id[batch_id]["query_status"],
                            role=SUFFIXES[suffix], sha256=sha_bytes(raw), bytes=len(raw)))
    with zipfile.ZipFile(base / ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, raw in payloads.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw, compresslevel=9)
    raw_archive = (base / ARCHIVE).read_bytes()
    manifest = dict(schema_version=1, archive_path=ARCHIVE,
                    archive_sha256=sha_bytes(raw_archive), archive_bytes=len(raw_archive),
                    uncompressed_bytes=sum(len(value) for value in payloads.values()),
                    compression="ZIP DEFLATE, lossless; fixed entry timestamps and modes",
                    preservation="All original SQL, HTTP response and provenance bytes unchanged."
                                 " Failed response bytes are retained as failures, never empty tables.",
                    query_summary=summary, entries=entries, batches=batches)
    (base / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
    summary_path = base / "catalogue_summary.json"
    catalogue = json.loads(summary_path.read_text())
    catalogue.update(
        batch_provenance_files_scope="Historical original provenance for 79 initial failed UNION"
          " attempts and 79 successful VALUES attempts; paths are preserved inside queries_evidence.zip.",
        historical_query_attempts=158, successful_historical_query_attempts=79,
        initial_union_failed_query_attempts=79)
    summary_path.write_text(json.dumps(catalogue, indent=2) + "\n")
    result = verify_archive(base)
    with zipfile.ZipFile(base / ARCHIVE) as archive:
        assert all(archive.read(name) == raw for name, raw in payloads.items())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--base", type=Path, default=HERE)
    args = parser.parse_args()
    result = build(args.base) if args.command == "build" else verify_archive(args.base)
    print("PASS query archive: " + json.dumps(dict(checked_files=result["checked_files"],
          checked_original_bytes=result["checked_original_bytes"], **result["summary"])))


if __name__ == "__main__":
    main()
