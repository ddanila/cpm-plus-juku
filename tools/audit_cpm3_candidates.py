#!/usr/bin/env python3
"""Verify and render the pinned strict-8080 CP/M utility catalogue."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "third_party/cpm3/releases"
CATALOGUE = RELEASES / "candidates.json"
PROVENANCE = RELEASES / "provenance.json"
SOURCE_ARCHIVE = RELEASES / "cpm3src_unix-20260607.zip"
BINARY_ARCHIVE = RELEASES / "cpm3bin_unix-20260607.zip"
DEFAULT_OUTPUT = ROOT / "docs/cpm3-utility-catalogue.md"
SCHEMA = "cpm-plus-juku-cpm3-candidates-v1"
VALID_STATUSES = {"shipped", "candidate", "deferred-duplicate"}
VALID_PROFILES = {"full", "dev", "none"}
VALID_TESTS = {"strict-8080-cosim", "profile-and-directory", "not-run"}
TPA_START = 0x0100


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f"{path} is not a JSON object")
    return value


def audit() -> tuple[dict[str, object], list[dict[str, object]]]:
    catalogue = load_json(CATALOGUE)
    provenance = load_json(PROVENANCE)
    require(catalogue.get("schema") == SCHEMA, "candidate schema differs")
    candidates = catalogue.get("candidates")
    require(isinstance(candidates, list), "candidate list is absent")
    require(20 <= len(candidates) <= 30,
            f"candidate count is outside planned range: {len(candidates)}")
    tpa_bytes = catalogue.get("tpa_bytes")
    require(tpa_bytes == 39168, "catalogue TPA differs from C6 evidence")
    selected = provenance.get("selected_distribution_files")
    require(isinstance(selected, dict), "selected distribution files absent")
    archives = provenance.get("archives")
    require(isinstance(archives, dict), "pinned archive records absent")
    for path in (SOURCE_ARCHIVE, BINARY_ARCHIVE):
        record = archives.get(path.name)
        require(isinstance(record, dict),
                f"pinned archive record absent: {path.name}")
        data = path.read_bytes()
        require(record.get("bytes") == len(data)
                and record.get("sha256") == digest(data),
                f"pinned archive differs: {path.name}")
    selected_com = {name for name in selected if name.endswith(".COM")}
    names: set[str] = set()
    members: set[str] = set()
    audited: list[dict[str, object]] = []
    with zipfile.ZipFile(SOURCE_ARCHIVE) as source, \
            zipfile.ZipFile(BINARY_ARCHIVE) as binary:
        source_names = set(source.namelist())
        binary_names = set(binary.namelist())
        for raw in candidates:
            require(isinstance(raw, dict), "candidate is not an object")
            item = dict(raw)
            name = item.get("name")
            member = item.get("archive_member")
            sources = item.get("source_members")
            require(isinstance(name, str) and name.endswith(".COM"),
                    f"candidate name differs: {name!r}")
            require(name == name.upper() and name not in names,
                    f"candidate name is duplicate or noncanonical: {name}")
            require(isinstance(member, str) and member in binary_names
                    and member not in members,
                    f"candidate binary member differs: {name}")
            require(isinstance(sources, list) and sources
                    and all(isinstance(value, str) for value in sources),
                    f"candidate source mapping differs: {name}")
            missing = sorted(set(sources) - source_names)
            require(not missing, f"candidate sources absent for {name}: {missing}")
            require(item.get("status") in VALID_STATUSES,
                    f"candidate status differs: {name}")
            require(item.get("profile") in VALID_PROFILES,
                    f"candidate profile differs: {name}")
            require(item.get("cpm3_test") in VALID_TESTS,
                    f"candidate CP/M 3 evidence differs: {name}")
            require(isinstance(item.get("source_language"), str),
                    f"candidate source language absent: {name}")
            data = binary.read(member)
            require(item.get("bytes") == len(data)
                    and item.get("sha256") == digest(data),
                    f"candidate binary differs: {name}")
            require(len(data) <= tpa_bytes,
                    f"candidate does not fit the C6 TPA: {name}")
            if item["status"] == "shipped":
                require(name in selected_com,
                        f"shipped candidate is not admission-pinned: {name}")
                require(item["profile"] == "full",
                        f"shipped candidate is outside full profile: {name}")
            elif name in selected_com:
                raise ValueError(
                    f"admission-pinned candidate is not marked shipped: {name}"
                )
            item["load_start"] = TPA_START
            item["load_end"] = TPA_START + len(data) - 1
            item["tpa_bytes_after_image"] = tpa_bytes - len(data)
            audited.append(item)
            names.add(name)
            members.add(member)
    require(selected_com == {item["name"] for item in audited
                             if item["status"] == "shipped"},
            "catalogue shipped set differs from admitted COM set")
    require((ROOT / str(catalogue["license"])).is_file(),
            "catalogue license file is absent")
    return catalogue, audited


def render(catalogue: dict[str, object], candidates: list[dict[str, object]]) -> str:
    lines = [
        "# CP/M Plus strict-8080 utility catalogue",
        "",
        "Status: **AUDITED CANDIDATE CORPUS; ONLY `shipped` ROWS ARE ADMITTED**",
        "",
        "This file is generated by `tools/audit_cpm3_candidates.py` from the",
        "pinned CP/M 3.1 source and binary archives. Do not edit the table by",
        "hand. Every row has an exact binary digest and at least one source",
        "member in the checksum-pinned source archive.",
        "",
        f"Upstream: <{catalogue['upstream']}>, revision `{catalogue['revision']}`.",
        f"Author/publisher record: {catalogue['author']}.",
        f"License record: [`{catalogue['license']}`](../{catalogue['license']}).",
        "",
        "The TPA column is a conservative static load measurement: `.COM` bytes",
        "start at 0100h, and the remaining count is the space to the measured",
        "C6 TPA ceiling before runtime stack, buffers, or RSXs. A candidate is",
        "not admitted merely because its image fits; selected programs still",
        "need executable strict-8080 CP/M 3 evidence.",
        "",
        "| Program | State/profile | Source/build | Bytes | Static TPA use | CP/M 3 evidence |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for item in candidates:
        sources = ", ".join(f"`{name}`" for name in item["source_members"])
        state = f"{item['status']} / {item['profile']}"
        span = (f"0100h--{item['load_end']:04X}h; "
                f"{item['tpa_bytes_after_image']:,} B remain")
        lines.append(
            f"| `{item['name']}` | {state} | {item['source_language']}: "
            f"{sources} | {item['bytes']:,} | {span} | {item['cpm3_test']} |"
        )
    lines.extend([
        "",
        "All rows use the upstream Makefile recipe recorded in the catalogue:",
        f"{catalogue['build_method']}. The target CPU contract is",
        f"{catalogue['cpu_requirement']}.",
        "",
        "## External candidates not admitted",
        "",
        "- `cpm-ls`: no unambiguous source repository and license have been",
        "  identified; do not ship a similarly named binary by assumption.",
        "- `HIST`: z80pack demonstrates the CP/M 3 RSX behavior, but its exact",
        "  program source, independent license, 8080 instruction set, and",
        "  resident-memory cost remain unproven for this port.",
        "- 8080 FIG-Forth 1.1: a preserved CP/M source listing exists and names",
        "  its publications public domain, but its complete notice, fixed memory",
        "  map, disk geometry, build, and CP/M 3 behavior require a separate",
        "  optional-development-media audit.",
        "- z88dk, Millfork, and uplm80 are host toolchain experiments, not target",
        "  utilities. Compiler output must pass the same executable 8080 gate.",
        "- RomWBW and LokiOS remain Z80-family usability references, not binary",
        "  sources for this Intel 8080 distribution.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    catalogue, candidates = audit()
    expected = render(catalogue, candidates)
    if args.check:
        require(args.output.is_file() and args.output.read_text() == expected,
                f"generated utility catalogue differs: {args.output}")
        print(f"CPM3-CANDIDATES: PASS ({len(candidates)} exact source/binary pairs)")
        return 0
    args.output.write_text(expected)
    print(f"wrote {args.output} ({len(candidates)} candidates)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, TypeError, ValueError,
            zipfile.BadZipFile) as error:
        print(f"cpm3-candidate-audit: {error}", file=sys.stderr)
        raise SystemExit(1)
