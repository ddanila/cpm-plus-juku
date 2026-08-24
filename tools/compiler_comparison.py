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

from audit_8080_com import audit_file
from cpmtools import cpmtool, driver_args

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
    require(data.get("schema") == 2, "unsupported compiler result schema")
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
            static_audit = program.get("static_8080_audit", {})
            require(static_audit.get("origin") == "0100",
                    f"missing static origin for {toolchain_name} "
                    f"{program_name}")
            require(
                static_audit.get("reachable_code_bytes", -1)
                + static_audit.get("data_bytes", -1) == size,
                f"static disassembly does not account for every byte of "
                f"{toolchain_name} {program_name}",
            )
            require(static_audit.get("reachable_instructions", 0) > 0,
                    f"empty static disassembly for {toolchain_name} "
                    f"{program_name}")
            require(
                static_audit.get("forbidden_reachable_opcodes") == 0
                and static_audit.get(
                    "unapproved_runtime_dependencies",
                ) == 0,
                f"static 8080/dependency gate failed for {toolchain_name} "
                f"{program_name}",
            )
            require(len(static_audit.get("listing_sha256", "")) == 64,
                    f"missing canonical disassembly digest for "
                    f"{toolchain_name} {program_name}")
            dependencies = static_audit.get(
                "approved_runtime_dependencies", [],
            )
            require(
                dependencies
                and set(dependencies) <= {
                    "0000h CP/M warm boot",
                    "0005h CP/M BDOS call gate",
                },
                f"unexpected runtime dependency for {toolchain_name} "
                f"{program_name}: {dependencies}",
            )
            stack = program.get("cosim_stack", {})
            for field in ("entry_sp", "anchor_sp", "low_sp"):
                require(
                    len(stack.get(field, "")) == 4,
                    f"missing simulator {field} for {toolchain_name} "
                    f"{program_name}",
                )
            stack_bytes = stack.get("bytes_observed", 0)
            require(
                stack_bytes > 0
                and int(stack["anchor_sp"], 16)
                - int(stack["low_sp"], 16) == stack_bytes,
                f"invalid stack low-water evidence for {toolchain_name} "
                f"{program_name}: {stack}",
            )
            require(stack.get("explicit_sp_writes", -1) >= 0,
                    f"missing SP-write evidence for {toolchain_name} "
                    f"{program_name}")
            require(
                program.get("tpa_bytes_after_image_and_stack") ==
                TPA_BYTES - size - stack_bytes,
                f"incorrect image+stack TPA accounting for "
                f"{toolchain_name} {program_name}",
            )
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
            static_audit, _listing = audit_file(output)
            require(
                static_audit == expected["static_8080_audit"],
                f"{toolchain} {program} static 8080 disassembly or "
                "runtime-dependency evidence differs",
            )
        if strict_cosim:
            run_strict_cosim(work, outputs, data)
    print("Compiler comparison: PASS (records and rebuild are exact)")


def run_strict_cosim(work: Path,
                     outputs: dict[tuple[str, str], Path], data: dict) -> None:
    volume = work / "compiler-comparison.img"
    shutil.copyfile(ROOT / "out" / "cpm-plus-juku-full.img", volume)
    for (toolchain, program), output in outputs.items():
        prefix = "mf" if toolchain == "millfork" else "z"
        run([
            cpmtool("cpmcp"), *driver_args(), "-f", "juku386", str(volume),
            str(output), f"0:{prefix}{program}.com",
        ])
    environment = os.environ.copy()
    metrics_path = work / "compiler-cosim-metrics.json"
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
        "CPM_PLUS_JUKU_CAPTURE_EXTRA_STACK": "1",
        "CPM_PLUS_JUKU_EXPECT_STRICT_TPA_OPCODES": "1",
        "CPM_PLUS_JUKU_METRICS_OUTPUT": str(metrics_path),
    })
    run([sys.executable, str(ROOT / "tests" / "cosim_check.py")],
        env=environment)
    metrics = json.loads(metrics_path.read_text())
    metric_names = ("extra", "extra2", "extra3", "extra4", "extra5", "extra6")
    identities = tuple(
        (toolchain, program)
        for toolchain in ("millfork", "z88dk")
        for program in PROGRAMS
    )
    for metric_name, (toolchain, program) in zip(metric_names, identities):
        observed = metrics[metric_name]
        expected = data["toolchains"][toolchain]["programs"][program][
            "cosim_stack"
        ]
        require(
            observed["stack_entry_sp"] == int(expected["entry_sp"], 16)
            and observed["stack_anchor_sp"] ==
            int(expected["anchor_sp"], 16)
            and observed["stack_low_sp"] == int(expected["low_sp"], 16)
            and observed["stack_bytes_observed"] ==
            expected["bytes_observed"]
            and observed["explicit_sp_writes"] ==
            expected["explicit_sp_writes"],
            f"{toolchain} {program} stack high-water differs: "
            f"expected={expected} observed={observed}",
        )


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
