#!/usr/bin/env python3
"""Verify and extract the pinned CP/M 3.1 distribution utilities."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "third_party/cpm3/releases"
PROVENANCE = RELEASES / "provenance.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_provenance() -> dict[str, object]:
    value = json.loads(PROVENANCE.read_text())
    if not isinstance(value, dict) or \
            value.get("schema") != "cpm-plus-juku-upstream-release-v1":
        raise ValueError("CP/M 3 utility provenance schema differs")
    return value


def expected_files() -> tuple[dict[str, object], dict[str, bytes]]:
    provenance = load_provenance()
    archives = provenance.get("archives")
    selected = provenance.get("selected_distribution_files")
    if not isinstance(archives, dict) or not isinstance(selected, dict):
        raise TypeError("CP/M 3 provenance lacks archives or selected files")
    opened: dict[str, zipfile.ZipFile] = {}
    try:
        for name, record in archives.items():
            if not isinstance(name, str) or not isinstance(record, dict):
                raise TypeError("CP/M 3 archive provenance differs")
            path = RELEASES / name
            data = path.read_bytes()
            if len(data) != record.get("bytes") or \
                    digest(data) != record.get("sha256"):
                raise ValueError(f"pinned CP/M 3 archive differs: {name}")
            opened[name] = zipfile.ZipFile(path)
        source = opened["cpm3src_unix-20260607.zip"]
        binary = opened["cpm3bin_unix-20260607.zip"]
        source_names = set(source.namelist())
        result: dict[str, bytes] = {}
        for output_name, record in selected.items():
            if not isinstance(output_name, str) or not isinstance(record, dict):
                raise TypeError("CP/M 3 selected-file provenance differs")
            member = record.get("archive_member")
            sources = record.get("source_members")
            if not isinstance(member, str) or not isinstance(sources, list) or \
                    not all(isinstance(name, str) for name in sources):
                raise TypeError(f"source mapping differs for {output_name}")
            missing = sorted(set(sources) - source_names)
            if missing:
                raise ValueError(
                    f"source members for {output_name} are absent: {missing}"
                )
            data = binary.read(member)
            if len(data) != record.get("bytes") or \
                    digest(data) != record.get("sha256"):
                raise ValueError(f"pinned CP/M 3 member differs: {member}")
            result[output_name] = data
        return provenance, result
    finally:
        for archive in opened.values():
            archive.close()


def manifest(provenance: dict[str, object], files: dict[str, bytes]
             ) -> dict[str, object]:
    return {
        "schema": "cpm-plus-juku-utility-extract-v1",
        "release": provenance["release"],
        "license": "third_party/cpm3/LICENSE.md",
        "files": {
            name: {"bytes": len(data), "sha256": digest(data)}
            for name, data in sorted(files.items())
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "build/cpm3-utilities")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="require an existing byte-identical extraction")
    mode.add_argument("--verify", action="store_true",
                      help="verify archives and source mappings without writing")
    args = parser.parse_args()

    provenance, files = expected_files()
    expected_manifest = manifest(provenance, files)
    if args.verify:
        print(
            "CPM3-UTILITY-INPUTS: PASS "
            f"({len(files)} selected files, source mappings present)"
        )
        return 0
    output = args.output.resolve()
    if args.check:
        for name, data in files.items():
            path = output / name
            if not path.is_file() or path.read_bytes() != data:
                raise ValueError(f"extracted CP/M 3 utility differs: {name}")
        record = output / "manifest.json"
        if not record.is_file() or json.loads(record.read_text()) != \
                expected_manifest:
            raise ValueError("extracted CP/M 3 utility manifest differs")
        print(f"CPM3-UTILITY-EXTRACT: PASS {output}")
        return 0

    output.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (output / name).write_bytes(data)
    (output / "manifest.json").write_text(
        json.dumps(expected_manifest, indent=2) + "\n"
    )
    print(f"CPM3-UTILITY-EXTRACT: wrote {len(files)} files to {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, TypeError, ValueError,
            zipfile.BadZipFile) as error:
        print(f"cpm3-utility-extract: {error}")
        raise SystemExit(1)
