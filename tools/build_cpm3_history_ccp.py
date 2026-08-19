#!/usr/bin/env python3
"""Rebuild the pinned DRI CCP exactly, then apply the Juku history patch."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "third_party/cpm3/releases/cpm3src_unix-20260607.zip"
PINNED_CCP = ROOT / "third_party/cpm3/ccp.com"
PATCH = ROOT / "patches/ccp3-history.patch"
ZXCC = ROOT / "build/bin/zxcc"
ARCHIVE_SHA256 = "d90cda1f25112ace3b436c4054304ace423331caa1f034c44f26698728a9fdb7"
UPSTREAM_SHA256 = "f1837073d217075223d17dd81d068481819665273b59fbb3502c2f9068e8a671"
MEMBERS = (
    "ccp3.asm", "ccpdate.asm", "loader3.asm", "makedate.lib",
    "mac.com", "rmac.com", "drlink.com",
)
HISTORY_START = 0xD571
HISTORY_END = 0xD5BF
ROM_GUARD_START = 0xD5C0


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def run(command: list[str], directory: Path) -> str:
    result = subprocess.run(
        command, cwd=directory, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    output = result.stdout.replace("\r\n", "\n").replace("\r", "\n")
    upper = output.upper()
    require("ERROR" not in upper or "NO ERROR" in upper,
            f"archived CP/M tool reported an error: {' '.join(command)}\n"
            f"{output}")
    return output


def patch_hex(base: bytes, encoded: bytes) -> bytes:
    """Apply the ordered type-0 Intel HEX stream like upstream HEXPAT."""
    image = bytearray(base)
    cursor = 0x100
    saw_end = False
    for line_number, raw in enumerate(encoded.splitlines(), 1):
        raw = raw.rstrip(b"\x1a").strip()
        if not raw:
            continue
        require(raw.startswith(b":"),
                f"Intel HEX line {line_number} has no colon")
        try:
            record = bytes.fromhex(raw[1:].decode("ascii"))
        except (UnicodeDecodeError, ValueError) as error:
            raise ValueError(f"invalid Intel HEX line {line_number}") from error
        require(len(record) >= 5 and len(record) == record[0] + 5,
                f"Intel HEX length differs at line {line_number}")
        require(sum(record) & 0xFF == 0,
                f"Intel HEX checksum differs at line {line_number}")
        count = record[0]
        address = (record[1] << 8) | record[2]
        record_type = record[3]
        require(record_type in (0, 1),
                f"unsupported Intel HEX type {record_type}")
        if record_type == 1 or count == 0:
            saw_end = True
            break
        require(address >= cursor,
                f"Intel HEX records overlap at {address:04X}h")
        offset = address - 0x100
        if len(image) < offset:
            image.extend(b"\x00" * (offset - len(image)))
        end = offset + count
        if len(image) < end:
            image.extend(b"\x00" * (end - len(image)))
        image[offset:end] = record[4:4 + count]
        cursor = address + count
    require(saw_end, "Intel HEX end record is absent")
    return bytes(image)


def prepare(work: Path) -> None:
    require(digest(ARCHIVE.read_bytes()) == ARCHIVE_SHA256,
            "pinned CP/M 3 source archive differs")
    with zipfile.ZipFile(ARCHIVE) as archive:
        require(all(member in archive.namelist() for member in MEMBERS),
                "CCP source member is absent from the pinned archive")
        for member in MEMBERS:
            (work / member).write_bytes(archive.read(member))


def build_loader(work: Path) -> bytes:
    run([str(ZXCC), "rmac.com", "loader3"], work)
    run([str(ZXCC), "drlink.com", "loader3", "+-[OP]"], work)
    prl = (work / "loader3.prl").read_bytes()
    require(len(prl) >= 256, "LOADER3.PRL header is truncated")
    return prl[256:] + bytes(19 * 128)


def assemble_ccp(work: Path, base: bytes) -> bytes:
    run([str(ZXCC), "mac.com", "ccp3"], work)
    run([str(ZXCC), "mac.com", "ccpdate"], work)
    image = patch_hex(base, (work / "ccp3.hex").read_bytes())
    return patch_hex(image, (work / "ccpdate.hex").read_bytes())


def normalize_crlf(path: Path) -> None:
    text = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    path.write_bytes(text.replace(b"\n", b"\r\n"))


def verify_history_source(path: Path) -> None:
    text = path.read_text(encoding="ascii")
    equates = {
        name: int(value, 16)
        for name, value in re.findall(
            r"^(histmagic0|histmagic1|histlen|histdata)\s+equ\s+0([0-9a-f]+)h$",
            text, re.MULTILINE | re.IGNORECASE,
        )
    }
    require(equates == {
        "histmagic0": HISTORY_START,
        "histmagic1": HISTORY_START + 1,
        "histlen": HISTORY_START + 2,
        "histdata": HISTORY_START + 3,
    }, "history source state map differs")
    require("histmax\t\tequ\t76" in text,
            "history command limit differs")
    require("call\thistory" in text and "histnotrepeat:" in text
            and "histsave:" in text,
            "history source control path is incomplete")


def build(output: Path) -> dict[str, object]:
    require(ZXCC.is_file(), f"build the pinned ZXCC tool first: {ZXCC}")
    require(PATCH.is_file(), f"history patch is absent: {PATCH}")
    upstream = PINNED_CCP.read_bytes()
    require(digest(upstream) == UPSTREAM_SHA256 and len(upstream) == 3200,
            "pinned upstream CCP differs")
    require(HISTORY_END + 1 == ROM_GUARD_START,
            "history state no longer ends below the ROM guard")

    with tempfile.TemporaryDirectory(prefix="cpm3-history-ccp.") as name:
        work = Path(name)
        prepare(work)
        loader = build_loader(work)
        rebuilt = assemble_ccp(work, loader)
        require(rebuilt == upstream,
                "unmodified DRI CCP does not reproduce byte-for-byte")

        source = work / "ccp3.asm"
        source.write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))
        run([
            "patch", "--batch", "--fuzz=0", "-p0", "-i", str(PATCH),
        ], work)
        normalize_crlf(source)
        verify_history_source(source)
        derived = assemble_ccp(work, loader)
        require(len(derived) < 0x0F00,
                "history CCP leaves insufficient space below 1000h")
        require(derived != upstream, "history patch did not change CCP")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(derived)
    manifest = {
        "schema": "cpm-plus-juku-history-ccp-v1",
        "upstream": {
            "name": "Digital Research CP/M 3.1 CCP",
            "bytes": len(upstream),
            "sha256": digest(upstream),
            "license": "third_party/cpm3/LICENSE.md",
        },
        "derived": {
            "name": output.name,
            "bytes": len(derived),
            "sha256": digest(derived),
            "patch": str(PATCH.relative_to(ROOT)),
            "patch_sha256": digest(PATCH.read_bytes()),
            "runtime_end_exclusive": f"{0x100 + len(derived):04X}",
        },
        "history_state": {
            "start": f"{HISTORY_START:04X}",
            "end": f"{HISTORY_END:04X}",
            "bytes": HISTORY_END - HISTORY_START + 1,
            "next_reserved": f"{ROM_GUARD_START:04X}",
        },
    }
    manifest_path = output.with_name("manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "build/cpm3-history/CCP.COM",
    )
    args = parser.parse_args()
    manifest = build(args.output.resolve())
    derived = manifest["derived"]
    print(
        "CPM3-HISTORY-CCP: PASS "
        f"({derived['bytes']} bytes, {derived['sha256']})"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, TypeError, ValueError, zipfile.BadZipFile,
            subprocess.CalledProcessError) as error:
        print(f"cpm3-history-ccp: {error}", file=sys.stderr)
        raise SystemExit(1)
