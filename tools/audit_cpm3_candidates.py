#!/usr/bin/env python3
"""Verify and render the pinned strict-8080 CP/M utility catalogue."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
from audit_8080_com import audit_bytes

ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "third_party/cpm3/releases"
CATALOGUE = RELEASES / "candidates.json"
STATIC_AUDIT = RELEASES / "static-8080.json"
PROVENANCE = RELEASES / "provenance.json"
SOURCE_ARCHIVE = RELEASES / "cpm3src_unix-20260607.zip"
BINARY_ARCHIVE = RELEASES / "cpm3bin_unix-20260607.zip"
DEFAULT_OUTPUT = ROOT / "docs/cpm3-utility-catalogue.md"
SCHEMA = "cpm-plus-juku-cpm3-candidates-v1"
STATIC_SCHEMA = "cpm-plus-juku-cpm3-static-8080-v1"
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


def hex_address(value: object, label: str) -> int:
    require(
        isinstance(value, str)
        and len(value) == 4
        and all(character in "0123456789ABCDEF" for character in value),
        f"invalid {label}: {value!r}",
    )
    return int(value, 16)


def address_map(value: object, label: str) -> dict[int, tuple[int, ...]]:
    require(isinstance(value, dict), f"{label} is not an object")
    result: dict[int, tuple[int, ...]] = {}
    for raw_address, raw_targets in value.items():
        address = hex_address(raw_address, f"{label} address")
        require(isinstance(raw_targets, list) and raw_targets,
                f"{label} targets absent at {raw_address}")
        result[address] = tuple(
            hex_address(target, f"{label} target")
            for target in raw_targets
        )
    return result


def reason_map(value: object, label: str) -> dict[int, str]:
    require(isinstance(value, dict), f"{label} is not an object")
    result: dict[int, str] = {}
    for raw_address, reason in value.items():
        require(isinstance(reason, str) and reason.strip(),
                f"{label} rationale absent at {raw_address}")
        result[hex_address(raw_address, f"{label} address")] = reason
    return result


def static_policy(raw: object) -> dict[str, object]:
    require(isinstance(raw, dict), "static 8080 policy is not an object")
    allowed = {
        "indirect_targets", "indirect_external_targets",
        "dynamic_indirect_exits", "dynamic_indirect_calls",
        "dynamic_direct_exits", "noreturn_targets",
    }
    require(not (set(raw) - allowed),
            f"unknown static 8080 policy fields: {sorted(set(raw) - allowed)}")
    result: dict[str, object] = {}
    if "indirect_targets" in raw:
        result["indirect_targets"] = address_map(
            raw["indirect_targets"], "indirect target",
        )
    if "indirect_external_targets" in raw:
        external = raw["indirect_external_targets"]
        require(isinstance(external, dict),
                "indirect external targets are not an object")
        result["indirect_external_targets"] = {
            hex_address(site, "indirect external site"): reason_map(
                targets, "indirect external target",
            )
            for site, targets in external.items()
        }
    for field in (
        "dynamic_indirect_exits", "dynamic_direct_exits",
        "noreturn_targets",
    ):
        if field in raw:
            result[field] = reason_map(raw[field], field.replace("_", " "))
    if "dynamic_indirect_calls" in raw:
        calls = raw["dynamic_indirect_calls"]
        require(isinstance(calls, dict),
                "dynamic indirect calls are not an object")
        converted = {}
        for site, call in calls.items():
            require(isinstance(call, dict),
                    f"dynamic indirect call differs at {site}")
            continuations = call.get("return_continuations")
            reason = call.get("reason")
            require(isinstance(continuations, list) and continuations
                    and isinstance(reason, str) and reason.strip(),
                    f"dynamic indirect call evidence absent at {site}")
            converted[hex_address(site, "dynamic indirect call site")] = (
                tuple(hex_address(target, "return continuation")
                      for target in continuations),
                reason,
            )
        result["dynamic_indirect_calls"] = converted
    return result


def audit_static_program(name: str, image: bytes, raw: object) -> dict:
    require(isinstance(raw, dict), f"static audit absent: {name}")
    image_format = raw.get("format")
    require(image_format in {"flat-com", "gencom-rsx", "sid-relocator"},
            f"static audit format differs: {name}")
    components = raw.get("components")
    require(isinstance(components, list) and components,
            f"static audit components absent: {name}")

    if image_format == "flat-com":
        require(len(components) == 1
                and components[0].get("offset") == 0
                and components[0].get("bytes") == len(image),
                f"flat COM coverage differs: {name}")
    elif image_format == "gencom-rsx":
        require(len(components) == 2 and len(image) >= 0x100
                and image[0] == 0xC9 and image[3] == 0xC9
                and image[15] == 1,
                f"GENCOM header differs: {name}")
        transient, rsx = components
        require(transient.get("offset") == 0x100
                and transient.get("bytes") == int.from_bytes(
                    image[1:3], "little",
                )
                and rsx.get("offset") == int.from_bytes(
                    image[16:18], "little",
                )
                and rsx.get("bytes") == int.from_bytes(
                    image[18:20], "little",
                )
                and raw.get("container_noncode_bytes") ==
                len(image) - transient["bytes"] - rsx["bytes"],
                f"GENCOM component map differs: {name}")
    else:
        require(name == "SID.COM" and len(components) == 2
                and components[0].get("offset") == 0
                and components[0].get("bytes") == len(image)
                and components[1].get("offset") == 0x100
                and components[1].get("bytes") == int.from_bytes(
                    image[1:3], "little",
                )
                and raw.get("relocation_and_padding_bytes") ==
                len(image) - 0x100 - components[1]["bytes"],
                f"SID relocator component map differs: {name}")

    audited_components = []
    for component in components:
        require(isinstance(component, dict),
                f"static component is not an object: {name}")
        component_name = component.get("name")
        offset = component.get("offset")
        size = component.get("bytes")
        source_basis = component.get("source_basis")
        require(isinstance(component_name, str) and component_name
                and isinstance(offset, int) and isinstance(size, int)
                and size > 0 and 0 <= offset <= len(image) - size
                and isinstance(source_basis, str) and source_basis.strip(),
                f"static component metadata differs: {name}")
        origin = hex_address(component.get("origin"), "component origin")
        entries = component.get("entry_points")
        require(isinstance(entries, list) and entries,
                f"static entry points absent: {name}/{component_name}")
        kwargs = static_policy(component.get("policy", {}))
        result, _ = audit_bytes(
            image[offset:offset + size],
            origin=origin,
            entry_points=tuple(
                hex_address(value, "component entry point")
                for value in entries
            ),
            **kwargs,
        )
        evidence = component.get("evidence")
        require(isinstance(evidence, dict)
                and set(evidence) == {
                    "reachable_instructions", "reachable_code_bytes",
                    "data_bytes", "listing_sha256",
                }
                and all(result[key] == value
                        for key, value in evidence.items())
                and result["forbidden_reachable_opcodes"] == 0
                and result["unapproved_runtime_dependencies"] == 0,
                f"static 8080 evidence differs: {name}/{component_name}")
        audited_components.append({
            "name": component_name,
            **evidence,
        })
    return {"format": image_format, "components": audited_components}


def audit() -> tuple[dict[str, object], list[dict[str, object]]]:
    catalogue = load_json(CATALOGUE)
    provenance = load_json(PROVENANCE)
    static = load_json(STATIC_AUDIT)
    require(catalogue.get("schema") == SCHEMA, "candidate schema differs")
    require(static.get("schema") == STATIC_SCHEMA,
            "static 8080 schema differs")
    static_programs = static.get("programs")
    require(isinstance(static_programs, dict),
            "static 8080 program map is absent")
    candidates = catalogue.get("candidates")
    require(isinstance(candidates, list), "candidate list is absent")
    require(20 <= len(candidates) <= 30,
            f"candidate count is outside planned range: {len(candidates)}")
    tpa_bytes = catalogue.get("tpa_bytes")
    require(tpa_bytes == 39168, "catalogue TPA differs from C6 evidence")
    selected_full = provenance.get("selected_distribution_files")
    selected_dev = provenance.get("selected_development_files")
    require(isinstance(selected_full, dict),
            "selected distribution files absent")
    require(isinstance(selected_dev, dict),
            "selected development files absent")
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
    selected_by_profile = {
        "full": {name for name in selected_full if name.endswith(".COM")},
        "dev": {name for name in selected_dev if name.endswith(".COM")},
    }
    selected_com = set().union(*selected_by_profile.values())
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
                require(name in selected_by_profile[item["profile"]],
                        f"shipped candidate profile differs: {name}")
                require(item["cpm3_test"] == "strict-8080-cosim",
                        f"shipped candidate lacks executable 8080 proof: {name}")
                item["static_8080"] = audit_static_program(
                    name, data, static_programs.get(name),
                )
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
    require(set(static_programs) == selected_com,
            "static 8080 program set differs from admitted COM set")
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
        "need both flow-aware static 8080 and executable strict-8080 CP/M 3",
        "evidence. GENCOM RSXs and SID's relocated module are audited as",
        "separate executable components rather than mistaken for flat COMs.",
        "Shipped rows also have allocation, live stack, transient/RSX, and",
        "C6 TPA evidence in",
        "[`cpm3-runtime-memory.md`](cpm3-runtime-memory.md).",
        "",
        "| Program | State/profile | Source/build | Bytes | Static TPA use | Static 8080 proof | CP/M 3 evidence |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for item in candidates:
        sources = ", ".join(f"`{name}`" for name in item["source_members"])
        state = f"{item['status']} / {item['profile']}"
        span = (f"0100h--{item['load_end']:04X}h; "
                f"{item['tpa_bytes_after_image']:,} B remain")
        static_proof = "not admitted"
        if item["status"] == "shipped":
            components = item["static_8080"]["components"]
            code = sum(component["reachable_code_bytes"]
                       for component in components)
            static_proof = f"{len(components)} component(s), {code:,} code B"
        lines.append(
            f"| `{item['name']}` | {state} | {item['source_language']}: "
            f"{sources} | {item['bytes']:,} | {span} | {static_proof} | "
            f"{item['cpm3_test']} |"
        )
    lines.extend([
        "",
        "All rows use the upstream Makefile recipe recorded in the catalogue:",
        f"{catalogue['build_method']}. The target CPU contract is",
        f"{catalogue['cpu_requirement']}.",
        "",
        "## External candidates not admitted",
        "",
        "- Kevin Boone's exact GPLv3 `cpm-ls` 0.1b source is identified and its",
        "  z88dk port passes strict-8080 execution. It remains deferred because",
        "  ordinary `LS` costs 55 NetDisk reads versus three for `DIR`, while",
        "  `LS -L` costs 188 reads and the 14,913-byte image overlaps existing",
        "  listing commands.",
        "- `HIST`: z80pack's behavior-reference binaries have no matching source,",
        "  independent license, CPU contract, or build recipe, so they are",
        "  rejected rather than executed or redistributed.",
        "- 8080 FIG-Forth 1.1: the core listing builds and returns cleanly under",
        "  strict simulation, but the editor, assembler, documentation, and clear",
        "  complete-package notice required by the plan are absent, so packaging",
        "  is deferred.",
        "- Pinned z88dk and Millfork fixtures pass strict-8080 execution; neither",
        "  replaces hand-written assembly as the production baseline. `uplm80` is",
        "  rejected until it gains a real 8080 backend because exact DRI source",
        "  compilation emits Z80-only instructions.",
        "- RomWBW and LokiOS remain Z80-family usability references, not binary",
        "  sources for this Intel 8080 distribution.",
        "",
        "Exact revisions, patches, hashes, measured commands, and decisions are",
        "recorded in [`external-software-audit.md`](external-software-audit.md).",
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
