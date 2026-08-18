#!/usr/bin/env python3
"""Validate and render the CP/M 3 development-tool dispositions."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "third_party" / "cpm3" / "releases"
AUDIT = RELEASES / "development-tools.json"
PROVENANCE = RELEASES / "provenance.json"
CANDIDATES = RELEASES / "candidates.json"
SOURCE_ARCHIVE = RELEASES / "cpm3src_unix-20260607.zip"
BINARY_ARCHIVE = RELEASES / "cpm3bin_unix-20260607.zip"
DEV_PROFILE = ROOT / "volume" / "profiles" / "dev.json"
DEFAULT_OUTPUT = ROOT / "docs" / "cpm3-development-tools.md"
PROGRAMS = {
    "ASM.COM", "LOAD.COM", "ED.COM", "SID.COM", "RMAC.COM", "MAC.COM",
    "DRLINK.COM",
}
ADMITTED = {"ED.COM", "SID.COM"}
HOST_ONLY = {"RMAC.COM", "MAC.COM", "DRLINK.COM"}
UNAVAILABLE = {"ASM.COM", "LOAD.COM"}
TPA_BYTES = 39168


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f"{path} is not an object")
    return value


def audit() -> dict:
    data = load(AUDIT)
    provenance = load(PROVENANCE)
    catalogue = load(CANDIDATES)
    profile = load(DEV_PROFILE)
    require(data.get("schema") ==
            "cpm-plus-juku-cpm3-development-tools-v1",
            "development-tool schema differs")
    require(data.get("cpu") == "Intel 8080"
            and data.get("tpa_bytes") == TPA_BYTES,
            "development-tool target differs")
    programs = data.get("programs")
    require(isinstance(programs, dict) and set(programs) == PROGRAMS,
            "development-tool program set differs")
    archives = provenance.get("archives", {})
    for path in (SOURCE_ARCHIVE, BINARY_ARCHIVE):
        record = archives.get(path.name, {})
        raw = path.read_bytes()
        require(record.get("bytes") == len(raw)
                and record.get("sha256") == digest(raw),
                f"pinned archive differs: {path.name}")
    candidate_records = {
        item["name"]: item for item in catalogue.get("candidates", [])
    }
    selected = provenance.get("selected_development_files", {})
    profile_names = {
        item["destination"].split(":", 1)[1]
        for item in profile.get("files", [])
    }
    with zipfile.ZipFile(SOURCE_ARCHIVE) as source, \
            zipfile.ZipFile(BINARY_ARCHIVE) as binary:
        source_names = set(source.namelist())
        binary_names = set(binary.namelist())
        for name in UNAVAILABLE:
            item = programs[name]
            require(item.get("decision") == "reject-unavailable"
                    and item.get("profile") == "none",
                    f"{name} unavailable disposition differs")
            lower = name.lower()
            require(lower not in source_names and lower not in binary_names,
                    f"{name} is no longer absent from the pinned release")
            require(name not in selected and name not in profile_names,
                    f"{name} entered the development profile")
        for name in ADMITTED:
            item = programs[name]
            require(item.get("decision") == "admit"
                    and item.get("profile") == "dev"
                    and item.get("archive") == "binary",
                    f"{name} admission differs")
            member = item.get("member")
            require(isinstance(member, str) and member in binary_names,
                    f"{name} binary member is absent")
            raw = binary.read(member)
            require(item.get("bytes") == len(raw)
                    and item.get("sha256") == digest(raw),
                    f"{name} binary differs")
            sources = item.get("source_members")
            require(isinstance(sources, list) and sources
                    and not (set(sources) - source_names),
                    f"{name} source mapping differs")
            require(item.get("tpa_bytes_after_static_image")
                    == TPA_BYTES - len(raw),
                    f"{name} TPA accounting differs")
            evidence = item.get("strict_8080_cosim", {})
            require(evidence.get("passed") is True
                    and evidence.get("returned_to_ccp") is True
                    and evidence.get("tpa_z80_prefix_fetches") == 0
                    and evidence.get("tpa_undocumented_opcode_fetches") == 0,
                    f"{name} strict-8080 evidence differs")
            if name == "ED.COM":
                require(evidence.get("write_requests", 0) > 0
                        and evidence.get("saved_text") ==
                        "EDITED ON JUKU CP/M PLUS 3.1",
                        "ED.COM save/readback evidence differs")
            require(selected.get(name, {}).get("sha256") == digest(raw)
                    and name in profile_names,
                    f"{name} is not admission-pinned in development-a")
            candidate = candidate_records.get(name, {})
            require(candidate.get("status") == "shipped"
                    and candidate.get("profile") == "dev"
                    and candidate.get("cpm3_test") == "strict-8080-cosim",
                    f"{name} catalogue state differs")
        for name in HOST_ONLY:
            item = programs[name]
            require(item.get("decision") == "host-build-input-only"
                    and item.get("profile") == "none"
                    and item.get("archive") == "source"
                    and item.get("source_members") == [],
                    f"{name} host-only boundary differs")
            member = item.get("member")
            require(isinstance(member, str) and member in source_names,
                    f"{name} host tool is absent")
            raw = source.read(member)
            require(item.get("bytes") == len(raw)
                    and item.get("sha256") == digest(raw),
                    f"{name} host-tool bytes differ")
            require(name not in selected and name not in profile_names,
                    f"{name} leaked into development-a")
    workflow = data.get("selected_workflow")
    require(isinstance(workflow, list) and len(workflow) == 5,
            "selected development workflow differs")
    return data


def render(data: dict) -> str:
    programs = data["programs"]
    ed = programs["ED.COM"]
    sid = programs["SID.COM"]
    lines = [
        "# CP/M 3 development-tool audit",
        "",
        "Status: **COMPLETE; ED AND SID ADMITTED TO `development-a`**",
        "",
        "This generated report closes the feature plan's individual DRI",
        "`ASM`/`LOAD`/`ED`/`SID`/`RMAC` audit. It distinguishes programs that",
        "may run on the Juku from opaque historical executables used only inside",
        "the pinned host-side reproduction path.",
        "",
        "| Program | Exact pinned evidence | Decision |",
        "| --- | --- | --- |",
        "| `ASM.COM` | Absent from both CP/M 3 archives | Do not ship |",
        "| `LOAD.COM` | Absent from both CP/M 3 archives | Do not ship; use `HEXCOM` for Intel HEX |",
        (f"| `ED.COM` | {ed['bytes']:,} B; PL/M/8080 sources; strict edit/save "
         "pass | Admit to `development-a` |"),
        (f"| `SID.COM` | {sid['bytes']:,} B; byte-identical source rebuild; "
         "strict load/quit pass | Admit to `development-a` |"),
        "| `RMAC.COM` | Exact build-input binary; matching source absent | Host-side ZXCC input only |",
        "| `MAC.COM` | Exact build-input binary; matching source absent | Host-side ZXCC input only |",
        "| `DRLINK.COM` | Exact build-input binary; matching source absent | Host-side ZXCC input only |",
        "",
        "## Selected workflow",
        "",
    ]
    lines.extend(f"{index}. {step}" for index, step in enumerate(
        data["selected_workflow"], 1,
    ))
    lines.extend([
        "",
        "This is intentionally a hybrid period/modern workflow. It is useful and",
        "reproducible without pretending that source-less DRI assembler/linker",
        "binaries satisfy the target-distribution admission rule.",
        "",
        "## ED executable evidence",
        "",
        "The development simulator boots the generated image, waits for ED's",
        "actual `: *` prompt, sends the documented `Istring^Z` insertion, waits",
        "for the next prompt, saves with `E`, returns to CCP, and reads the new",
        (f"file back with `TYPE`. The command took "
         f"{ed['strict_8080_cosim']['read_requests']} NetDisk reads and "
         f"{ed['strict_8080_cosim']['write_requests']} synchronous writes in "
         "the observed run. ED's default uppercase translation is"),
        "retained and asserted rather than hidden by the harness.",
        "",
        "## Build boundary",
        "",
        "`SID`, `HEXCOM`, and `PATCH` rebuild byte-for-byte from archived 8080",
        "assembly with pinned ZXCC/MAC/RMAC/DRLINK. ED has complete PL/M-80 and",
        "assembly source plus the upstream GNU Make recipe, but recreating its",
        "binary requires the original PL/M80/ASM80/Thames environment. The exact",
        "maintained upstream binary is therefore checksum-pinned and executable-",
        "tested, while those historical compilers do not become ordinary project",
        "dependencies.",
        "",
        "`make development-tool-audit-check` verifies both complete archive",
        "hashes, every present/absent member, source mappings, profile isolation,",
        "TPA arithmetic, simulator evidence, catalogue state, and this report.",
        "`make development-cosim-check` executes the complete selected workflow.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = audit()
    expected = render(data)
    if args.check:
        require(args.output.is_file() and args.output.read_text() == expected,
                f"generated development-tool report differs: {args.output}")
        print("CPM3-DEV-TOOLS: PASS (seven explicit dispositions)")
    else:
        args.output.write_text(expected)
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, TypeError, ValueError,
            zipfile.BadZipFile) as error:
        print(f"cpm3-development-tool-audit: {error}")
        raise SystemExit(1)
