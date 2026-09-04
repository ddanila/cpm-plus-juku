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

    # DRI PL/M output uses bounded PCHL switch tables. Exact source-backed
    # targets remain reachable and audited; a policy not exercised is stale.
    dispatch = bytes((
        0xE9,                   # PCHL -> 0103h and 0106h
        0x00, 0x00,             # table/data
        0xC3, 0x00, 0x00,       # JMP 0000h
        0xC3, 0x00, 0x00,       # JMP 0000h
    ))
    result, _ = module.audit_bytes(
        dispatch, indirect_targets={0x0100: (0x0103, 0x0106)},
    )
    assert result["approved_bounded_pchl"] == [{
        "address": "0100", "targets": ["0103", "0106"],
    }]

    # CP/M function 0 is terminal, as is a JMP-tail-call into BDOS. This is
    # why the following 8086 compatibility bytes are data, not 8080 code.
    dri_exit = bytes((
        0x0E, 0x00,             # MVI C,00h
        0xCD, 0x05, 0x00,       # CALL 0005h; does not return
        0xCD, 0x20, 0x00,       # unreachable 8086 INT 20h guard
    ))
    result, _ = module.audit_bytes(dri_exit)
    assert result["approved_bdos_system_resets"] == 1
    assert result["data_bytes"] == 3
    tail, _ = module.audit_bytes(bytes((0xC3, 0x05, 0x00)))
    assert tail["approved_bdos_tail_calls"] == 1

    rom_call, _ = module.audit_bytes(
        bytes((0xCD, 0x5F, 0xD6, 0xC3, 0x00, 0x00)),
        external_call_targets={0xD65F: "JCGCONCONFIG ABI 1.5 gate"},
    )
    assert rom_call["approved_external_calls"] == [{
        "address": "D65F", "reason": "JCGCONCONFIG ABI 1.5 gate",
    }]

    # A source-proven fatal routine suppresses fallthrough after its caller.
    fatal = bytes((
        0xCD, 0x06, 0x01,       # CALL 0106h (non-returning)
        0x08, 0x10, 0x18,       # unreachable data
        0x0E, 0x00,             # MVI C,00h
        0xCD, 0x05, 0x00,       # CALL 0005h
    ))
    result, _ = module.audit_bytes(
        fatal, noreturn_targets={0x0106: "source fatal exit"},
    )
    assert result["approved_noreturn_targets"] == [{
        "address": "0106", "reason": "source fatal exit",
    }]

    dynamic, _ = module.audit_bytes(
        bytes((0xE9,)),
        dynamic_indirect_exits={0x0100: "debugger transfers to debuggee"},
    )
    assert dynamic["approved_dynamic_pchl"][0]["address"] == "0100"
    patched, _ = module.audit_bytes(
        bytes((0xC3, 0x34, 0x12)),
        dynamic_direct_exits={0x0100: "loader patches the next-RSX address"},
    )
    assert patched["approved_dynamic_direct_exits"][0]["address"] == "0100"
    mixed, _ = module.audit_bytes(
        bytes((0xE9, 0x00, 0xC3, 0x00, 0x00)),
        indirect_targets={0x0100: (0x0102,)},
        indirect_external_targets={
            0x0100: {0x0000: "jump-table warm boot"},
        },
    )
    assert mixed["approved_external_pchl"][0]["targets"][0][
        "address"
    ] == "0000"
    called, _ = module.audit_bytes(
        bytes((0xE9, 0xC3, 0x00, 0x00)),
        dynamic_indirect_calls={
            0x0100: ((0x0101,), "calls user code with stacked return"),
        },
    )
    assert called["approved_dynamic_pchl_calls"][0][
        "return_continuations"
    ] == ["0101"]

    reject(module, bytes((0x08,)), "undocumented/Z80-only opcode")
    reject(module, bytes((0xCD, 0x34, 0x12)), "unapproved external call")
    reject(module, bytes((0xDB, 0x09)), "unapproved direct hardware I/O")
    reject(module, bytes((0xE9,)), "unapproved indirect PCHL")
    reject(module, bytes((0xC3, 0x01, 0x01)), "enters the operand")
    reject(module, bytes((0x00,)), "falls out of the COM image")
    try:
        module.audit_bytes(
            bytes((0xC3, 0x00, 0x00, 0xC9)),
            dynamic_indirect_exits={0x0103: "stale policy"},
        )
    except module.AuditError as error:
        assert "unused source-backed policy" in str(error)
    else:
        raise AssertionError("COM audit accepted unused policy")

    print("8080-COM-AUDIT-TEST: PASS (source-aware control-flow gates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
