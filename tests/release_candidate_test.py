#!/usr/bin/env python3
"""Prove that the C5 release-candidate directory and tar are reproducible."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/package_release_candidate.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(path: Path) -> Path:
    subprocess.run(
        ["python3", str(SCRIPT), "--output", str(path)],
        cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
    )
    archive = Path(str(path) + ".tar")
    if archive.name != "cpm-plus-3.1-juku-c5-desk.tar":
        raise AssertionError("release archive name differs")
    return archive


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cpm-plus-c5-package-") as name:
        temporary = Path(name)
        first = temporary / "one/cpm-plus-3.1-juku-c5-desk"
        second = temporary / "two/cpm-plus-3.1-juku-c5-desk"
        first_tar = build(first)
        second_tar = build(second)
        if first_tar.read_bytes() != second_tar.read_bytes():
            raise AssertionError("release archives are not byte-identical")

        manifest = json.loads((first / "manifest.json").read_text())
        if manifest.get("schema") != "cpm-plus-juku-release-candidate-v1" or \
                manifest.get("rom_abi") != "1.1" or \
                "pending" not in manifest.get("status", ""):
            raise AssertionError("release status or ABI differs")
        for file_name, record in manifest["files"].items():
            path = first / file_name
            if record != {"bytes": path.stat().st_size, "sha256": digest(path)}:
                raise AssertionError(f"release file binding differs: {file_name}")
        boot_manifest = json.loads(
            (first / "cpm-plus-juku-c5-manifest.json").read_text()
        )
        for slot in boot_manifest["system_slots"]:
            for artifact_name in ("system", "fast_stage"):
                record = slot[artifact_name]
                path = first / record["file"]
                if not path.is_file() or record["sha256"] != digest(path):
                    raise AssertionError(
                        f"packaged slot differs: {slot['name']} {artifact_name}"
                    )
        d15 = first / "juku-network-rom-abi1.1-c5-d15.bin"
        d16 = first / "juku-network-rom-abi1.1-c5-d16.bin"
        combined = first / "juku-network-rom-abi1.1-c5.bin"
        if d15.read_bytes() + d16.read_bytes() != combined.read_bytes():
            raise AssertionError("packaged EPROM halves differ from combined ROM")
        print(
            "RELEASE-CANDIDATE: PASS "
            f"(reproducible tar {digest(first_tar)[:16]}, bound files)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
