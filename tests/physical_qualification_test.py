#!/usr/bin/env python3
"""Prove the C1 physical recorder rejects gaps and accepts complete evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/physical_qualification.py"
CANDIDATE = ROOT / "out/network-first-abi1-cs00015-c1"
D15 = "1eaf3410849aa967b38f5b74c3db48c1f0ab5684f888998ee6575fd98c1a8534"
D16 = "f15b1b029edd845e0aa7622d61e9b84740957dce1f38a75867cedccef54494ac"
TESTS = (
    "automatic_no_keypress", "post_no_failure_indication", "prompt",
    "warm_boot", "dir", "sequential_read", "diag", "erase_write",
    "keyboard", "compact_display", "cursor_blink", "host_loss_recovery",
    "server_reconnect_without_reset",
)


def invoke(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *arguments], cwd=ROOT, check=check,
        text=True, capture_output=True,
    )


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def captured_run(path: Path, *, kind: str, boot: dict[str, object] | None,
                 volume: Path) -> None:
    log = path / "host.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("disk request op=14 seq=01 drive=0 track=2 sector=1 status=0\n")
    if boot is not None:
        write_json(path / "boot.json", boot)
    write_json(
        path / "run.json",
        {
            "schema": "juku-network-first-physical-host-run-v1",
            "kind": kind,
            "returncode": 130,
            "host_log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
            "volume": str(volume),
            "volume_sha256_before":
                hashlib.sha256(volume.read_bytes()).hexdigest(),
            "volume_sha256_after": hashlib.sha256(volume.read_bytes()).hexdigest(),
            "boot_result": boot,
        },
    )


def main() -> int:
    if not CANDIDATE.is_dir():
        raise AssertionError("bench package must be generated before recorder test")
    manifest = json.loads((CANDIDATE / "manifest.json").read_text())
    with tempfile.TemporaryDirectory(prefix="c1-physical-recorder.") as name:
        session = Path(name) / "session"
        invoke(
            "init", "--candidate", str(CANDIDATE),
            "--output", str(session),
        )
        incomplete = invoke("audit", str(session), check=False)
        if incomplete.returncode != 1 or \
                "only 0 complete cold-boot timings" not in incomplete.stdout:
            raise AssertionError("incomplete evidence was not rejected")
        for index, elapsed in enumerate((4.25, 4.31, 4.28), 1):
            run_directory = session / f"boot-{index:02d}"
            run_directory.mkdir()
            volume = run_directory / "working-network-disk.img"
            shutil.copyfile(CANDIDATE / "network-disk.img", volume)
            boot = {
                "schema": "juku-janet-boot-result-v1",
                "network_rom": True,
                "effective_boot_baud": 19200,
                "disk_baud": 19200,
                "system_sha256":
                    manifest["files"]["cpm-plus-system.bin"]["sha256"],
                "fast_stage_sha256":
                    manifest["files"]["fastboot-v15.bin"]["sha256"],
                "first_disk_request": {"elapsed_seconds": elapsed},
            }
            captured_run(
                run_directory, kind="cold boot", boot=boot, volume=volume,
            )
        captured_run(
            session / "resume-01", kind="resume", boot=None, volume=volume,
        )
        record = [
            "record", str(session), "--d15-sha256", D15,
            "--d16-sha256", D16,
        ]
        for test in TESTS:
            record.extend(("--test", f"{test}=pass"))
        invoke(*record)
        passed = invoke("audit", str(session))
        if "PHYSICAL-QUALIFICATION-AUDIT: PASS" not in passed.stdout:
            raise AssertionError("complete physical evidence did not pass")
        result = json.loads((session / "session.json").read_text())
        if result.get("status") != \
                "physical qualification passed; acceptance audit pending" or \
                result.get("cold_boot_timings_seconds") != [4.25, 4.31, 4.28]:
            raise AssertionError("qualification summary differs")
        with (session / "boot-01" / "host.log").open("a") as log:
            log.write("tampered\n")
        tampered = invoke("audit", str(session), check=False)
        if tampered.returncode != 1 or \
                "invalid or incomplete cold-boot capture" not in tampered.stdout:
            raise AssertionError("changed captured evidence was not rejected")
        result = json.loads((session / "session.json").read_text())
        if result.get("status") != "physical qualification incomplete":
            raise AssertionError("failed re-audit retained a passing status")
    print("PHYSICAL-QUALIFICATION-RECORDER-TEST: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
