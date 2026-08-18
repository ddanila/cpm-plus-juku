#!/usr/bin/env python3
"""Negative and determinism checks for the CP/M utility admission catalogue."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/audit_cpm3_candidates.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "audit_cpm3_candidates", MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load candidate audit module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_rejection(module, path: Path, value: dict[str, object],
                      marker: str) -> None:
    path.write_text(json.dumps(value))
    module.CATALOGUE = path
    try:
        module.audit()
    except ValueError as error:
        if marker not in str(error):
            raise AssertionError(f"wrong catalogue rejection: {error}")
    else:
        raise AssertionError(f"catalogue mutation was accepted: {marker}")


def main() -> int:
    module = load_module()
    catalogue, candidates = module.audit()
    if len(candidates) != 23:
        raise AssertionError(f"candidate count differs: {len(candidates)}")
    expected = module.render(catalogue, candidates)
    if module.DEFAULT_OUTPUT.read_text() != expected:
        raise AssertionError("checked-in candidate catalogue is stale")

    with tempfile.TemporaryDirectory(prefix="cpm3-candidate-audit.") as name:
        directory = Path(name)
        candidate_path = directory / "candidates.json"
        original = json.loads(module.CATALOGUE.read_text())

        changed = json.loads(json.dumps(original))
        changed["candidates"][0]["sha256"] = "0" * 64
        require_rejection(module, candidate_path, changed, "binary differs")

        changed = json.loads(json.dumps(original))
        changed["candidates"][0]["source_members"] = ["missing.plm"]
        require_rejection(module, candidate_path, changed, "sources absent")

        changed = json.loads(json.dumps(original))
        pip = next(item for item in changed["candidates"]
                   if item["name"] == "PIP.COM")
        pip["status"] = "candidate"
        require_rejection(module, candidate_path, changed,
                          "admission-pinned candidate")

        changed = json.loads(json.dumps(original))
        changed["candidates"] = changed["candidates"][:19]
        require_rejection(module, candidate_path, changed,
                          "outside planned range")

        module.CATALOGUE = ROOT / "third_party/cpm3/releases/candidates.json"
        binary = directory / module.BINARY_ARCHIVE.name
        shutil.copyfile(module.BINARY_ARCHIVE, binary)
        data = bytearray(binary.read_bytes())
        data[-1] ^= 1
        binary.write_bytes(data)
        module.BINARY_ARCHIVE = binary
        try:
            module.audit()
        except ValueError as error:
            if "pinned archive differs" not in str(error):
                raise AssertionError(f"wrong archive rejection: {error}")
        else:
            raise AssertionError("mutated candidate archive was accepted")

    print("CPM3-CANDIDATE-AUDIT-TEST: PASS (23 candidates; negative gates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
