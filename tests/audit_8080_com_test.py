#!/usr/bin/env python3
"""Positive and fail-closed checks for the flow-aware COM audit."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "audit_8080_com.py"


def load_module():
    spec = importlib.util.spec_from_file_location("audit_8080_com", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load 8080 COM audit module")
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through the registered module.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def reject(module, image: bytes, marker: str) -> None:
    try:
        module.audit_bytes(image)
    except module.AuditError as error:
        if marker not in str(error):
            raise AssertionError(f"wrong COM-audit rejection: {error}")
    else:
        raise AssertionError(f"COM audit accepted invalid image: {marker}")


def main() -> int:
    module = load_module()

    # CALL 0005h and JMP 0000h are the only external CP/M control gates. The
    # unreachable bytes deliberately include every forbidden opcode, proving
    # that strings/data are accounted for without being misclassified as code.
    image = bytes((
        0x0E, 0x09,             # MVI C,09h
        0xCD, 0x05, 0x00,       # CALL 0005h
        0xC3, 0x00, 0x00,       # JMP 0000h
        0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38,
        0xCB, 0xD9, 0xDD, 0xED, 0xFD,
    ))
    result, listing = module.audit_bytes(image)
    assert result["reachable_instructions"] == 3
    assert result["reachable_code_bytes"] == 8
    assert result["data_bytes"] == len(image) - 8
    assert result["approved_runtime_dependencies"] == [
        "0000h CP/M warm boot",
        "0005h CP/M BDOS call gate",
    ]
    assert "DB 08 10 18 20 28 30 38 CB" in listing

    # z88dk uses this exact callee-cleanup return sequence. It is a bounded
    # internal return, whereas a free-standing PCHL remains forbidden.
    trampoline = bytes((
        0xCD, 0x06, 0x01,       # CALL 0106h
        0xC3, 0x00, 0x00,       # JMP 0000h
        0xE3, 0xE9,             # XTHL; PCHL
    ))
    result, _ = module.audit_bytes(trampoline)
    assert result["approved_xthl_pchl_returns"] == 1

    reject(module, bytes((0x08,)), "undocumented/Z80-only opcode")
    reject(module, bytes((0xCD, 0x34, 0x12)), "unapproved external call")
    reject(module, bytes((0xDB, 0x09)), "unapproved direct hardware I/O")
    reject(module, bytes((0xE9,)), "unapproved indirect PCHL")
    reject(module, bytes((0xC3, 0x01, 0x01)), "enters the operand")
    reject(module, bytes((0x00,)), "falls out of the COM image")

    print("8080-COM-AUDIT-TEST: PASS (complete listing + six negative gates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
