#!/usr/bin/env python3
"""Combine a CP/M Plus SYS file and Juku adapter into a RAM image."""

from __future__ import annotations

import argparse
from pathlib import Path


PREFIX_SIZE = 512
DEFAULT_LOAD_ADDRESS = 0x7000
DEFAULT_ADAPTER_ADDRESS = 0xA000
DEFAULT_ENTRY_ADDRESS = 0x9C00
DEFAULT_END_ADDRESS = 0xB000
MAGIC = b"JUKURM1\x1a"


def crc16_ibm(data: bytes) -> int:
    crc = 0
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc


def unpack_sys(data: bytes, *, load_address: int, adapter_address: int,
               entry_address: int, end_address: int) -> tuple[bytearray, int]:
    if len(data) < 256 or len(data) % 128:
        raise ValueError("CPM3.SYS must contain complete 128-byte records")
    common_top, common_pages, bank_top, bank_pages = data[:4]
    entry = int.from_bytes(data[4:6], "little")
    if bank_top or bank_pages:
        raise ValueError("only a non-banked CPM3.SYS is supported")
    if entry != entry_address or common_top * 256 != adapter_address:
        raise ValueError("unexpected CP/M Plus entry or memory top")
    records = common_pages * 2
    payload = data[256:]
    if len(payload) != records * 128:
        raise ValueError("CPM3.SYS common length does not match its header")
    if not 0 <= load_address < adapter_address < end_address <= 0x10000:
        raise ValueError("invalid Juku RAM container layout")
    memory = bytearray(end_address - load_address)
    for index in range(records):
        address = adapter_address - (index + 1) * 128
        offset = address - load_address
        if offset < 0:
            raise ValueError("CP/M Plus system starts below the load address")
        memory[offset:offset + 128] = payload[index * 128:(index + 1) * 128]
    return memory, adapter_address - common_pages * 256


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adapter", type=Path)
    parser.add_argument("cpm3_sys", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--load-address", type=lambda value: int(value, 0),
                        default=DEFAULT_LOAD_ADDRESS)
    parser.add_argument("--adapter-address", type=lambda value: int(value, 0),
                        default=DEFAULT_ADAPTER_ADDRESS)
    parser.add_argument("--entry-address", type=lambda value: int(value, 0),
                        default=DEFAULT_ENTRY_ADDRESS)
    parser.add_argument("--end-address", type=lambda value: int(value, 0),
                        default=DEFAULT_END_ADDRESS)
    args = parser.parse_args()

    adapter = args.adapter.read_bytes()
    if not adapter:
        raise ValueError("Juku CP/M Plus adapter is empty")
    if args.adapter_address + len(adapter) > args.end_address:
        raise ValueError("Juku adapter exceeds the RAM container")
    memory, system_base = unpack_sys(
        args.cpm3_sys.read_bytes(), load_address=args.load_address,
        adapter_address=args.adapter_address, entry_address=args.entry_address,
        end_address=args.end_address,
    )
    adapter_offset = args.adapter_address - args.load_address
    if any(memory[adapter_offset:adapter_offset + len(adapter)]):
        raise ValueError("CP/M Plus system overlaps the adapter window")
    memory[adapter_offset:adapter_offset + len(adapter)] = adapter

    header = bytearray([0xE5]) * PREFIX_SIZE
    header[:8] = MAGIC
    header[8:10] = args.load_address.to_bytes(2, "little")
    header[10:12] = args.entry_address.to_bytes(2, "little")
    header[12:14] = len(memory).to_bytes(2, "little")
    header[14:16] = crc16_ibm(memory).to_bytes(2, "little")
    args.output.write_bytes(header + memory)
    print(
        f"Juku CP/M Plus image: adapter={len(adapter)} bytes, "
        f"system={system_base:04X}h..{args.adapter_address - 1:04X}h, "
        f"adapter={args.adapter_address:04X}h.."
        f"{args.adapter_address + len(adapter) - 1:04X}h, "
        f"entry={args.entry_address:04X}h, "
        f"container={args.load_address:04X}h..{args.end_address - 1:04X}h, "
        f"CRC16/IBM={crc16_ibm(memory):04X}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
