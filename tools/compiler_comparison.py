#!/usr/bin/env python3
"""Validate and optionally reproduce the pinned 8080 compiler experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "compiler-comparison"
RESULTS = EXPERIMENT / "results.json"
PROGRAMS = ("hello", "cat", "wc")
TPA_BYTES = 39168


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_and_validate() -> dict:
    data = json.loads(RESULTS.read_text())
    require(data.get("schema") == 1, "unsupported compiler result schema")
    require(data.get("target", {}).get("cpu") == "Intel 8080",
            "compiler experiment no longer targets the Intel 8080")
    require(data["target"].get("tpa_bytes") == TPA_BYTES,
            "compiler experiment TPA differs from the measured C6 TPA")
    require(set(data.get("toolchains", {})) == {"millfork", "z88dk"},
            "compiler experiment must cover exactly Millfork and z88dk")
    for toolchain_name, toolchain in data["toolchains"].items():
        require(len(toolchain.get("revision", "")) == 40,
                f"{toolchain_name} lacks an exact revision")
        require(len(toolchain.get("release_asset_sha256", "")) == 64,
                f"{toolchain_name} lacks a release-asset digest")
        require(set(toolchain.get("programs", {})) == set(PROGRAMS),
                f"{toolchain_name} must cover hello, cat, and wc")
        for program_name, program in toolchain["programs"].items():
            source = EXPERIMENT / program["source"]
            require(source.is_file(), f"missing source fixture {source}")
            require(sha256(source) == program["source_sha256"],
                    f"source fixture changed without new evidence: {source}")
            size = program["output_bytes"]
            require(size > 0, f"invalid {toolchain_name} {program_name} size")
            require(program["tpa_bytes_after_static_image"] == TPA_BYTES - size,
                    f"incorrect TPA accounting for {toolchain_name} "
                    f"{program_name}")
            require(len(program["output_sha256"]) == 64,
                    f"missing output digest for {toolchain_name} "
                    f"{program_name}")
            require(program["cosim_read_requests"] > 0,
                    f"missing executed workload for {toolchain_name} "
                    f"{program_name}")
    strict = data.get("strict_8080_cosim", {})
    require(strict.get("passed") is True,
            "compiler fixtures lack strict-8080 execution evidence")
    require(strict.get("tpa_z80_prefix_fetches") == 0
            and strict.get("tpa_undocumented_opcode_fetches") == 0,
            "compiler fixture execution fetched a forbidden opcode")
    require(len(strict.get("commands", [])) == 6,
            "strict compiler suite must execute all six binaries")
    require(data.get("decision", {}).get("production_baseline") ==
            "hand-written 8080 assembly",
            "compiler experiment must not silently replace the baseline")
    return data


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def reproduce(data: dict, millfork: Path, z88dk_root: Path,
              strict_cosim: bool) -> None:
    require(millfork.is_file(), f"Millfork executable not found: {millfork}")
    zcc = z88dk_root / "bin" / "zcc"
    require(zcc.is_file(), f"z88dk zcc not found: {zcc}")
    zcc_config = z88dk_root / "lib" / "config"
    zcc_libsrc = z88dk_root / "libsrc"
    require(zcc_config.is_dir() and zcc_libsrc.is_dir(),
            f"z88dk source build is incomplete: {z88dk_root}")
    with tempfile.TemporaryDirectory(
            prefix="cpm-plus-compiler-comparison.") as name:
        work = Path(name)
        outputs: dict[tuple[str, str], Path] = {}
        for program in PROGRAMS:
            output = work / f"mf{program}.com"
            run([
                str(millfork), "-t", "cpm", "-O4", "-o",
                str(output.with_suffix("")),
                str(EXPERIMENT / "millfork" / f"{program}.mfk"),
            ])
            outputs[("millfork", program)] = output
        environment = os.environ.copy()
        environment["PATH"] = \
            f"{z88dk_root / 'bin'}:{environment.get('PATH', '')}"
        environment["ZCCCFG"] = str(zcc_config)
        zcc_flags = [
            str(zcc), "+cpm", "-clib=8080", "-O3", "-vn",
            "-pragma-define:CRT_ENABLE_COMMANDLINE=0",
            "-pragma-define:CLIB_OPEN_MAX=0",
            "-pragma-define:noprotectmsdos=1",
            f"-L{zcc_libsrc}",
        ]
        for program in PROGRAMS:
            output = work / f"z{program}.com"
            run([
                *zcc_flags, f"-o{output}",
                str(EXPERIMENT / "z88dk" / f"{program}.c"),
            ], env=environment)
            outputs[("z88dk", program)] = output
        for (toolchain, program), output in outputs.items():
            expected = data["toolchains"][toolchain]["programs"][program]
            require(output.stat().st_size == expected["output_bytes"],
                    f"{toolchain} {program} size differs: "
                    f"{output.stat().st_size}")
            require(sha256(output) == expected["output_sha256"],
                    f"{toolchain} {program} bytes are not reproducible")
        if strict_cosim:
            run_strict_cosim(work, outputs)
    print("Compiler comparison: PASS (records and rebuild are exact)")


def run_strict_cosim(work: Path,
                     outputs: dict[tuple[str, str], Path]) -> None:
    volume = work / "compiler-comparison.img"
    shutil.copyfile(ROOT / "out" / "cpm-plus-juku-full.img", volume)
    for (toolchain, program), output in outputs.items():
        prefix = "mf" if toolchain == "millfork" else "z"
        run([
            "cpmcp", "-f", "juku386", str(volume), str(output),
            f"0:{prefix}{program}.com",
        ])
    environment = os.environ.copy()
    environment.update({
        "CPM_PLUS_JUKU_BOOT_PATH": "distribution",
        "CPM_PLUS_JUKU_VOLUME": str(volume),
        "CPM_PLUS_JUKU_EXTRA_COMMAND": "MFHELLO",
        "CPM_PLUS_JUKU_EXTRA_MARKER": "Hello from Millfork",
        "CPM_PLUS_JUKU_EXTRA_COMMAND2": "MFCAT README.TXT",
        "CPM_PLUS_JUKU_EXTRA_MARKER2": "CP/M Plus 3.1",
        "CPM_PLUS_JUKU_EXTRA_COMMAND3": "MFWC README.TXT",
        "CPM_PLUS_JUKU_EXTRA_MARKER3":
            "lines=0014 words=003B bytes=01FA",
        "CPM_PLUS_JUKU_EXTRA_COMMAND4": "ZHELLO",
        "CPM_PLUS_JUKU_EXTRA_MARKER4": "Hello from z88dk",
        "CPM_PLUS_JUKU_EXTRA_COMMAND5": "ZCAT README.TXT",
        "CPM_PLUS_JUKU_EXTRA_MARKER5": "CP/M Plus 3.1",
        "CPM_PLUS_JUKU_EXTRA_COMMAND6": "ZWC README.TXT",
        "CPM_PLUS_JUKU_EXTRA_MARKER6":
            "lines=0014 words=003B bytes=01FA",
    })
    run([sys.executable, str(ROOT / "tests" / "cosim_check.py")],
        env=environment)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--millfork", type=Path)
    parser.add_argument("--z88dk-root", type=Path)
    parser.add_argument("--strict-cosim", action="store_true")
    args = parser.parse_args()
    data = load_and_validate()
    if args.millfork or args.z88dk_root or args.strict_cosim:
        require(args.millfork is not None and args.z88dk_root is not None,
                "rebuild requires both --millfork and --z88dk-root")
        reproduce(data, args.millfork, args.z88dk_root, args.strict_cosim)
    else:
        print("Compiler comparison: PASS (pinned records and sources)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
