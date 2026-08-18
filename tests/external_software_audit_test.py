#!/usr/bin/env python3
"""Negative checks for the external-software admission boundary."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "external_software_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "external_software_audit", MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load external-software audit module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reject(module, path: Path, data: dict, marker: str) -> None:
    path.write_text(json.dumps(data))
    module.RESULTS = path
    try:
        module.validate()
    except SystemExit as error:
        if marker not in str(error):
            raise AssertionError(f"wrong external-audit rejection: {error}")
    else:
        raise AssertionError(f"external-audit mutation accepted: {marker}")


def main() -> int:
    module = load_module()
    module.validate()
    original_path = module.RESULTS
    original = json.loads(original_path.read_text())
    with tempfile.TemporaryDirectory(
            prefix="external-software-audit-test.") as name:
        path = Path(name) / "results.json"

        changed = json.loads(json.dumps(original))
        changed["candidates"]["cpm-ls"]["decision"] = "admit"
        reject(module, path, changed, "unreviewed admission state")

        changed = json.loads(json.dumps(original))
        changed["candidates"]["cpm-ls"]["audited_port"][
            "tpa_bytes_after_static_image"] += 1
        reject(module, path, changed, "TPA accounting")

        changed = json.loads(json.dumps(original))
        changed["candidates"]["hist-rsx"]["source_present"] = True
        reject(module, path, changed, "HIST admission boundary")

        changed = json.loads(json.dumps(original))
        changed["candidates"]["fig-forth-1.1"][
            "missing_package_parts"] = ["editor"]
        reject(module, path, changed, "FIG-Forth deferral boundary")

        changed = json.loads(json.dumps(original))
        changed["candidates"]["uplm80"]["fixture"][
            "optimized_jr_instructions"] = 0
        reject(module, path, changed, "uplm80 rejection")

    module.RESULTS = original_path
    print("EXTERNAL-SOFTWARE-TEST: PASS (five negative gates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
