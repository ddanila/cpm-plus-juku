#!/usr/bin/env python3
"""Guard the C10 STATUS/DIAG POF observability and volume binding."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from cpmtools import cpmtool, driver_args


STATUS = ROOT / "build/status-c10.cim"
DIAG = ROOT / "build/diag-c10.cim"
VOLUME = ROOT / "out/cpm-plus-juku-c10-full.img"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def extract(image: Path, name: str, output: Path) -> bytes:
    subprocess.run(
        [cpmtool("cpmcp"), *driver_args(), "-f", "juku386",
         str(image), f"0:{name}", str(output)],
        cwd=ROOT, check=True, capture_output=True,
    )
    return output.read_bytes()


def main() -> int:
    status = STATUS.read_bytes()
    diag = DIAG.read_bytes()
    for marker in (
        b"Juku Status 1.5",
        b"PPI0 Port C: $",
        b"POF: $",
        b"released (picture enabled)",
        b"asserted (pixels suppressed)",
    ):
        require(marker in status, f"STATUS omits {marker!r}")
    require(bytes.fromhex("DB 06") in status,
            "STATUS does not read the PPI0 Port C latch")
    for marker in (
        b"Juku Diag 0.7",
        b"Video enable/console state: $",
    ):
        require(marker in diag, f"DIAG omits {marker!r}")
    require(bytes.fromhex("DB 06 E6 80") in diag,
            "DIAG does not fail on asserted PC7/POF")

    with tempfile.TemporaryDirectory(prefix="c10-observability.") as name:
        temporary = Path(name)
        volume_status = extract(VOLUME, "STATUS.COM", temporary / "status.com")
        volume_diag = extract(VOLUME, "DIAG.COM", temporary / "diag.com")
    require(volume_status == status, "C10 volume STATUS differs from build")
    require(volume_diag == diag, "C10 volume DIAG differs from build")

    print(
        "C10-VIDEO-OBSERVABILITY: PASS "
        "STATUS 1.5 reports Port C/POF; DIAG 0.7 rejects PC7 high"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
