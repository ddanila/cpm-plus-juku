#!/usr/bin/env python3
"""Build the host-backed CP/M Plus A: volume reproducibly."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit(
            f"usage: {sys.argv[0]} OUTPUT CCP.COM DIAG.COM WBOOT.COM README"
        )
    output, ccp, diag, wboot, readme = map(Path, sys.argv[1:])
    output.parent.mkdir(parents=True, exist_ok=True)
    environment = {**os.environ, "DISKDEFS": str(ROOT / "diskdefs")}
    with tempfile.TemporaryDirectory(prefix="cpm-plus-juku-volume.") as name:
        converted = Path(name) / "readme.txt"
        text = readme.read_text().replace("\r\n", "\n").replace("\r", "\n")
        converted.write_bytes(text.replace("\n", "\r\n").encode("ascii") + b"\x1a")
        subprocess.run(
            ["truncate", "-s", "0", str(output)], check=True,
        )
        subprocess.run(
            ["mkfs.cpm", "-f", "juku386", str(output)],
            cwd=ROOT, env=environment, check=True,
        )
        subprocess.run(
            ["truncate", "-s", "409600", str(output)], check=True,
        )
        for source, destination in (
            (ccp, "0:CCP.COM"),
            (diag, "0:DIAG.COM"),
            (wboot, "0:WBOOT.COM"),
            (converted, "0:README.TXT"),
        ):
            subprocess.run(
                ["cpmcp", "-f", "juku386", str(output),
                 str(source), destination],
                cwd=ROOT, env=environment, check=True,
            )
    if output.stat().st_size != 409600:
        raise RuntimeError(f"unexpected Juku volume size: {output.stat().st_size}")
    print(f"wrote {output} ({output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
