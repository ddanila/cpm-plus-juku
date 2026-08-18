#!/usr/bin/env python3
"""Flow-aware static Intel 8080 audit for CP/M COM binaries.

The audit follows reachable control flow from 0100h, rejects undocumented
8080 opcode aliases and target-specific I/O, and permits only CP/M's warm-boot
and BDOS gates as external control transfers.  Its canonical listing includes
both reachable instructions and every remaining byte as data, so its digest
accounts for the complete executable without interpreting strings as code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

ORIGIN = 0x0100
UNDEFINED = {
    0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38,
    0xCB, 0xD9, 0xDD, 0xED, 0xFD,
}
CONDITIONAL_JUMPS = {0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA}
CONDITIONAL_CALLS = {0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC}
CONDITIONAL_RETURNS = {0xC0, 0xC8, 0xD0, 0xD8, 0xE0, 0xE8, 0xF0, 0xF8}
RST_OPCODES = {0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF}
DIRECT_IO = {0xD3, 0xDB}


class AuditError(ValueError):
    """The reachable program violates the standalone Intel 8080 policy."""


@dataclass(frozen=True)
class Instruction:
    address: int
    opcode: int
    raw: bytes
    text: str

    @property
    def next_address(self) -> int:
        return self.address + len(self.raw)

    @property
    def word(self) -> int:
        if len(self.raw) != 3:
            raise AssertionError("instruction has no word operand")
        return self.raw[1] | (self.raw[2] << 8)


def opcode_formats() -> tuple[str, ...]:
    low = """
NOP
LXI B,%w
STAX B
INX B
INR B
DCR B
MVI B,%b
RLC
ILL
DAD B
LDAX B
DCX B
INR C
DCR C
MVI C,%b
RRC
ILL
LXI D,%w
STAX D
INX D
INR D
DCR D
MVI D,%b
RAL
ILL
DAD D
LDAX D
DCX D
INR E
DCR E
MVI E,%b
RAR
ILL
LXI H,%w
SHLD %w
INX H
INR H
DCR H
MVI H,%b
DAA
ILL
DAD H
LHLD %w
DCX H
INR L
DCR L
MVI L,%b
CMA
ILL
LXI SP,%w
STA %w
INX SP
INR M
DCR M
MVI M,%b
STC
ILL
DAD SP
LDA %w
DCX SP
INR A
DCR A
MVI A,%b
CMC
""".strip().splitlines()
    registers = ("B", "C", "D", "E", "H", "L", "M", "A")
    move = [
        "HLT" if destination == "M" and source == "M"
        else f"MOV {destination},{source}"
        for destination in registers
        for source in registers
    ]
    arithmetic = [
        f"{operation} {register}"
        for operation in ("ADD", "ADC", "SUB", "SBB", "ANA", "XRA", "ORA", "CMP")
        for register in registers
    ]
    high = """
