#!/usr/bin/env python3
"""Guard DIAG's self-contained ROM fingerprints and command policy."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COSIM = ROOT.parent / "8080-cosim"
COM = ROOT / "build" / "diag.cim"

ENTRIES = (
    ("roms/ekta24.bin", "EktaSoft #0024 / RomBios 3.42", 1),
    ("roms/ekta31.bin", "EktaSoft #0031 / RomBios 3.43", 1),
    ("roms/ekta32.bin", "EktaSoft #0032 / RomBios 2.43", 1),
    ("roms/ekta35.bin", "EktaSoft #0035 / RomBios 3.43", 1),
    ("roms/ekta37.bin", "EktaSoft #0037 / RomBios 3.43m", 1),
    ("roms/ekta43.bin", "EktaSoft #0043 / RomBios 2.43m", 1),
    ("roms/jmon33.bin", "Juku monitor 3.3", 1),
    ("roms/jmon22.bin", "Juku monitor 2.2 (known damaged archive)", 4),
    (
        "spinoffs/jukuravi/remix/ekta4401.bin",
        "EktaSoft 4.4 #01 / RomBios 3.43m",
        1,
    ),
    (
        "spinoffs/jukuravi/remix/ekta4402.bin",
        "EktaSoft 4.4 #02 / RomBios 3.43m",
        1,
    ),
    (
        "spinoffs/jukuravi/network-rom/juku-network-rom-abi1.bin",
        "JukuNet C4 / ROM ABI 1.0",
        2,
    ),
    (
        "spinoffs/jukuravi/network-rom/juku-network-rom-abi1.1-c5.bin",
        "JukuNet C5 / ROM ABI 1.1",
        2,
    ),
    (
        "spinoffs/jukuravi/network-rom/juku-network-rom-abi1.2-c6.bin",
        "JukuNet C6 / ROM ABI 1.2",
        2,
    ),
    (
        "spinoffs/jukuravi/network-rom/juku-network-rom-abi1.2-c7.bin",
        "JukuNet C7 / ROM ABI 1.2",
        2,
    ),
    (
        "spinoffs/jukuravi/network-rom/juku-network-rom-abi1.3-c8.bin",
        "JukuNet C8 / ROM ABI 1.3",
        2,
    ),
)


def fingerprint(image: bytes) -> bytes:
    assert len(image) == 0x4000
    visible = image[0x1800:]
    return bytes(
        sum(visible[offset:offset + 0xA00]) & 0xFF
        for offset in range(0, 0x2800, 0xA00)
    )


def fail(message: str) -> None:
    raise SystemExit(f"DIAG-ROM-IDENTITY: FAIL: {message}")


def main() -> None:
    payload = COM.read_bytes()
    source = (ROOT / "src" / "diag.asm").read_text()
    expected = [
        (fingerprint((COSIM / path).read_bytes()), identity, kind)
        for path, identity, kind in ENTRIES
    ]
    cursor = payload.find(expected[0][0])
    if cursor < 0:
        fail("compiled fingerprint table is missing")

    for wanted_fingerprint, wanted_identity, wanted_class in expected:
        observed_fingerprint = payload[cursor:cursor + 4]
        pointer = int.from_bytes(payload[cursor + 4:cursor + 6], "little")
        observed_class = payload[cursor + 6]
        identity_offset = pointer - 0x100
        end = payload.find(b"$", identity_offset)
        if end < 0:
            fail(f"unterminated identity at {pointer:04X}h")
        observed_identity = payload[identity_offset:end].rstrip(b"\r\n").decode()
        if (
            observed_fingerprint != wanted_fingerprint
            or observed_identity != wanted_identity
            or observed_class != wanted_class
        ):
            fail(
                f"entry differs at {cursor + 0x100:04X}h: "
                f"fingerprint={observed_fingerprint.hex().upper()} "
                f"identity={observed_identity!r} class={observed_class}"
            )
        cursor += 7

    if payload[cursor:cursor + 7] != b"\0" * 7:
        fail("fingerprint table terminator differs")
    for required in (
        "jz      show_usage",
        "call    select_rom_reads",
        "call    diag_s21_config_read",
        'include "s21-config.asm"',
    ):
        if required not in source:
            fail(f"source policy is missing {required!r}")
    for forbidden in ("ROM_DIAG_GATE", "ROM_INFO_GATE"):
        if forbidden in source:
            fail(f"DIAG still calls ROM-owned procedure {forbidden}")

    print(
        "DIAG-ROM-IDENTITY: PASS "
        f"({len(expected)} exact images, stock/JukuNet direct mechanisms)"
    )


if __name__ == "__main__":
    main()
