#!/usr/bin/env python3
"""Validate, render, and optionally reproduce external-software audits."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "external-software"
RESULTS = EXPERIMENT / "results.json"
COMPILER_RESULTS = ROOT / "experiments" / "compiler-comparison" / "results.json"
DEFAULT_OUTPUT = ROOT / "docs" / "external-software-audit.md"
TPA_BYTES = 39168
CANDIDATES = {"cpm-ls", "hist-rsx", "fig-forth-1.1", "uplm80"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> tuple[dict, dict]:
    data = json.loads(RESULTS.read_text())
    compilers = json.loads(COMPILER_RESULTS.read_text())
    require(data.get("schema") == 1, "unsupported external audit schema")
    target = data.get("target", {})
    require(target.get("cpu") == "Intel 8080", "audit target is not 8080")
    require(target.get("tpa_bytes") == TPA_BYTES,
            "audit TPA differs from C6")
    candidates = data.get("candidates", {})
    require(set(candidates) == CANDIDATES,
            "external candidate set differs")
    for name, item in candidates.items():
        require(item.get("decision") in {"defer", "reject"},
                f"{name} has an unreviewed admission state")
        require(item.get("profile") == "none",
                f"{name} entered a profile despite non-admission")
        revision = item.get("revision", "")
        require(len(revision) == 40
                and all(char in "0123456789abcdef" for char in revision),
                f"{name} lacks an exact revision")
        require(item.get("reason"), f"{name} lacks a decision reason")

    ls = candidates["cpm-ls"]
    port = ls["audited_port"]
    ls_patch = EXPERIMENT / port["patch"]
    require(ls_patch.is_file() and sha256(ls_patch) == port["patch_sha256"],
            "cpm-ls port patch differs")
    require(port["output_bytes"] <= TPA_BYTES
            and port["tpa_bytes_after_static_image"]
            == TPA_BYTES - port["output_bytes"],
            "cpm-ls TPA accounting differs")
    ls_cosim = ls["strict_8080_cosim"]
    require(ls_cosim.get("passed") is True
            and ls_cosim.get("tpa_z80_prefix_fetches") == 0
            and ls_cosim.get("tpa_undocumented_opcode_fetches") == 0,
            "cpm-ls lacks strict-8080 execution evidence")
    require(ls_cosim["normal"]["read_requests"]
            > ls_cosim["baseline_dir"]["read_requests"]
            and ls_cosim["long"]["read_requests"]
            > ls_cosim["normal"]["read_requests"],
            "cpm-ls deferral is not supported by measured workloads")

    hist = candidates["hist-rsx"]
    require(hist.get("source_present") is False
            and hist.get("independent_license_present") is False
            and hist["strict_8080_cosim"].get("passed") is False,
            "HIST admission boundary differs")
    require({item["name"] for item in hist["artifacts"]}
            == {"HIST.COM", "HISTCL.COM"},
            "HIST behavior-reference artifact set differs")

    forth = candidates["fig-forth-1.1"]
    build = forth["audited_build"]
    forth_patch = EXPERIMENT / build["patch"]
    require(forth_patch.is_file()
            and sha256(forth_patch) == build["patch_sha256"],
            "FIG-Forth build patch differs")
    require(build["output_bytes"] <= TPA_BYTES
            and build["tpa_bytes_after_static_image"]
            == TPA_BYTES - build["output_bytes"],
            "FIG-Forth TPA accounting differs")
    forth_cosim = forth["strict_8080_cosim"]
    require(forth_cosim.get("passed") is True
            and forth_cosim.get("returned_to_ccp") is True
            and forth_cosim.get("tpa_z80_prefix_fetches") == 0
            and forth_cosim.get("tpa_undocumented_opcode_fetches") == 0,
            "FIG-Forth lacks strict-8080 return evidence")
    require(set(forth.get("missing_package_parts", [])) == {
        "editor", "assembler", "user documentation",
        "unambiguous complete-package license",
    }, "FIG-Forth deferral boundary differs")

    uplm = candidates["uplm80"]
    fixture = uplm["fixture"]
    require(uplm.get("declared_target") == "Zilog Z80 assembly"
            and fixture.get("optimized_jr_instructions", 0) > 0
            and fixture.get("unoptimized_srl_instructions", 0) > 0
            and fixture.get("unoptimized_rr_instructions", 0) > 0,
            "uplm80 rejection lacks fetched-opcode evidence")

    require(compilers.get("target", {}).get("cpu") == "Intel 8080"
            and compilers.get("strict_8080_cosim", {}).get("passed") is True
            and compilers.get("decision", {}).get("production_baseline")
            == "hand-written 8080 assembly",
            "compiler comparison decision differs")
    return data, compilers


def render(data: dict, compilers: dict) -> str:
    candidates = data["candidates"]
    ls = candidates["cpm-ls"]
    hist = candidates["hist-rsx"]
    forth = candidates["fig-forth-1.1"]
    uplm = candidates["uplm80"]
    normal = ls["strict_8080_cosim"]["normal"]
    long = ls["strict_8080_cosim"]["long"]
    baseline = ls["strict_8080_cosim"]["baseline_dir"]
    millfork = compilers["toolchains"]["millfork"]
    z88dk = compilers["toolchains"]["z88dk"]
    compiler_rows = []
    for toolchain_name, toolchain in (("Millfork", millfork), ("z88dk", z88dk)):
        for program_name in ("hello", "cat", "wc"):
            program = toolchain["programs"][program_name]
            compiler_rows.append(
                f"| {toolchain_name} | `{program_name}` | "
                f"{program['output_bytes']} | "
                f"{program['cosim_stack']['bytes_observed']} | "
                f"{program['tpa_bytes_after_image_and_stack']:,} | "
                f"{program['static_8080_audit']['reachable_instructions']} |"
            )
    lines = [
        "# External CP/M software and compiler audit",
        "",
        "Status: **COMPLETE; NO EXTERNAL CANDIDATE ADMITTED BY THIS AUDIT**",
        "",
        "This generated report closes the external-candidate and host-toolchain",
        "items in the CP/M Plus feature plan. Passing a build or simulator test",
        "is necessary but not sufficient for admission: provenance, overlap,",
        "runtime cost, and completeness also apply. Exact records live in",
        "`experiments/external-software/results.json`; checked patches preserve",
        "the two source experiments without importing unexplained binaries.",
        "",
        "| Candidate | Exact source | 8080 execution | Decision |",
        "| --- | --- | --- | --- |",
        (f"| `cpm-ls` {ls['version']} | Kevin Boone, GPLv3, "
         f"`{ls['revision'][:12]}` | Pass | Defer from profiles |"),
        (f"| `HIST` RSX | z80pack image `{hist['revision'][:12]}`; "
         "matching source/license absent | Not run | Reject |"),
        (f"| FIG-Forth {forth['version']} | Cassady/Harris listing, "
         f"gist `{forth['revision'][:12]}` | Pass, including `BYE` | "
         "Defer incomplete package |"),
        (f"| `uplm80` | GPLv3, `{uplm['revision'][:12]}` | Fails CPU "
         "contract at generated assembly | Reject as production tool |"),
        "",
        "## cpm-ls",
        "",
        (f"The intended project is [{ls['upstream']}]({ls['upstream']}) at "
         f"`{ls['revision']}`. It explicitly supports 8080 and Z80 and is "
         "GPLv3, so the earlier name/provenance uncertainty is resolved."),
        "",
        ("Upstream builds a checked-in 9,984-byte binary with Manx Aztec C "
         "1.06d. The archived patch ports the same source to pinned z88dk, "
         "fixes byte-valued BDOS return handling and an FCB-name bounds bug, "
         f"and reproducibly emits a {ls['audited_port']['output_bytes']:,}-byte "
         "strict-8080 executable. It leaves "
         f"{ls['audited_port']['tpa_bytes_after_static_image']:,} bytes below "
         "the measured TPA ceiling before runtime data and stack."),
        "",
        "Measured on the same representative full A: image:",
        "",
        "| Command | NetDisk reads | Records | Observed elapsed |",
        "| --- | ---: | ---: | ---: |",
        (f"| `{baseline['command']}` | {baseline['read_requests']} | "
         f"{baseline['read_records']} | {baseline['elapsed_seconds_observed']:.3f} s |"),
        (f"| `{normal['command']}` | {normal['read_requests']} | "
         f"{normal['read_records']} | {normal['elapsed_seconds_observed']:.3f} s |"),
        (f"| `{long['command']}` | {long['read_requests']} | "
         f"{long['read_records']} | {long['elapsed_seconds_observed']:.3f} s |"),
        "",
        "Decision: keep it planned and audited, but do not put it in `full` or",
        "`dev` yet. `DIR`/`DIRSYS` cover ordinary listing, while the richer",
        "sorting/size display currently has a disproportionate network and TPA",
        "cost. A future indexed-directory service or a demonstrated workflow can",
        "reopen admission without repeating the provenance and compiler work.",
        "",
        "## HIST command-history RSX",
        "",
        (f"The z80pack CP/M 3 image at `{hist['revision']}` contains the "
         "behavior-reference `HIST.COM` and `HISTCL.COM` binaries. No matching "
         "source, independent license, CPU declaration, or build recipe exists "
         "in that tree. `HIST.UTL` is an unrelated Digital Research SID "
         "histogram utility, not the RSX source."),
        "",
        "Decision: reject. The project does not execute or redistribute an",
        "unlicensed, unexplained resident binary merely because another",
        "distribution demonstrates useful behavior.",
        "",
        "## FIG-Forth 1.1",
        "",
        (f"The exact preserved listing (`{forth['source_sha256']}`) needs only "
         "three mechanical zmac compatibility edits. It builds to a "
         f"{forth['audited_build']['output_bytes']:,}-byte image with SHA-256 "
         f"`{forth['audited_build']['output_sha256']}`. Strict simulation "
         "prints `fig-FORTH 1.1`, accepts `BYE`, returns to `A>`, and fetches "
         "neither Z80 prefixes nor undocumented 8080 aliases."),
        "",
        "Decision: defer optional development-media packaging. The plan asks for",
        "the language together with its editor, assembler, source, documentation,",
        "and complete notice. The gist supplies only the core listing, and its",
        "public-domain publication statement coexists with narrower copyright and",
        "all-rights-reserved text that does not cover the missing components.",
        "",
        "## Host compiler experiments",
        "",
        (f"Pinned Millfork {millfork['release']} and z88dk {z88dk['release']} "
         "each reproducibly build standalone `hello`, `cat`, and `wc` fixtures; "
         "all six pass strict-8080 execution. Millfork emits much smaller images "
         "and readable Intel assembly, while z88dk remains the preferable C "
         "portability probe."),
        "",
        "| Toolchain | Program | COM bytes | Observed stack bytes | TPA left | Static instructions |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
        *compiler_rows,
        "",
        "The flow-aware static disassembler accounts for every output byte,",
        "follows only reachable code, and rejects undocumented/Z80-only",
        "opcodes, direct hardware I/O, arbitrary `PCHL`, and control transfers",
        "outside the image except CP/M warm boot and BDOS. The strict simulator",
        "arms and freezes an SP low-water measurement around each representative",
        "command; its broader fetched-opcode gate independently remains clean.",
        "Exact listings are represented by stable SHA-256 digests in",
        "`experiments/compiler-comparison/results.json`.",
        "",
        "Hand-written 8080 assembly remains the production baseline. Neither",
        "compiler becomes a required distribution build dependency. Millfork is",
        "the preferred next high-level experiment; z88dk is retained for C ports.",
        "",
        (f"`uplm80` revision `{uplm['revision']}` cannot replace the archived "
         "DRI PL/M-80 toolchain: its documented target is Z80, and exact "
         "`SETDEF.PLM` output contains 200 `JR` instructions at `-O2`; at `-O0` "
         "it still contains `SRL`/`RR`. Reconsider it only after a genuine Intel "
         "8080 backend exists."),
        "",
        "## Reproduction boundaries",
        "",
        "`make external-software-audit-check` verifies the exact revisions,",
        "decisions, hashes, TPA arithmetic, patches, strict-execution records, and",
        "this generated report. `make external-software-rebuild-check` additionally",
        "rebuilds cpm-ls and FIG-Forth when the pinned source trees/toolchains are",
        "supplied explicitly; ordinary offline builds never download third-party",
        "material.",
        "",
    ]
    return "\n".join(lines)


def run(command: list[str], *, cwd: Path | None = None,
        env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd or ROOT, env=env, check=True)


def reproduce(data: dict, cpm_ls_tree: Path, z88dk_root: Path,
              fig_source: Path, zmac: Path) -> None:
    ls = data["candidates"]["cpm-ls"]
    forth = data["candidates"]["fig-forth-1.1"]
    require(cpm_ls_tree.is_dir(), f"cpm-ls tree absent: {cpm_ls_tree}")
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=cpm_ls_tree,
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    require(revision == ls["revision"], "cpm-ls source revision differs")
    zcc = z88dk_root / "bin" / "zcc"
    require(zcc.is_file(), f"z88dk compiler absent: {zcc}")
    require(fig_source.is_file(), f"FIG-Forth source absent: {fig_source}")
    require(sha256(fig_source) == forth["source_sha256"],
            "FIG-Forth source differs")
    require(zmac.is_file(), f"zmac absent: {zmac}")
    with tempfile.TemporaryDirectory(prefix="external-software-rebuild.") as name:
        work = Path(name)
        ls_work = work / "cpm-ls"
        shutil.copytree(cpm_ls_tree, ls_work,
                        ignore=shutil.ignore_patterns(".git"))
        run(["git", "apply", str(EXPERIMENT / ls["audited_port"]["patch"])],
            cwd=ls_work)
        output = ls_work / "ls-z88dk.com"
        environment = os.environ.copy()
        environment["PATH"] = \
            f"{z88dk_root / 'bin'}:{environment.get('PATH', '')}"
        environment["ZCCCFG"] = str(z88dk_root / "lib" / "config")
        run([
            str(zcc), "+cpm", "-clib=8080", "-O3", "-SO3", "-vn",
            f"-L{z88dk_root / 'libsrc'}", "-DZ88DK", "-DCPM",
            "-pragma-define:nofileio=1",
            "-pragma-define:nostreams=1",
            "-pragma-define:noprotectmsdos=1", f"-o{output}",
            *(str(ls_work / source)
              for source in ls["audited_port"]["source_files"]),
        ], env=environment)
        require(output.stat().st_size == ls["audited_port"]["output_bytes"]
                and sha256(output) == ls["audited_port"]["output_sha256"],
                "cpm-ls output is not byte reproducible")

        forth_work = work / "8080-fig-forth.asm"
        shutil.copyfile(fig_source, forth_work)
        run(["patch", "-s", "-p0", "-i",
             str(EXPERIMENT / forth["audited_build"]["patch"])], cwd=work)
        require(forth_work.stat().st_size
                == forth["audited_build"]["patched_source_bytes"]
                and sha256(forth_work)
                == forth["audited_build"]["patched_source_sha256"],
                "patched FIG-Forth source differs")
        forth_output = work / "fig.cim"
        run([str(zmac), *forth["audited_build"]["build_arguments"],
             "-o", str(forth_output), str(forth_work)])
        require(forth_output.stat().st_size
                == forth["audited_build"]["output_bytes"]
                and sha256(forth_output)
                == forth["audited_build"]["output_sha256"],
                "FIG-Forth output is not byte reproducible")
    print("EXTERNAL-SOFTWARE: PASS (both source experiments reproduce exactly)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--cpm-ls-tree", type=Path)
    parser.add_argument("--z88dk-root", type=Path)
    parser.add_argument("--fig-source", type=Path)
    parser.add_argument("--zmac", type=Path)
    args = parser.parse_args()
    data, compilers = validate()
    supplied = (args.cpm_ls_tree, args.z88dk_root,
                args.fig_source, args.zmac)
    require(all(value is not None for value in supplied)
            or all(value is None for value in supplied),
            "rebuild requires --cpm-ls-tree, --z88dk-root, --fig-source, and --zmac")
    if args.cpm_ls_tree is not None:
        reproduce(data, args.cpm_ls_tree, args.z88dk_root,
                  args.fig_source, args.zmac)
    expected = render(data, compilers)
    if args.check:
        require(args.output.is_file() and args.output.read_text() == expected,
                f"generated external-software report differs: {args.output}")
        print("EXTERNAL-SOFTWARE: PASS (pinned decisions and generated report)")
    else:
        args.output.write_text(expected)
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
