#!/usr/bin/env python3
"""Prove pinned CP/M 3 utilities retain source, license, and exact bytes."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import tempfile


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/extract_cpm3_utilities.py"


def load_module():
    spec = importlib.util.spec_from_file_location("extract_cpm3_utilities", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load CP/M 3 utility extractor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_module()
    provenance, files = module.expected_files()
    required = {
        "PIP.COM", "SHOW.COM", "SET.COM", "DEVICE.COM", "DATE.COM",
        "SUBMIT.COM", "SETDEF.COM", "DUMP.COM", "HELP.COM", "HELP.HLP",
    }
    if set(files) != required:
        raise AssertionError(f"selected CP/M 3 utility set differs: {set(files)}")
    if not (ROOT / "third_party/cpm3/LICENSE.md").is_file() or \
            provenance.get("license") != "../LICENSE.md":
        raise AssertionError("CP/M 3 utility license record differs")
    for name, data in files.items():
        record = provenance["selected_distribution_files"][name]
        if len(data) != record["bytes"] or module.digest(data) != record["sha256"]:
            raise AssertionError(f"selected CP/M 3 utility differs: {name}")

    with tempfile.TemporaryDirectory(prefix="cpm3-utility-inputs.") as name:
        releases = Path(name) / "releases"
        shutil.copytree(module.RELEASES, releases)
        archive = releases / "cpm3bin_unix-20260607.zip"
        changed = bytearray(archive.read_bytes())
        changed[-1] ^= 1
        archive.write_bytes(changed)
        module.RELEASES = releases
        module.PROVENANCE = releases / "provenance.json"
        try:
            module.expected_files()
        except ValueError as error:
            if "archive differs" not in str(error):
                raise AssertionError(f"wrong archive rejection: {error}")
        else:
            raise AssertionError("changed CP/M 3 binary archive was accepted")
    print("CPM3-UTILITY-INPUTS-TEST: PASS (10 files and source mappings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
