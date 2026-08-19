#!/usr/bin/env python3
"""Prove that the focused C7 bench directory and tar are reproducible."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/package_release_candidate.py"
CANDIDATE = "cpm-plus-3.1-juku-c7-modified-raw-bench"
EXPECTED_STATUS = "simulator-qualified; focused modified-raw bench pending"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(path: Path) -> Path:
    subprocess.run(
        ["python3", str(SCRIPT), "--variant", "c7", "--output", str(path)],
        cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
    )
    return Path(str(path) + ".tar")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cpm-plus-c7-package-") as name:
        temporary = Path(name)
        first = temporary / f"one/{CANDIDATE}"
        second = temporary / f"two/{CANDIDATE}"
        first_tar = build(first)
        second_tar = build(second)
        if first_tar.read_bytes() != second_tar.read_bytes():
            raise AssertionError("C7 bench archives are not byte-identical")

        manifest = json.loads((first / "manifest.json").read_text())
        if manifest.get("candidate") != CANDIDATE or \
                manifest.get("rom_abi") != "1.2" or \
                manifest.get("status") != EXPECTED_STATUS:
            raise AssertionError("C7 bench identity differs")
        for filename, record in manifest["files"].items():
            path = first / filename
            if record != {"bytes": path.stat().st_size,
                          "sha256": digest(path)}:
                raise AssertionError(f"C7 file binding differs: {filename}")
        stem = "juku-network-rom-abi1.2-c7"
        if (first / f"{stem}-d15.bin").read_bytes() + \
                (first / f"{stem}-d16.bin").read_bytes() != \
                (first / f"{stem}.bin").read_bytes():
            raise AssertionError("C7 D15/D16 order differs")
        boot = json.loads((first / "cpm-plus-juku-c7-manifest.json").read_text())
        if boot.get("rom", {}).get("candidate") != \
                "network-first-abi1.2-c7-modified-raw-simulator":
            raise AssertionError("packaged C7 boot manifest differs")
        print(
            "C7-BENCH-CANDIDATE: PASS "
            f"(reproducible tar {digest(first_tar)[:16]}, exact C7 halves)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
