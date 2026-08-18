#!/usr/bin/env python3
"""Negative gates for CP/M 3 development-tool admission."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "audit_cpm3_development_tools.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "audit_cpm3_development_tools", MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load development-tool audit module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reject(module, path: Path, data: dict, marker: str) -> None:
    path.write_text(json.dumps(data))
    module.AUDIT = path
    try:
        module.audit()
    except ValueError as error:
        if marker not in str(error):
            raise AssertionError(f"wrong development-tool rejection: {error}")
    else:
        raise AssertionError(f"development-tool mutation accepted: {marker}")


def main() -> int:
    module = load_module()
    module.audit()
    original_path = module.AUDIT
    original = json.loads(original_path.read_text())
    with tempfile.TemporaryDirectory(prefix="cpm3-dev-tool-test.") as name:
        path = Path(name) / "audit.json"

        changed = json.loads(json.dumps(original))
        changed["programs"]["ASM.COM"]["decision"] = "admit"
        reject(module, path, changed, "unavailable disposition")

        changed = json.loads(json.dumps(original))
        changed["programs"]["ED.COM"]["sha256"] = "0" * 64
        reject(module, path, changed, "ED.COM binary differs")

        changed = json.loads(json.dumps(original))
        changed["programs"]["SID.COM"]["strict_8080_cosim"][
            "tpa_z80_prefix_fetches"] = 1
        reject(module, path, changed, "SID.COM strict-8080 evidence")

        changed = json.loads(json.dumps(original))
        changed["programs"]["ED.COM"]["strict_8080_cosim"][
            "write_requests"] = 0
        reject(module, path, changed, "ED.COM save/readback evidence")

        changed = json.loads(json.dumps(original))
        changed["programs"]["RMAC.COM"]["profile"] = "dev"
        reject(module, path, changed, "RMAC.COM host-only boundary")

    module.AUDIT = original_path
    print("CPM3-DEV-TOOLS-TEST: PASS (five negative gates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
