#!/usr/bin/env python3
"""Audit the C12 active-console VIDTEST without weakening the default gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "tools/audit_8080_com.py"
C12_VIDTEST = ROOT / "build/vidtest-c12.cim"
LEGACY_VIDTEST = ROOT / "build/vidtest.cim"
LEGACY_SHA256 = "07809927ad4094974cd04606387af82dc4ad49ea1a80fefb2e19fc1e682517c9"


def load_auditor():
    spec = importlib.util.spec_from_file_location("audit_8080_com", AUDITOR)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load 8080 COM auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    import hashlib

    auditor = load_auditor()
    legacy = LEGACY_VIDTEST.read_bytes()
    c12 = C12_VIDTEST.read_bytes()
    if hashlib.sha256(legacy).hexdigest() != LEGACY_SHA256:
        raise AssertionError("C12 work changed the legacy VIDTEST binary")
    result, _ = auditor.audit_bytes(
        c12,
        external_call_targets={0xD65F: "JCGCONCONFIG ABI 1.5 gate"},
    )
    if result["approved_external_calls"] != [{
            "address": "D65F", "reason": "JCGCONCONFIG ABI 1.5 gate"}] or \
            result["forbidden_reachable_opcodes"] != 0 or \
            result["unapproved_runtime_dependencies"] != 0:
        raise AssertionError("C12 VIDTEST executable audit differs")
    print(
        "C12-VIDTEST-TEST: PASS "
        f"({len(c12)} bytes; active ABI 1.5 query; legacy immutable)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
