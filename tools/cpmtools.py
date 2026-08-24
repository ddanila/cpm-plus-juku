#!/usr/bin/env python3
"""Locate the cpmtools binaries and pin their disk-container driver."""

from __future__ import annotations

import functools
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
LOCAL_BIN = ROOT / "build/cpmtools-install/bin"
PROBE_GEOMETRY = "juku386"


def cpmtool(name: str) -> str:
    """Prefer a locally built cpmtools over whatever is on PATH."""
    local = LOCAL_BIN / name
    return str(local) if local.is_file() else name


@functools.lru_cache(maxsize=None)
def driver_args() -> tuple[str, ...]:
    """Arguments that pin cpmtools to plain sector images.

    Homebrew's cpmtools is linked against libdsk, which autodetects the disk
    container and refuses the raw images built here; -T raw pins the raw
    driver. cpmtools built without libdsk -- the usual Linux package, and what
    CI runs -- has no -T at all and would reject it. Ask the installed tools
    rather than read their usage text: build a scratch image and see whether
    an ordinary listing already works. Anything unexpected returns no
    arguments, which is the command line used before this probe existed.
    """
    # cwd=ROOT because cpmtools reads its diskdefs from the working directory,
    # like every other cpmtools call in this repository.
    with tempfile.TemporaryDirectory(prefix="cpmtools-probe.") as name:
        image = Path(name) / "probe.img"
        try:
            created = subprocess.run(
                [cpmtool("mkfs.cpm"), "-f", PROBE_GEOMETRY, str(image)],
                cwd=ROOT, capture_output=True, check=False,
            )
            if created.returncode != 0:
                return ()
            listed = subprocess.run(
                [cpmtool("cpmls"), "-f", PROBE_GEOMETRY, str(image)],
                cwd=ROOT, capture_output=True, check=False,
            )
        except OSError:
            return ()
        return () if listed.returncode == 0 else ("-T", "raw")
