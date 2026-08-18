#!/usr/bin/env python3
"""Negative checks for the pinned high-level compiler experiment."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "compiler_comparison.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "compiler_comparison", MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load compiler comparison module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reject(module, path: Path, data: dict, marker: str) -> None:
    path.write_text(json.dumps(data))
    module.RESULTS = path
    try:
        module.load_and_validate()
    except SystemExit as error:
        if marker not in str(error):
            raise AssertionError(f"wrong compiler-record rejection: {error}")
    else:
        raise AssertionError(f"compiler-record mutation accepted: {marker}")


def main() -> int:
    module = load_module()
    module.load_and_validate()
    original_path = module.RESULTS
    original = json.loads(original_path.read_text())
    with tempfile.TemporaryDirectory(
            prefix="compiler-comparison-test.") as name:
        path = Path(name) / "results.json"

        changed = json.loads(json.dumps(original))
        changed["toolchains"]["millfork"]["programs"]["hello"][
            "source_sha256"] = "0" * 64
        reject(module, path, changed, "source fixture changed")

        changed = json.loads(json.dumps(original))
        changed["toolchains"]["z88dk"]["programs"]["wc"][
            "tpa_bytes_after_static_image"] += 1
        reject(module, path, changed, "incorrect TPA accounting")

        changed = json.loads(json.dumps(original))
        changed["strict_8080_cosim"]["tpa_z80_prefix_fetches"] = 1
        reject(module, path, changed, "forbidden opcode")

        changed = json.loads(json.dumps(original))
        changed["decision"]["production_baseline"] = "z88dk"
        reject(module, path, changed, "must not silently replace")

    module.RESULTS = original_path
    print("COMPILER-COMPARISON-TEST: PASS (four negative gates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
