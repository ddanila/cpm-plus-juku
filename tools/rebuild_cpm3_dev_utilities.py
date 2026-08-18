#!/usr/bin/env python3
"""Rebuild the admitted assembly-only CP/M 3 development utilities exactly."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "third_party/cpm3/releases"
SOURCE_ARCHIVE = RELEASES / "cpm3src_unix-20260607.zip"
BINARY_ARCHIVE = RELEASES / "cpm3bin_unix-20260607.zip"
CANDIDATES = RELEASES / "candidates.json"
ZXCC = ROOT / "build/bin/zxcc"
PROGRAMS = ("HEXCOM.COM", "PATCH.COM", "SID.COM")
MEMBERS = (
    "mac.com", "rmac.com", "drlink.com",
    "hexcom.c", "hexpat.c", "hexcom.asm", "patch.asm",
    "prs0mov.asm", "prs1asm.asm", "prs2mon.asm", "makedate.lib",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(command: list[str], directory: Path, *, stdin: Path | None = None) -> None:
    stream = stdin.open("rb") if stdin is not None else None
    try:
        subprocess.run(command, cwd=directory, stdin=stream, check=True)
    finally:
        if stream is not None:
            stream.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        help="optional directory for the three byte-identical rebuilt COM files",
    )
    args = parser.parse_args()
    if not ZXCC.is_file():
        raise FileNotFoundError(f"build the pinned ZXCC tool first: {ZXCC}")

    # The catalogue audit independently validates both complete archive hashes,
    # source mappings, target sizes, and licenses. Reuse it before executing any
    # archived host or CP/M tool.
    sys.path.insert(0, str(ROOT / "tools"))
    from audit_cpm3_candidates import audit  # noqa: PLC0415

    _, candidates = audit()
    records = {item["name"]: item for item in candidates}
    if not all(name in records for name in PROGRAMS):
        raise ValueError("development rebuild set is absent from the catalogue")

    with tempfile.TemporaryDirectory(prefix="cpm3-dev-rebuild.") as name:
        work = Path(name)
        with zipfile.ZipFile(SOURCE_ARCHIVE) as source:
            for member in MEMBERS:
                (work / member).write_bytes(source.read(member))

        compiler = os.environ.get("CC", "cc")
        for helper in ("hexcom", "hexpat"):
            run([
                compiler, "-std=gnu89", "-O2", "-w", "-o", helper,
                f"{helper}.c",
            ], work)

        run([str(ZXCC), "mac.com", "hexcom"], work)
        run([str(work / "hexcom"), "hexcom.com"], work,
            stdin=work / "hexcom.hex")
        run([str(ZXCC), "mac.com", "patch"], work)
        run([str(work / "hexcom"), "patch.com"], work,
            stdin=work / "patch.hex")

        run([str(ZXCC), "rmac.com", "prs1asm"], work)
        run([str(ZXCC), "rmac.com", "prs2mon"], work)
        run([
            str(ZXCC), "drlink.com", "sid.spr", "+-=", "+prs1asm",
            "+-,", "+prs2mon", "+-[OS]",
        ], work)
        run([str(ZXCC), "mac.com", "prs0mov"], work)
        run([str(work / "hexpat"), "sid.spr", "sid.com"], work,
            stdin=work / "prs0mov.hex")

        with zipfile.ZipFile(BINARY_ARCHIVE) as binary:
            rebuilt: dict[str, bytes] = {}
            for program in PROGRAMS:
                data = (work / program.lower()).read_bytes()
                expected = records[program]
                archived = binary.read(str(expected["archive_member"]))
                if data != archived or len(data) != expected["bytes"] or \
                        digest(data) != expected["sha256"]:
                    raise ValueError(
                        f"reproduced {program} differs from its pinned binary"
                    )
                rebuilt[program] = data

        if args.output is not None:
            output = args.output.resolve()
            output.mkdir(parents=True, exist_ok=True)
            for program, data in rebuilt.items():
                (output / program).write_bytes(data)
            (output / "manifest.json").write_text(json.dumps({
                "schema": "cpm-plus-juku-cpm3-dev-rebuild-v1",
                "files": {
                    program: {"bytes": len(data), "sha256": digest(data)}
                    for program, data in sorted(rebuilt.items())
                },
            }, indent=2) + "\n")

    print(
        "CPM3-DEV-REBUILD: PASS "
        "(HEXCOM.COM + PATCH.COM + SID.COM exact from pinned sources)"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, TypeError, ValueError,
            subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        print(f"cpm3-dev-rebuild: {error}", file=sys.stderr)
        raise SystemExit(1)
