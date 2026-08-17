#!/usr/bin/env python3
"""Build and report reproducible CP/M Plus distribution volumes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PROFILE_SCHEMA = "cpm-plus-juku-volume-profile-v1"
REPORT_SCHEMA = "cpm-plus-juku-volume-report-v1"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_path(value: object, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty path")
    path = (ROOT / value).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as error:
        raise ValueError(f"{field} escapes the repository: {value}") from error
    if not path.is_file():
        raise ValueError(f"{field} does not exist: {value}")
    return path


def load_profile(path: Path, stack: tuple[Path, ...] = ()) -> dict[str, object]:
    path = path.resolve()
    if path in stack:
        raise ValueError(f"volume profile inheritance cycle at {path}")
    profile = json.loads(path.read_text())
    if not isinstance(profile, dict) or profile.get("schema") != PROFILE_SCHEMA:
        raise ValueError(f"unsupported volume profile schema in {path}")
    parent_name = profile.get("extends")
    if parent_name is not None:
        if not isinstance(parent_name, str) or not parent_name:
            raise ValueError("volume profile extends must be a path")
        parent_path = (path.parent / parent_name).resolve()
        profiles_root = (ROOT / "volume/profiles").resolve()
        try:
            parent_path.relative_to(profiles_root)
        except ValueError as error:
            raise ValueError(
                f"volume profile parent escapes {profiles_root}: {parent_name}"
            ) from error
        parent = load_profile(parent_path, (*stack, path))
        child_files = profile.get("files", [])
        if not isinstance(child_files, list):
            raise ValueError("volume profile child files must be a list")
        merged = dict(parent)
        merged.update({
            key: value for key, value in profile.items()
            if key not in ("extends", "files")
        })
        merged_files = [dict(item) for item in parent["files"]]
        for child in child_files:
            if not isinstance(child, dict):
                raise ValueError("volume profile child file is not an object")
            replacement = child.get("override", False)
            if not isinstance(replacement, bool):
                raise ValueError("volume file override must be boolean")
            clean_child = {
                key: value for key, value in child.items()
                if key != "override"
            }
            if replacement:
                destination = clean_child.get("destination")
                matches = [
                    index for index, item in enumerate(merged_files)
                    if item.get("destination") == destination
                ]
                if len(matches) != 1:
                    raise ValueError(
                        "volume override must replace exactly one inherited "
                        f"destination: {destination!r}"
                    )
                merged_files[matches[0]] = clean_child
            else:
                merged_files.append(clean_child)
        merged["files"] = merged_files
        profile = merged
    for key in ("name", "description", "geometry"):
        if not isinstance(profile.get(key), str) or not profile[key]:
            raise ValueError(f"volume profile {key} is missing")
    if not isinstance(profile.get("image_bytes"), int) or \
            profile["image_bytes"] <= 0:
        raise ValueError("volume profile image_bytes is invalid")
    if not isinstance(profile.get("allocation_block_bytes"), int) or \
            profile["allocation_block_bytes"] <= 0:
        raise ValueError("volume profile allocation_block_bytes is invalid")
    if profile.get("output_layout", "logical") not in (
            "logical", "juku-cylinder-head"):
        raise ValueError("volume profile output_layout is invalid")
    files = profile.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("volume profile files must be a non-empty list")
    names: set[str] = set()
    for index, record in enumerate(files):
        if not isinstance(record, dict):
            raise ValueError(f"volume file {index} is not an object")
        checked_path(record.get("source"), f"files[{index}].source")
        destination = record.get("destination")
        if not isinstance(destination, str) or not re.fullmatch(
                r"[0-9]+:[A-Z0-9$#@!%&'()\-^_{}~]{1,8}"
                r"(?:\.[A-Z0-9$#@!%&'()\-^_{}~]{1,3})?", destination):
            raise ValueError(f"invalid CP/M destination: {destination!r}")
        if destination in names:
            raise ValueError(f"duplicate CP/M destination: {destination}")
        names.add(destination)
        if record.get("mode", "binary") not in ("binary", "text"):
            raise ValueError(f"invalid mode for {destination}")
        provenance = record.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError(f"provenance is missing for {destination}")
        for key in ("source", "version", "license"):
            if not isinstance(provenance.get(key), str) or not provenance[key]:
                raise ValueError(f"{destination} provenance lacks {key}")
    return profile


def text_bytes(path: Path) -> bytes:
    text = path.read_text().replace("\r\n", "\n").replace("\r", "\n")
    return text.replace("\n", "\r\n").encode("ascii") + b"\x1a"


def source_bytes(record: dict[str, object]) -> tuple[Path, bytes]:
    source = checked_path(record["source"], "file source")
    data = text_bytes(source) if record.get("mode", "binary") == "text" \
        else source.read_bytes()
    expected = record.get("sha256")
    if expected is not None and expected != digest(data):
        raise ValueError(
            f"profile checksum differs for {record['destination']}: {expected}"
        )
    return source, data


def inspect_volume(path: Path, geometry: str,
                   environment: dict[str, str]) -> tuple[str, int, int]:
    result = subprocess.run(
        ["cpmls", "-f", geometry, "-D", str(path)], cwd=ROOT,
        env=environment, check=True, text=True, capture_output=True,
    )
    listing = result.stdout
    match = re.search(
        r"Files occupying\s+([0-9]+)K,\s+([0-9]+)K Free\.", listing
    )
    if match is None:
        raise RuntimeError("cannot parse cpmtools free-space report")
    return listing, int(match.group(1)) * 1024, int(match.group(2)) * 1024


def logical_to_juku_image(volume: bytes) -> bytes:
    """Convert 160 side-then-track records to native cylinder/head order."""
    track_bytes = 40 * 128
    tracks_per_side = 80
    if len(volume) != 2 * tracks_per_side * track_bytes:
        raise ValueError("native Juku conversion requires exactly 819200 bytes")
    image = bytearray(len(volume))
    for cylinder in range(tracks_per_side):
        for side in range(2):
            source = (side * tracks_per_side + cylinder) * track_bytes
            target = (cylinder * 2 + side) * track_bytes
            image[target:target + track_bytes] = volume[
                source:source + track_bytes
            ]
    return bytes(image)


def build(output: Path, profile_path: Path,
          report_path: Path | None) -> dict[str, object]:
    profile = load_profile(profile_path)
    geometry = str(profile["geometry"])
    image_bytes = int(profile["image_bytes"])
    environment = {**os.environ, "DISKDEFS": str(ROOT / "diskdefs")}
    prepared: list[tuple[dict[str, object], Path, bytes]] = []
    for untyped in profile["files"]:
        if not isinstance(untyped, dict):
            raise AssertionError("validated profile file changed type")
        source, data = source_bytes(untyped)
        prepared.append((untyped, source, data))

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
            prefix="cpm-plus-juku-volume.", dir=output.parent) as name:
        temporary = Path(name) / output.name
        subprocess.run(["truncate", "-s", "0", str(temporary)], check=True)
        subprocess.run(
            ["mkfs.cpm", "-f", geometry, str(temporary)],
            cwd=ROOT, env=environment, check=True,
        )
        subprocess.run(
            ["truncate", "-s", str(image_bytes), str(temporary)], check=True,
        )
        staging = Path(name) / "files"
        staging.mkdir()
        for index, (record, _source, data) in enumerate(prepared):
            copy = staging / f"{index:03d}.bin"
            copy.write_bytes(data)
            subprocess.run(
                ["cpmcp", "-f", geometry, str(temporary), str(copy),
                 str(record["destination"])],
                cwd=ROOT, env=environment, check=True,
            )
        if temporary.stat().st_size != image_bytes:
            raise RuntimeError(
                f"unexpected {profile['name']} volume size: "
                f"{temporary.stat().st_size}"
            )
        listing, allocated_bytes, free_bytes = inspect_volume(
            temporary, geometry, environment
        )
        logical_data = temporary.read_bytes()
        output_layout = str(profile.get("output_layout", "logical"))
        image_data = logical_to_juku_image(logical_data) \
            if output_layout == "juku-cylinder-head" else logical_data
        try:
            display_profile_path = str(profile_path.resolve().relative_to(ROOT))
        except ValueError:
            display_profile_path = "generated legacy profile"
        allocation_block_bytes = int(profile.get("allocation_block_bytes", 2048))
        report: dict[str, object] = {
            "schema": REPORT_SCHEMA,
            "profile": profile["name"],
            "description": profile["description"],
            "profile_path": display_profile_path,
            "geometry": geometry,
            "output_layout": output_layout,
            "image_bytes": len(image_data),
            "image_sha256": digest(image_data),
            "allocated_bytes": allocated_bytes,
            "free_bytes": free_bytes,
            "files": [
                {
                    "destination": record["destination"],
                    "source": str(source.relative_to(ROOT)),
                    "mode": record.get("mode", "binary"),
                    "source_bytes": source.stat().st_size,
                    "source_sha256": digest(source.read_bytes()),
                    "volume_bytes": len(data),
                    "sha256": digest(data),
                    "allocated_bytes": math.ceil(
                        len(data) / allocation_block_bytes
                    ) * allocation_block_bytes,
                    "provenance": record["provenance"],
                }
                for record, source, data in prepared
            ],
            "cpmtools_listing": listing.rstrip().splitlines(),
        }
        artifact = Path(name) / "artifact.bin"
        artifact.write_bytes(image_data)
        artifact.replace(output)

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"wrote {output} ({report['image_bytes']} bytes, "
        f"sha256 {report['image_sha256']}, {free_bytes // 1024}K free)"
    )
    return report


def legacy_profile(arguments: list[str], directory: Path) -> Path:
    if len(arguments) != 5:
        raise ValueError(
            "legacy usage: OUTPUT CCP.COM DIAG.COM WBOOT.COM README"
        )
    _output, ccp, diag, wboot, readme = map(Path, arguments)
    records = []
    for source, destination, mode, version in (
        (ccp, "0:CCP.COM", "binary", "Digital Research CP/M 3 CCP"),
        (diag, "0:DIAG.COM", "binary", "cpm-plus-juku build"),
        (wboot, "0:WBOOT.COM", "binary", "cpm-plus-juku build"),
        (readme, "0:README.TXT", "text", "cpm-plus-juku build"),
    ):
        records.append({
            "source": str(source.resolve().relative_to(ROOT)),
            "destination": destination,
            "mode": mode,
            "provenance": {
                "source": "legacy build invocation",
                "version": version,
                "license": "see NOTICE.md",
            },
        })
    profile = {
        "schema": PROFILE_SCHEMA,
        "name": "legacy-recovery",
        "description": "Backward-compatible recovery volume invocation",
        "geometry": "juku386",
        "image_bytes": 409600,
        "allocation_block_bytes": 2048,
        "files": records,
    }
    path = directory / "legacy-profile.json"
    path.write_text(json.dumps(profile, indent=2) + "\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy", nargs="*")
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    if args.profile is not None:
        if args.legacy or args.output is None:
            parser.error("--profile requires --output and no legacy operands")
        build(args.output, args.profile, args.report)
        return 0
    if args.output is not None or args.report is not None:
        parser.error("--output/--report require --profile")
    with tempfile.TemporaryDirectory(prefix="cpm-plus-juku-legacy.") as name:
        profile = legacy_profile(args.legacy, Path(name))
        build(Path(args.legacy[0]), profile, None)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (json.JSONDecodeError, OSError, subprocess.CalledProcessError,
            TypeError, ValueError) as error:
        print(f"build-volume: {error}")
        raise SystemExit(1)
