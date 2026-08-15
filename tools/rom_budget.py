#!/usr/bin/env python3
"""Measure shared Juku modules against the network-first ROM envelopes."""

from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / "third_party" / "juku-common"
ZMAC = ROOT / "build" / "bin" / "zmac"


@dataclass(frozen=True)
class Module:
    name: str
    source: Path
    defines: tuple[str, ...] = ()


def assemble_size(module: Module, temporary: Path) -> int:
    output = temporary / f"{module.name}.rel"
    command = [
        str(ZMAC), "--nmnv", "--zmac", "-8", "--rel7", "-l",
        f"-I{module.source.parent}",
        *(f"-D{name}" for name in module.defines),
        "-o", str(output), str(module.source),
    ]
    result = subprocess.run(
        command, check=True, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    matches = re.findall(r"^\s*(\d+)\s+bytes\s*$", result.stdout, re.MULTILINE)
    if len(matches) != 1:
        raise RuntimeError(f"cannot find unique byte count for {module.name}")
    return int(matches[0])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true",
        help="fail unless every measured module fits its assigned envelope",
    )
    args = parser.parse_args()

    if not ZMAC.is_file():
        raise SystemExit("build/bin/zmac is missing; run `make tools` first")

    modules = (
        Module("console", COMMON / "platform" / "ram-console.asm",
               ("RAMKEYBOARD",)),
        Module("keyboard", COMMON / "platform" / "ram-keyboard.asm"),
        Module("netdisk-v3", COMMON / "platform" / "netdisk-v3.asm",
               ("CPM3ADAPTER",)),
        Module("netconsole", COMMON / "platform" / "netconsole.asm"),
        Module("diag-cpu", COMMON / "diag" / "cpu.asm"),
        Module("diag-memory", COMMON / "diag" / "memory.asm"),
        Module("diag-address", COMMON / "diag" / "memory-address.asm"),
        Module("diag-retention", COMMON / "diag" / "memory-retention.asm"),
        Module("diag-checksum", COMMON / "diag" / "checksum.asm"),
    )

    with tempfile.TemporaryDirectory(prefix="juku-rom-budget.") as name:
        temporary = Path(name)
        smoke = temporary / "sound.asm"
        smoke.write_text(
            f'        include "{COMMON / "music" / "smoke-player.asm"}"\n'
            f'        include "{COMMON / "music" / "smoke-table.asm"}"\n'
            "        end\n"
        )
        all_modules = (*modules, Module("sound", smoke))
        sizes = {module.name: assemble_size(module, temporary)
                 for module in all_modules}

    core = ROOT / "build" / "fastboot-core.cim"
    extension = ROOT / "build" / "fastboot-extension.cim"
    if not core.is_file() or not extension.is_file():
        raise SystemExit("fastboot objects are missing; run `make` first")
    sizes["fastboot-core"] = core.stat().st_size
    sizes["fastboot-extension"] = extension.stat().st_size

    diagnostics = sum(sizes[name] for name in (
        "diag-cpu", "diag-memory", "diag-address", "diag-retention",
        "diag-checksum",
    ))
    resident = (
        ("console", sizes["console"], 0x500),
        ("keyboard", sizes["keyboard"], 0x180),
        ("serial extraction", 0, 0x280),
        ("NetDisk v3", sizes["netdisk-v3"], 0x300),
        ("remote console/status", sizes["netconsole"], 0x200),
        ("diagnostics", diagnostics, 0x300),
        ("sound/platform init", sizes["sound"], 0x100),
        ("near-term growth", 0, 0x600),
        ("font/locale and future services", 0, 0x800),
        ("unassigned reserve", 0, 0x700),
        ("ABI manifest/vectors", 0, 0x100),
    )
    boot_measured = (
        sizes["fastboot-core"] + sizes["fastboot-extension"] +
        sizes["diag-cpu"] + sizes["diag-memory"] +
        sizes["diag-address"] + sizes["diag-checksum"]
    )
    boot = (
        ("reset/init/quick POST", sizes["diag-cpu"] + sizes["diag-memory"] +
         sizes["diag-address"] + sizes["diag-checksum"], 0x600),
        ("automatic boot transport", sizes["fastboot-core"], 0x600),
        ("validation/decompress/recovery", sizes["fastboot-extension"], 0x600),
        ("RAM helper image/staging", 0, 0x400),
        ("manifest/checksum/reserve", 0, 0x200),
    )

    print("Measured shared modules (linked bytes):")
    for key in sorted(sizes):
        print(f"  {key:24s} {sizes[key]:5d}")
    print(f"  {'diagnostics total':24s} {diagnostics:5d}")
    print()

    failures: list[str] = []
    for title, rows, total in (
        ("Boot-only lower ROM", boot, 0x1800),
        ("Resident upper ROM", resident, 0x2800),
    ):
        print(f"{title}:")
        for label, measured, envelope in rows:
            free = envelope - measured
            print(f"  {label:31s} measured={measured:4d} "
                  f"envelope={envelope:4d} headroom={free:4d}")
            if free < 0:
                failures.append(label)
        envelope_total = sum(row[2] for row in rows)
        print(f"  {'TOTAL':31s} envelope={envelope_total:4d} "
              f"required={total:4d}\n")
        if envelope_total != total:
            failures.append(f"{title} envelope total")

    print(f"Measured boot ingredients: {boot_measured} / 6144 bytes")
    print(f"Measured resident ingredients: "
          f"{sum(row[1] for row in resident)} / 10240 bytes")
    if args.check and failures:
        raise SystemExit("ROM-BUDGET: FAIL: " + ", ".join(failures))
    if args.check:
        print("ROM-BUDGET: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