RNZ
POP B
JNZ %w
JMP %w
CNZ %w
PUSH B
ADI %b
RST 0
RZ
RET
JZ %w
ILL
CZ %w
CALL %w
ACI %b
RST 1
RNC
POP D
JNC %w
OUT %b
CNC %w
PUSH D
SUI %b
RST 2
RC
ILL
JC %w
IN %b
CC %w
ILL
SBI %b
RST 3
RPO
POP H
JPO %w
XTHL
CPO %w
PUSH H
ANI %b
RST 4
RPE
PCHL
JPE %w
XCHG
CPE %w
ILL
XRI %b
RST 5
RP
POP PSW
JP %w
DI
CP %w
PUSH PSW
ORI %b
RST 6
RM
SPHL
JM %w
EI
CM %w
ILL
CPI %b
RST 7
""".strip().splitlines()
    formats = tuple(low + move + arithmetic + high)
    if len(formats) != 256:
        raise AssertionError(f"8080 opcode table has {len(formats)} entries")
    return formats


OPCODE_FORMATS = opcode_formats()


def decode(image: bytes, address: int, origin: int = ORIGIN) -> Instruction:
    offset = address - origin
    if not 0 <= offset < len(image):
        raise AuditError(f"control flow leaves COM image at {address:04X}h")
    opcode = image[offset]
    template = OPCODE_FORMATS[opcode]
    length = 3 if "%w" in template else 2 if "%b" in template else 1
    raw = image[offset:offset + length]
    if len(raw) != length:
        raise AuditError(f"truncated instruction at {address:04X}h")
    if "%w" in template:
        value = raw[1] | (raw[2] << 8)
        text = template.replace("%w", f"{value:04X}h")
    elif "%b" in template:
        text = template.replace("%b", f"{raw[1]:02X}h")
    else:
        text = template
    return Instruction(address, opcode, raw, text)


def audit_bytes(image: bytes, *, origin: int = ORIGIN) -> tuple[dict, str]:
    if not image:
        raise AuditError("COM image is empty")
    if origin + len(image) > 0x10000:
        raise AuditError("COM image exceeds the 8080 address space")

    instructions: dict[int, Instruction] = {}
    occupied: dict[int, int] = {}
    pending = [origin]
    dependencies: set[str] = set()
    approved_indirect_returns = 0

    def add_control_target(target: int, source: Instruction, kind: str) -> None:
        if origin <= target < origin + len(image):
            pending.append(target)
            return
        if target == 0x0000 and kind in ("jump", "rst"):
            dependencies.add("0000h CP/M warm boot")
            return
        if target == 0x0005 and kind == "call":
            dependencies.add("0005h CP/M BDOS call gate")
            return
        raise AuditError(
            f"unapproved external {kind} from {source.address:04X}h "
            f"to {target:04X}h",
        )

    while pending:
        address = pending.pop()
        if address in instructions:
            continue
        if address in occupied:
            raise AuditError(
                f"control target {address:04X}h enters the operand of "
                f"{occupied[address]:04X}h",
            )
        instruction = decode(image, address, origin)
        if instruction.opcode in UNDEFINED:
            raise AuditError(
                f"undocumented/Z80-only opcode {instruction.opcode:02X}h "
                f"is reachable at {address:04X}h",
            )
        if instruction.opcode in DIRECT_IO:
            raise AuditError(
                f"unapproved direct hardware I/O is reachable at "
                f"{address:04X}h: {instruction.text}",
            )
        for byte_address in range(address, instruction.next_address):
            previous = occupied.get(byte_address)
            if previous is not None and previous != address:
                raise AuditError(
                    f"overlapping instructions at {previous:04X}h and "
                    f"{address:04X}h",
                )
            occupied[byte_address] = address
        instructions[address] = instruction

        opcode = instruction.opcode
        follow_next = True
        if opcode == 0xC3 or opcode in CONDITIONAL_JUMPS:
            add_control_target(instruction.word, instruction, "jump")
            follow_next = opcode in CONDITIONAL_JUMPS
        elif opcode == 0xCD or opcode in CONDITIONAL_CALLS:
            add_control_target(instruction.word, instruction, "call")
        elif opcode == 0xC9:
            follow_next = False
        elif opcode in CONDITIONAL_RETURNS:
            pass
        elif opcode in RST_OPCODES:
            vector = opcode & 0x38
            add_control_target(vector, instruction, "rst")
            # RST 0 is the CP/M warm-boot exit and does not return.
            follow_next = vector != 0
        elif opcode == 0xE9:
            previous = instructions.get(address - 1)
            if previous is None or previous.opcode != 0xE3:
                raise AuditError(
                    f"unapproved indirect PCHL transfer is reachable at "
                    f"{address:04X}h",
                )
            # z88dk's 8080 callee-cleanup helper loads the caller's return
            # address, exchanges it with the stack top, then uses PCHL as an
            # indirect RET.  Accept only that exact XTHL/PCHL terminator.
            approved_indirect_returns += 1
            follow_next = False
        elif opcode == 0x76:
            follow_next = False

        if follow_next:
            if instruction.next_address >= origin + len(image):
                raise AuditError(
                    f"reachable instruction at {address:04X}h falls out "
                    "of the COM image",
                )
            pending.append(instruction.next_address)

    lines = []
    address = origin
    end = origin + len(image)
    while address < end:
        instruction = instructions.get(address)
        if instruction is not None:
            encoded = " ".join(f"{value:02X}" for value in instruction.raw)
            lines.append(
                f"{address:04X}: {encoded:<8}  {instruction.text}",
            )
            address = instruction.next_address
            continue
        data = bytearray()
        while address + len(data) < end and len(data) < 8:
            candidate = address + len(data)
            if candidate in instructions:
                break
            data.append(image[candidate - origin])
        encoded = " ".join(f"{value:02X}" for value in data)
        lines.append(f"{address:04X}: {encoded:<23}  DB {encoded}")
        address += len(data)
    listing = "\n".join(lines) + "\n"
    code_bytes = sum(len(item.raw) for item in instructions.values())
    result = {
        "origin": f"{origin:04X}",
        "reachable_instructions": len(instructions),
        "reachable_code_bytes": code_bytes,
        "data_bytes": len(image) - code_bytes,
        "approved_runtime_dependencies": sorted(dependencies),
        "approved_xthl_pchl_returns": approved_indirect_returns,
        "listing_sha256": hashlib.sha256(listing.encode("ascii")).hexdigest(),
        "forbidden_reachable_opcodes": 0,
        "unapproved_runtime_dependencies": 0,
    }
    return result, listing


def audit_file(path: Path) -> tuple[dict, str]:
    return audit_bytes(path.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--listing-dir", type=Path)
    args = parser.parse_args()
    results = {}
    if args.listing_dir:
        args.listing_dir.mkdir(parents=True, exist_ok=True)
    for path in args.images:
        result, listing = audit_file(path)
        results[str(path)] = result
        if args.listing_dir:
            (args.listing_dir / f"{path.name}.dis").write_text(listing)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
