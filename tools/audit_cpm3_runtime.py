#!/usr/bin/env python3
"""Validate and render DRI utility disk and runtime-memory evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "third_party" / "cpm3" / "releases"
RUNTIME = RELEASES / "runtime-memory.json"
CANDIDATES = RELEASES / "candidates.json"
STATIC_AUDIT = RELEASES / "static-8080.json"
DEFAULT_OUTPUT = ROOT / "docs" / "cpm3-runtime-memory.md"
SCHEMA = "cpm-plus-juku-cpm3-runtime-memory-v1"
ARTIFACT_NAMES = ("network_rom", "system", "fastboot")
EXPECTED_ARTIFACTS = {
    "network_rom": ("juku-network-rom-abi1.2-c6.bin", 16384),
    "system": ("cpm-plus-juku-network-rom-extended-native-system.bin", 18432),
    "fastboot": (
        "cpm-plus-juku-network-rom-extended-native-fastboot-v16.bin", 8031,
    ),
}
ADDRESS_FIELDS = (
    "entry_sp", "anchor_sp", "low_sp", "segment_min_anchor_sp",
    "segment_max_anchor_sp",
)
INTEGER_FIELDS = ("segments", "bytes_observed", "explicit_sp_writes")
METRIC_FIELDS = {
    "entry_sp": "stack_entry_sp",
    "anchor_sp": "stack_anchor_sp",
    "low_sp": "stack_low_sp",
    "segment_min_anchor_sp": "stack_segment_min_anchor_sp",
    "segment_max_anchor_sp": "stack_segment_max_anchor_sp",
    "segments": "stack_segments",
    "bytes_observed": "stack_bytes_observed",
    "explicit_sp_writes": "explicit_sp_writes",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict:
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


def allocation_size(size: int, block_size: int) -> int:
    return (size + block_size - 1) // block_size * block_size


def audit() -> dict:
    data = load_json(RUNTIME)
    candidates = load_json(CANDIDATES)
    static = load_json(STATIC_AUDIT)
    require(data.get("schema") == SCHEMA, "runtime-memory schema differs")
    require(data.get("platform") ==
            "C6 network-first ROM with native CP/M 3 BIOS",
            "runtime-memory platform differs")
    artifacts = data.get("artifacts")
    require(isinstance(artifacts, dict)
            and set(artifacts) == set(ARTIFACT_NAMES),
            "runtime-memory C6 artifact set differs")
    for name in ARTIFACT_NAMES:
        artifact = artifacts[name]
        require(
            isinstance(artifact, dict)
            and set(artifact) == {"name", "bytes", "sha256"}
            and isinstance(artifact["name"], str)
            and artifact["name"]
            and isinstance(artifact["bytes"], int)
            and artifact["bytes"] > 0
            and isinstance(artifact["sha256"], str)
            and len(artifact["sha256"]) == 64
            and all(character in "0123456789abcdef"
                    for character in artifact["sha256"]),
            f"runtime-memory C6 artifact identity differs: {name}",
        )
        require(
            (artifact["name"], artifact["bytes"]) == EXPECTED_ARTIFACTS[name],
            f"runtime-memory artifact is not the C6 {name}",
        )

    tpa = data.get("tpa")
    require(isinstance(tpa, dict), "runtime-memory TPA record is absent")
    origin = hex_address(tpa.get("origin"), "TPA origin")
    top = hex_address(tpa.get("top_exclusive"), "TPA top")
    initial_stack = hex_address(
        tpa.get("initial_stack"), "initial stack",
    )
    require(
        origin == 0x0100
        and top == 0x9A00
        and tpa.get("bytes") == top - origin == 39168
        and initial_stack == 0x9CFE,
        "runtime-memory C6 TPA geometry differs",
    )
    require(candidates.get("tpa_bytes") == tpa["bytes"],
            "candidate/runtime TPA sizes differ")
    block_size = data.get("allocation_block_bytes")
    require(block_size == 2048, "runtime allocation block differs")

    candidate_list = candidates.get("candidates")
    require(isinstance(candidate_list, list), "candidate list is absent")
    candidate_records = {
        item.get("name"): item for item in candidate_list
        if isinstance(item, dict)
    }
    shipped = {
        name for name, item in candidate_records.items()
        if item.get("status") == "shipped"
    }
    programs = data.get("programs")
    require(isinstance(programs, dict) and set(programs) == shipped,
            "runtime program set differs from shipped DRI set")
    static_programs = static.get("programs")
    require(isinstance(static_programs, dict),
            "static 8080 program map is absent")

    seen_metrics: set[tuple[str, str]] = set()
    records = []
    for candidate in candidate_list:
        name = candidate.get("name")
        if name not in shipped:
            continue
        item = programs[name]
        require(isinstance(item, dict), f"runtime record differs: {name}")
        profile = item.get("profile")
        metric = item.get("metric")
        command = item.get("command")
        require(
            profile in {"full", "dev"}
            and profile == candidate.get("profile")
            and isinstance(metric, str) and metric.startswith("extra")
            and isinstance(command, str) and command.strip(),
            f"runtime identity differs: {name}",
        )
        require((profile, metric) not in seen_metrics,
                f"duplicate runtime metric: {profile}/{metric}")
        seen_metrics.add((profile, metric))

        runtime = item.get("runtime")
        require(isinstance(runtime, dict)
                and set(runtime) == set(ADDRESS_FIELDS + INTEGER_FIELDS),
                f"runtime fields differ: {name}")
        addresses = {
            field: hex_address(runtime[field], f"{name} {field}")
            for field in ADDRESS_FIELDS
        }
        require(all(isinstance(runtime[field], int)
                    and runtime[field] >= 0 for field in INTEGER_FIELDS),
                f"runtime integer fields differ: {name}")
        require(addresses["entry_sp"] == initial_stack,
                f"runtime entry stack differs: {name}")
        require(
            addresses["low_sp"] >= origin
            and addresses["anchor_sp"] - addresses["low_sp"]
            == runtime["bytes_observed"]
            and addresses["segment_min_anchor_sp"]
            <= addresses["anchor_sp"]
            <= addresses["segment_max_anchor_sp"]
            and addresses["segment_max_anchor_sp"] == initial_stack,
            f"runtime stack geometry differs: {name}",
        )
        require(
            1 <= runtime["segments"]
            <= runtime["explicit_sp_writes"] + 1,
            f"runtime stack-segment count differs: {name}",
        )

        disk_bytes = candidate.get("bytes")
        require(isinstance(disk_bytes, int) and disk_bytes > 0,
                f"candidate byte size differs: {name}")
        static_item = static_programs.get(name)
        require(isinstance(static_item, dict),
                f"static runtime basis absent: {name}")
        components = static_item.get("components")
        require(isinstance(components, list) and components,
                f"static runtime components absent: {name}")
        first = components[0]
        require(isinstance(first, dict)
                and isinstance(first.get("bytes"), int),
                f"transient component differs: {name}")
        transient_bytes = first["bytes"]
        image_format = static_item.get("format")
        if image_format == "gencom-rsx":
            require(len(components) == 2
                    and isinstance(components[1].get("bytes"), int),
                    f"resident component differs: {name}")
            resident_bytes = components[1]["bytes"]
        else:
            resident_bytes = 0
        loaded_end = origin + transient_bytes
        runtime_top = max(loaded_end, addresses["anchor_sp"])
        require(runtime_top <= top,
                f"runtime image exceeds C6 TPA: {name}")
        records.append({
            "name": name,
            "profile": profile,
            "metric": metric,
            "command": command,
            "disk_bytes": disk_bytes,
            "allocated_bytes": allocation_size(disk_bytes, block_size),
            "transient_bytes": transient_bytes,
            "resident_bytes": resident_bytes,
            "runtime_top": runtime_top,
            "tpa_headroom": top - runtime_top,
            "runtime": runtime,
        })
    result = dict(data)
    result["records"] = records
    return result


def verify_volume_report(data: dict, profile: str, path: Path) -> None:
    report = load_json(path)
    require(report.get("schema") == "cpm-plus-juku-volume-report-v1",
            f"volume report schema differs: {path}")
    files = report.get("files")
    require(isinstance(files, list), f"volume file report absent: {path}")
    by_name = {
        item.get("destination", "").split(":", 1)[-1]: item
        for item in files if isinstance(item, dict)
    }
    for record in data["records"]:
        if record["profile"] != profile:
            continue
        actual = by_name.get(record["name"])
        require(isinstance(actual, dict)
                and actual.get("volume_bytes") == record["disk_bytes"]
                and actual.get("allocated_bytes") ==
                record["allocated_bytes"],
                f"volume allocation differs: {record['name']}")


def verify_metrics(data: dict, profile: str, path: Path) -> None:
    metrics = load_json(path)
    require(metrics.get("_platform") == data["artifacts"],
            "runtime metrics do not bind the exact C6 artifacts")
    selected = [
        record for record in data["records"]
        if record["profile"] == profile
    ]
    require(selected, f"runtime profile is empty: {profile}")
    for record in selected:
        actual = metrics.get(record["metric"])
        require(isinstance(actual, dict),
                f"runtime metric absent: {record['name']}")
        require(actual.get("command") == record["command"],
                f"runtime command differs: {record['name']}")
        expected = record["runtime"]
        for expected_field, actual_field in METRIC_FIELDS.items():
            expected_value = expected[expected_field]
            if expected_field in ADDRESS_FIELDS:
                expected_value = int(expected_value, 16)
            require(actual.get(actual_field) == expected_value,
                    f"runtime metric differs: {record['name']}/"
                    f"{actual_field}")


def render(data: dict) -> str:
    tpa = data["tpa"]
    lines = [
        "# CP/M 3 shipped-utility runtime memory",
        "",
        "Status: **COMPLETE; DISK AND LIVE STACK COSTS ADMISSION-GATED**",
        "",
        "Every shipped Digital Research executable is exercised on the C6",
        "network-first ROM and native CP/M 3 BIOS, not only on the retained",
        "RomBios compatibility path. Each useful workload must return to CCP,",
        "freeze its own command-scoped stack measurement, pass strict Intel",
        "8080 fetched-opcode checks, and retain the ordinary warm-boot test.",
        "",
        (f"The transient area is `{tpa['origin']}h..99FFh` "
         f"({tpa['bytes']:,} bytes). The initial CCP stack at "
         f"`{tpa['initial_stack']}h` is in the loader workspace above the TPA "
         "and is recorded for attribution, not charged to a program's TPA "
         "footprint."),
        "",
        ("The measured platform is bound by SHA-256 to the exact C6 ROM, "
         "extended native system, and V16 Fastboot artifacts; a matching "
         "memory map alone is not accepted as C6 evidence."),
        "",
        "| Program | Profile and workload | Disk bytes / allocated | Loaded transient / resident | Observed stack | Runtime top / TPA left |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for record in data["records"]:
        runtime = record["runtime"]
        resident = (f"{record['resident_bytes']:,} B RSX"
                    if record["resident_bytes"] else "none")
        lines.append(
            f"| `{record['name']}` | {record['profile']}: "
            f"`{record['command']}` | {record['disk_bytes']:,} / "
            f"{record['allocated_bytes']:,} B | "
            f"{record['transient_bytes']:,} B / {resident} | "
            f"`{runtime['anchor_sp']}h`→`{runtime['low_sp']}h`, "
            f"{runtime['bytes_observed']} B | "
            f"`{record['runtime_top']:04X}h` / "
            f"{record['tpa_headroom']:,} B |"
        )
    lines.extend([
        "",
        "Disk allocation uses the native 2,048-byte Juku allocation block and",
        "is cross-checked against the generated volume report. Runtime top is",
        "the greater of the loaded transient end and the measured private-stack",
        "anchor. GENCOM's separately loaded RSX component is reported rather",
        "than silently double-counted inside the ordinary transient span.",
        "",
        "The stack figures are exact for the named useful admission workload;",
        "they are regression baselines, not a claim about every possible input",
        "path. Even the smallest recorded headroom is deliberately much larger",
        "than the observed stack peak, so profile selection does not depend on",
        "a razor-thin measurement.",
        "",
        "`make distribution-cosim-check` produces and verifies the full-profile",
        "metrics, including native `DEVICE NAMES`. `make",
        "development-cosim-check` does the same for HEXCOM, SID, PATCH, and ED.",
        "`make utility-catalogue-check` validates the exact 13-program set, TPA",
        "geometry, component accounting, workload map, stack arithmetic,",
        "negative mutations, and this generated report.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--profile", choices=("full", "dev"))
    parser.add_argument("--metrics", type=Path)
    parser.add_argument("--volume-report", type=Path)
    args = parser.parse_args()
    require(bool(args.metrics) == bool(args.profile),
            "--metrics and --profile must be supplied together")
    require(not args.volume_report or args.profile,
            "--volume-report requires --profile")
    data = audit()
    expected = render(data)
    if args.check:
        require(args.output.is_file() and args.output.read_text() == expected,
                f"generated runtime-memory report differs: {args.output}")
    else:
        args.output.write_text(expected)
        print(f"wrote {args.output}")
    if args.metrics and args.profile:
        verify_metrics(data, args.profile, args.metrics)
        if args.volume_report:
            verify_volume_report(data, args.profile, args.volume_report)
        count = sum(record["profile"] == args.profile
                    for record in data["records"])
        print(f"CPM3-RUNTIME: PASS ({count} {args.profile} programs)")
    else:
        print("CPM3-RUNTIME: PASS (13 admitted DRI programs)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, TypeError, ValueError) as error:
        print(f"cpm3-runtime-audit: {error}")
        raise SystemExit(1)
