#!/usr/bin/env python3
"""Boot non-banked CP/M Plus through Ekta4402 and exercise NetDisk."""

from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import tempfile
import threading
import time
import tty

ROOT = Path(__file__).resolve().parents[1]
COSIM = Path(os.environ.get("JUKU_COSIM_ROOT", ROOT.parent / "8080-cosim"))
ROM_DIRECT = COSIM / "spinoffs" / "jukuravi" / "remix" / "ekta4402.bin"
ROM_STOCK = COSIM / "spinoffs" / "jukuravi" / "remix" / "ekta4401.bin"
ROM_NETWORK = Path(os.environ.get(
    "CPM_PLUS_JUKU_NETWORK_ROM",
    COSIM / "spinoffs" / "jukuravi" / "network-rom" /
    "juku-network-rom-abi1.bin",
)).resolve()
SYSTEM = ROOT / "out" / "cpm-plus-juku-system.bin"
FASTBOOT = ROOT / "out" / "cpm-plus-juku-fastboot-v15.bin"
ROM_SYSTEM = Path(os.environ.get(
    "CPM_PLUS_JUKU_ROM_SYSTEM",
    ROOT / "out" / "cpm-plus-juku-network-rom-system.bin",
))
ROM_FASTBOOT = Path(os.environ.get(
    "CPM_PLUS_JUKU_ROM_FASTBOOT",
    ROOT / "out" / "cpm-plus-juku-network-rom-fastboot-v15.bin",
))
VOLUME = Path(os.environ.get(
    "CPM_PLUS_JUKU_VOLUME", ROOT / "out" / "cpm-plus-juku.img"
))
DRIVE_B = Path(os.environ["CPM_PLUS_JUKU_DRIVE_B"]) \
    if "CPM_PLUS_JUKU_DRIVE_B" in os.environ else None
ZMAC = ROOT / "build" / "bin" / "zmac"
LD80 = ROOT / "build" / "bin" / "ld80"
ZX0 = ROOT / "build" / "bin" / "zx0"
sys.path.insert(0, str(COSIM / "tools"))
sys.path.insert(0, str(ROOT / "third_party" / "juku-common" / "tools"))

from janet_disk_server import juku_image_to_volume, serve_disk  # noqa: E402
from janet_fastboot import serve_fast  # noqa: E402
from creep_console_oracle import (  # noqa: E402
    main as check_console_font,
    render_transcript as render_console_transcript,
)

ram_console_reference: bytes | None = None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def build_trace(output: Path) -> None:
    sources = [
        COSIM / "cosim" / name
        for name in ("trace.c", "i8080.c", "juk_disk.c", "juku_fdc.c")
    ]
    require(
        ROM_DIRECT.is_file()
        and ROM_STOCK.is_file()
        and ROM_NETWORK.is_file()
        and all(path.is_file() for path in sources),
        f"8080-cosim checkout is incomplete at {COSIM}",
    )
    subprocess.run(
        [os.environ.get("CC", "cc"), "-O2", "-Wall", "-Wextra",
         "-o", str(output), *(str(path) for path in sources)],
        check=True,
    )


def build_timing_fixture(
        work: Path, name: str, *, adapter_define: str | None = None,
        netdisk_define: str | None = None) -> tuple[Path, Path]:
    """Build an actual pre-fix code path, rather than injecting an error."""
    fixture = work / name
    fixture.mkdir()
    platform = ROOT / "build" / "platform-adapter.rel"
    netdisk = ROOT / "build" / "netdisk-v3.rel"
    adapter_all = fixture / "adapter.all"
    adapter = fixture / "adapter.bin"
    system = fixture / "system.bin"
    fastboot = fixture / "fastboot.bin"
    required = (
        ZMAC, LD80, ZX0, ROOT / "build" / "platform-adapter.rel",
        ROOT / "build" / "netdisk-v3.rel",
        ROOT / "build" / "ram-keyboard.rel",
        ROOT / "build" / "netconsole.rel",
        ROOT / "build" / "fastboot-core.cim",
        ROOT / "build" / "fastboot-extension.cim",
    )
    require(all(path.is_file() for path in required),
            "legacy timing regression requires a completed make all")
    if adapter_define:
        platform = fixture / "platform-adapter.rel"
        subprocess.run([
            str(ZMAC), "--nmnv", "--zmac", "-m", "--rel7", "-8",
            f"-D{adapter_define}",
            f"-I{ROOT / 'third_party' / 'juku-common' / 'platform'}",
            "-o", str(platform), str(ROOT / "src" / "platform-adapter.asm"),
        ], cwd=ROOT, check=True)
    if netdisk_define:
        netdisk = fixture / "netdisk-v3.rel"
        subprocess.run([
            str(ZMAC), "--nmnv", "--zmac", "-m", "--rel7", "-8",
            "-DCPM3ADAPTER", f"-D{netdisk_define}", "-o", str(netdisk),
            str(ROOT / "third_party" / "juku-common" / "platform" /
                "netdisk-v3.asm"),
        ], cwd=ROOT, check=True)
    subprocess.run([
        str(LD80), "-m", "-O", "bin", "-o", str(adapter_all),
        "-s", "/dev/null", "-P0xa000",
        str(platform), "-P0xaa90",
        str(ROOT / "build" / "ram-keyboard.rel"), "-P0xac10",
        str(netdisk), "-P0xae40", str(ROOT / "build" / "netconsole.rel"),
    ], cwd=ROOT, check=True)
    adapter.write_bytes(adapter_all.read_bytes()[40960:])
    subprocess.run([
        sys.executable, str(ROOT / "tools" / "mksystem3.py"), str(adapter),
        str(ROOT / "third_party" / "cpm3" / "cpm3.sys"), str(system),
    ], cwd=ROOT, check=True)
    subprocess.run([
        sys.executable, str(ROOT / "tools" / "build_fastboot.py"),
        str(ROOT / "build" / "fastboot-core.cim"),
        str(ROOT / "build" / "fastboot-extension.cim"), str(system),
        str(ZX0), str(fastboot),
    ], cwd=ROOT, check=True)
    return fastboot, system


def read_console_until(
        fd: int, marker: bytes, timeout: float, *,
        allow_timeout: bool = False) -> bytes:
    result = bytearray()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], 0.1)
        if not ready:
            continue
        try:
            incoming = os.read(fd, 4096)
        except OSError:
            continue
        result.extend(incoming)
        if marker in result:
            return bytes(result)
    if allow_timeout:
        return bytes(result)
    raise TimeoutError(
        f"console did not emit {marker!r}; transcript={bytes(result)!r}"
    )


def read_console_paged(fd: int, timeout: float) -> bytes:
    """Read through CP/M TYPE pagination until the next CCP prompt."""
    result = bytearray()
    handled = 0
    page_prompt = b"Press RETURN to Continue"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], 0.1)
        if not ready:
            continue
        try:
            result.extend(os.read(fd, 4096))
        except OSError:
            continue
        if b"A>" in result:
            return bytes(result)
        if page_prompt in result[handled:]:
            os.write(fd, b"\r")
            handled = len(result)
    raise TimeoutError(
        f"paged console output did not return to CCP: {bytes(result)!r}"
    )


class RemoteConsole:
    """Thread-shared N4 console buffers used by the real serial protocol."""

    def __init__(self) -> None:
        self.input = bytearray()
        self.output = bytearray()
        self.cursor = 0

    def send(self, data: bytes) -> None:
        self.input.extend(data)

    def read_until(self, marker: bytes, timeout: float) -> bytes:
        start = self.cursor
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            snapshot = bytes(self.output[start:])
            found = snapshot.find(marker)
            if found >= 0:
                end = start + found + len(marker)
                self.cursor = end
                return bytes(self.output[start:end])
            time.sleep(0.01)
        raise TimeoutError(
            f"N4 console did not emit {marker!r}; "
            f"transcript={bytes(self.output[start:])!r}"
        )

    def read_paged(self, timeout: float) -> bytes:
        start = self.cursor
        handled = 0
        page_prompt = b"Press RETURN to Continue"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            snapshot = bytes(self.output[start:])
            found = snapshot.find(b"A>")
            if found >= 0:
                end = start + found + 2
                self.cursor = end
                return bytes(self.output[start:end])
            if page_prompt in snapshot[handled:]:
                self.send(b"\r")
                handled = len(snapshot)
            time.sleep(0.01)
        raise TimeoutError(
            "paged N4 console output did not return to CCP: "
            f"{bytes(self.output[start:])!r}"
        )


def run(trace: Path, work: Path, *, direct_core: bool,
        fastboot: Path = FASTBOOT, system: Path = SYSTEM,
        expect_disk_failure: str | None = None,
        network_rom: bool = False, disk_fault: str | None = None,
        video_mode: int = 3, remote_console: bool = False,
        drive_b: Path | None = DRIVE_B) -> None:
    require(not network_rom or direct_core,
            "network ROM requires direct-core fastboot")
    require(video_mode in range(4), "video mode must be 0..3")
    require(
        not remote_console or (
            direct_core and not expect_disk_failure and disk_fault is None
        ),
        "N4 console regression requires a clean direct-core path",
    )
    if network_rom:
        fastboot = ROM_FASTBOOT
        system = ROM_SYSTEM
    container = system.read_bytes()
    load_address = 0x9000 if network_rom else 0x7000
    entry_address = 0xBC00 if network_rom else 0x9C00
    adapter_address = 0xC000 if network_rom else 0xA000
    container_size = 0x4600 if network_rom else 0x4000
    require(
        container[:8] == b"JUKURM1\x1a"
        and int.from_bytes(container[8:10], "little") == load_address
        and int.from_bytes(container[10:12], "little") == entry_address
        and int.from_bytes(container[12:14], "little") == container_size,
        "CP/M Plus RAM container has an unexpected layout",
    )
    resident = container[512:]
    conout_vector = adapter_address - load_address + 0x000C
    require(resident[conout_vector] == 0xC3,
            "CP/M Plus adapter CONOUT vector is not a JMP")
    conout_pc = int.from_bytes(
        resident[conout_vector + 1:conout_vector + 3], "little",
    )

    if network_rom:
        case_name = "cpm3-network-rom"
        rom = ROM_NETWORK
        boot_label = "automatic network ROM"
    elif direct_core:
        case_name = "cpm3-direct"
        rom = ROM_DIRECT
        boot_label = "direct Ekta4402 N"
    else:
        case_name = "cpm3-stock"
        rom = ROM_STOCK
        boot_label = "stock Ekta4401 TN"
    if expect_disk_failure:
        case_name += f"-{expect_disk_failure}"
    if disk_fault:
        case_name += f"-{disk_fault}"
    if video_mode != 3:
        case_name += f"-video{video_mode}"
    if remote_console:
        case_name += "-remote-console"
    expected_profile = os.environ.get("CPM_PLUS_JUKU_EXPECT_PROFILE")
    if expected_profile:
        case_name += "-profile"
    if drive_b is not None:
        case_name += "-drive-b"
    case = work / case_name
    case.mkdir()
    master, slave = pty.openpty()
    tty.setraw(slave)
    console_master, console_slave = pty.openpty()
    tty.setraw(console_slave)
    environment = os.environ.copy()
    s21_raw = (video_mode << 1) | int(
        os.environ.get("CPM_PLUS_JUKU_S21_EXTRA", "0"), 0,
    )
    environment.update(
        JUKU_USART_PTY=os.ttyname(slave),
        JUKU_CONSOLE_PTY=os.ttyname(console_slave),
        JUKU_CONSOLE_OUT_PC=f"0x{conout_pc:04X}",
        JUKU_CONSOLE_OUT_REGISTER="C",
        JUKU_USART_TRANSFER_CYCLES="64",
        JUKU_USART_BYTE_CYCLES="2300",
        JUKU_USART_PIT_CLOCK="1",
        JUKU_USART_PIT_CPU_HZ=os.environ.get(
            "CPM_PLUS_JUKU_CPU_HZ", "1700000",
        ),
        JUKU_REALTIME_HZ=os.environ.get(
            "CPM_PLUS_JUKU_REALTIME_HZ",
            os.environ.get("CPM_PLUS_JUKU_CPU_HZ", "1700000"),
        ),
        JUKU_TRACE_BANK="1",
        JUKU_DISABLE_SETTLE="1",
        JUKU_KEY_HOLD_FRAMES="6",
        JUKU_KEY_GAP_FRAMES="8",
        JUKU_S21_CONFIG=f"0x{s21_raw:02X}",
        JUKU_CHECKPOINT_PREFIX=str(case / "final"),
    )
    if network_rom:
        environment.pop("JUKU_KEYS", None)
    else:
        environment["JUKU_KEYS"] = "N" if direct_core else "TN"
    volume = bytearray(VOLUME.read_bytes())
    drive_b_volume = juku_image_to_volume(drive_b.read_bytes()) \
        if drive_b is not None else None
    stats: dict[str, int] = {}
    status_reports: list[dict[str, int]] = []
    diag_reports: list[dict[str, int]] = []
    command_metrics: dict[str, dict[str, int | float]] = {}
    fault_evidence: dict[str, int] = {}
    restart_armed = threading.Event()
    errors: list[BaseException] = []
    remote = RemoteConsole()
    with (case / "stdout.txt").open("w") as stdout, \
            (case / "stderr.txt").open("w") as stderr:
        process = subprocess.Popen(
            [str(trace), str(rom),
             "1000000000000", "0", "100000"],
            cwd=case, env=environment, stdout=stdout, stderr=stderr,
        )
        os.close(slave)
        os.close(console_slave)
        try:
            print(f"COSIM {case.name}: bootstrap", flush=True)
            boot_started_at = time.monotonic()
            boot = serve_fast(
                master, fastboot.read_bytes(), container,
                stock_timeout=120, reply_timeout=8, verbose=False,
                configure_rate=False, direct_core=direct_core,
                auto_rom_ready=network_rom,
            )

            def disk_worker() -> None:
                class RestartDiskServer(Exception):
                    pass

                try:
                    def filter_reply(attempt: int, reply: bytes) -> bytes:
                        if disk_fault != "compound-recovery":
                            return reply
                        if attempt == 1:
                            return reply[:max(1, len(reply) // 2)]
                        if attempt == 3:
                            return reply + reply
                        if attempt == 5:
                            fault_evidence["corrupt_replies"] = 1
                            return reply[:-1] + bytes((reply[-1] ^ 1,))
                        return reply

                    def serve(
                        stats_target: dict[str, int],
                        reply_filter: Callable[[int, bytes], bytes] | None,
                        *, resume: bool,
                    ) -> None:
                        serve_disk(
                            master, volume, drive_b=drive_b_volume,
                            timeout=180, idle_timeout=None,
                            writable=True,
                            verbose=os.environ.get(
                                "CPM_PLUS_JUKU_SERVER_VERBOSE", "0",
                            ) == "1",
                            stats=stats_target,
                            protocol_version=3,
                            reply_guard=(
                                0.05 if disk_fault == "compound-recovery"
                                else 0.002
                            ),
                            reply_filter=reply_filter,
                            read_ahead_records=int(os.environ.get(
                                "CPM_PLUS_JUKU_READ_AHEAD_RECORDS", "3",
                            )),
                            tx_byte_delay=float(os.environ.get(
                                "CPM_PLUS_JUKU_TX_BYTE_DELAY", "0",
                            )),
                            v3_wire_drain=(
                                expect_disk_failure != "legacy-host-guard"
                            ),
                            resume=resume or network_rom,
                            console_protocol=remote_console,
                            console_input=remote.input,
                            console_output=remote.output,
                            status_report_hook=status_reports.append,
                            diag_report_hook=diag_reports.append,
                        )

                    if disk_fault in ("server-restart", "mid-session-restart"):
                        def stop_server(_attempt: int, _reply: bytes) -> bytes:
                            if disk_fault == "mid-session-restart" and \
                                    not restart_armed.is_set():
                                return _reply
                            raise RestartDiskServer

                        try:
                            serve(stats, stop_server, resume=False)
                        except RestartDiskServer:
                            fault_evidence["server_restarts"] = 1
                        serve(stats, None, resume=True)
                    else:
                        serve(stats, filter_reply, resume=False)
                except BaseException as error:
                    errors.append(error)

            worker = threading.Thread(target=disk_worker)
            worker.start()
            if expect_disk_failure:
                first = read_console_until(
                    console_master, b"Disk I/O",
                    float(os.environ.get(
                        "CPM_PLUS_JUKU_FAILURE_TIMEOUT",
                        "15" if expect_disk_failure ==
                        "legacy-unmasked-pic" else "120",
                    )),
                    allow_timeout=(
                        expect_disk_failure == "legacy-unmasked-pic"
                    ),
                )
                second = third = b""
            else:
                prompt_timeout = float(os.environ.get(
                    "CPM_PLUS_JUKU_PROMPT_TIMEOUT", "120",
                ))
                first = remote.read_until(b"A>", prompt_timeout) \
                    if remote_console else read_console_until(
                        console_master, b"A>", prompt_timeout,
                    )
                print(f"COSIM {case.name}: prompt", flush=True)
                command_metrics["boot"] = {
                    "read_requests": stats.get("reads", 0),
                    "read_records": stats.get("read_records", 0),
                    "request_wire_bytes": stats.get("request_wire_bytes", 0),
                    "reply_wire_bytes": stats.get("reply_wire_bytes", 0),
                    "elapsed_seconds": round(
                        time.monotonic() - boot_started_at, 3,
                    ),
                }
                if network_rom and remote_console:
                    # Let the emulated target enter its idle CONIN path before
                    # the first N4 key arrives.  Without this bench-faithful
                    # pause, the server thread can enqueue DIR in the few host
                    # microseconds between printing A> and calling CONIN; that
                    # race hid the resident ROM's deliberately blocking local
                    # CONIN service on physical CS00015.
                    time.sleep(float(os.environ.get(
                        "CPM_PLUS_JUKU_REMOTE_IDLE_DELAY", "0.25",
                    )))
                send_console = remote.send if remote_console else \
                    lambda data: os.write(console_master, data)
                read_until = remote.read_until if remote_console else \
                    lambda marker, timeout: read_console_until(
                        console_master, marker, timeout,
                    )
                command_timeout = 600 if network_rom and remote_console \
                    else 120
                profile_startup = first
                if expected_profile:
                    while profile_startup.count(b"A>") < 2:
                        profile_startup += read_until(b"A>", command_timeout)
                    require(
                        expected_profile.encode("ascii") in profile_startup
                        and b"CCP" in profile_startup,
                        "CP/M Plus PROFILE.SUB did not complete its expected "
                        f"command: {profile_startup!r}",
                    )
                if disk_fault == "mid-session-restart":
                    restart_armed.set()
                command_started_at = time.monotonic()
                send_console(b"DIR\r")
                second = read_until(b"A>", command_timeout)
                command_metrics["dir"] = {
                    "read_requests": stats.get("reads", 0)
                    - command_metrics["boot"]["read_requests"],
                    "read_records": stats.get("read_records", 0)
                    - command_metrics["boot"]["read_records"],
                    "request_wire_bytes": stats.get("request_wire_bytes", 0)
                    - command_metrics["boot"]["request_wire_bytes"],
                    "reply_wire_bytes": stats.get("reply_wire_bytes", 0)
                    - command_metrics["boot"]["reply_wire_bytes"],
                    "elapsed_seconds": round(
                        time.monotonic() - command_started_at, 3,
                    ),
                }
                print(f"COSIM {case.name}: DIR", flush=True)
                command_started_at = time.monotonic()
                send_console(b"TYPE README.TXT\r")
                third = remote.read_paged(300 if network_rom else 120) \
                    if remote_console else \
                    read_console_paged(console_master, 120)
                command_metrics["type"] = {
                    "read_requests": stats.get("reads", 0)
                    - command_metrics["boot"]["read_requests"]
                    - command_metrics["dir"]["read_requests"],
                    "read_records": stats.get("read_records", 0)
                    - command_metrics["boot"]["read_records"]
                    - command_metrics["dir"]["read_records"],
                    "request_wire_bytes": stats.get("request_wire_bytes", 0)
                    - command_metrics["boot"]["request_wire_bytes"]
                    - command_metrics["dir"]["request_wire_bytes"],
                    "reply_wire_bytes": stats.get("reply_wire_bytes", 0)
                    - command_metrics["boot"]["reply_wire_bytes"]
                    - command_metrics["dir"]["reply_wire_bytes"],
                    "elapsed_seconds": round(
                        time.monotonic() - command_started_at, 3,
                    ),
                }
                print(f"COSIM {case.name}: TYPE", flush=True)
                send_console(b"DIAG CPU\r")
                fourth = read_until(b"A>", command_timeout)
                print(f"COSIM {case.name}: DIAG", flush=True)
                extra_command = os.environ.get("CPM_PLUS_JUKU_EXTRA_COMMAND")
                if extra_command:
                    send_console(extra_command.encode("ascii") + b"\r")
                    extra = read_until(b"A>", command_timeout)
                    marker = os.environ.get(
                        "CPM_PLUS_JUKU_EXTRA_MARKER", extra_command,
                    ).encode("ascii")
                    require(marker in extra,
                            f"extra command lacks {marker!r}: {extra!r}")
                    print(
                        f"COSIM {case.name}: {extra_command}", flush=True,
                    )
                extra_command2 = os.environ.get(
                    "CPM_PLUS_JUKU_EXTRA_COMMAND2",
                )
                if extra_command2:
                    send_console(extra_command2.encode("ascii") + b"\r")
                    extra2 = read_until(b"A>", command_timeout)
                    marker2 = os.environ.get(
                        "CPM_PLUS_JUKU_EXTRA_MARKER2", extra_command2,
                    ).encode("ascii")
                    require(marker2 in extra2,
                            f"second extra command lacks {marker2!r}: "
                            f"{extra2!r}")
                    print(
                        f"COSIM {case.name}: {extra_command2}", flush=True,
                    )
                send_console(b"WBOOT\r")
                fifth = read_until(b"A>", command_timeout)
                print(f"COSIM {case.name}: WBOOT", flush=True)
                soak_cycles = int(os.environ.get(
                    "CPM_PLUS_JUKU_SOAK_CYCLES", "0",
                )) if disk_fault == "mid-session-restart" else 0
                for _ in range(soak_cycles):
                    send_console(b"DIR\r")
                    read_until(b"A>", 120)
                    send_console(b"DIAG CPU\r")
                    soak_diag = read_until(b"A>", 120)
                    require(b"CPU: PASS" in soak_diag,
                            "NetDisk soak diagnostic failed")
                fault_evidence["soak_cycles"] = soak_cycles
                send_console(b"ERA README.TXT\r")
                sixth = read_until(b"A>", command_timeout)
                print(f"COSIM {case.name}: ERA", flush=True)
                if drive_b is not None:
                    before = {
                        key: stats.get(key, 0) for key in (
                            "reads", "read_records", "request_wire_bytes",
                            "reply_wire_bytes",
                        )
                    }
                    command_started_at = time.monotonic()
                    send_console(b"B:\r")
                    selected_b = read_until(b"B>", command_timeout)
                    command_metrics["b_login"] = {
                        "read_requests": stats.get("reads", 0)
                        - before["reads"],
                        "read_records": stats.get("read_records", 0)
                        - before["read_records"],
                        "request_wire_bytes": stats.get(
                            "request_wire_bytes", 0,
                        ) - before["request_wire_bytes"],
                        "reply_wire_bytes": stats.get("reply_wire_bytes", 0)
                        - before["reply_wire_bytes"],
                        "elapsed_seconds": round(
                            time.monotonic() - command_started_at, 3,
                        ),
                    }
                    before_reads = stats.get("reads", 0)
                    before_records = stats.get("read_records", 0)
                    command_started_at = time.monotonic()
                    send_console(b"DIR\r")
                    listed_b = read_until(b"B>", command_timeout)
                    command_metrics["b_dir"] = {
                        "read_requests": stats.get("reads", 0) - before_reads,
                        "read_records": stats.get("read_records", 0)
                        - before_records,
                        "elapsed_seconds": round(
                            time.monotonic() - command_started_at, 3,
                        ),
                    }
                    send_console(b"DIAG CPU\r")
                    diagnosed_b = read_until(b"B>", command_timeout)
                    send_console(b"A:\r")
                    selected_a = read_until(b"A>", command_timeout)
                    per_drive_cache = os.environ.get(
                        "CPM_PLUS_JUKU_EXPECT_PER_DRIVE_CACHE",
                    ) == "1"
                    if per_drive_cache:
                        send_console(b"DIAG CPU\r")
                        diagnosed_a = read_until(b"A>", command_timeout)
                        require(
                            b"CPU: PASS" in diagnosed_a,
                            "A: diagnostic did not refill its resident cache",
                        )
            time.sleep(0.1)
            process.terminate()
            process.wait(timeout=5)
            os.close(master)
            worker.join(timeout=3)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            try:
                os.close(master)
            except OSError:
                pass
            os.close(console_master)

    if direct_core:
        require(
            boot["direct_core"] == 1
            and boot["stock_sent_frames"] == 0
            and boot["auto_rom_ready"] == int(network_rom)
            and boot["auto_ready_seen"] == int(network_rom),
            f"CP/M Plus did not use the requested direct ROM path: {boot}",
        )
    else:
        require(
            boot["direct_core"] == 0
            and boot["stock_sent_frames"] > 0
            and boot["protocol_version"] == 15,
            f"CP/M Plus did not use stock Janet into V15: {boot}",
        )
    if expect_disk_failure != "legacy-unmasked-pic":
        require(b"CP/M Plus" in first or b"CP/M Version 3" in first,
                f"CP/M Plus banner is missing: {first!r}")
    if expect_disk_failure:
        if expect_disk_failure != "legacy-unmasked-pic":
            require(
                b"Disk I/O" in first,
                f"legacy drain did not reproduce the disk error: {first!r}",
            )
        if expect_disk_failure != "legacy-unmasked-pic":
            require(
                stats.get("retries", 0) >= 2,
                f"legacy drain did not provoke three N3 attempts: {stats}",
            )
    else:
        require(b"DIR" in second and b"CCP" in second,
                f"CP/M Plus network DIR failed: {second!r}")
        require(
            b"TYPE README.TXT" in third
            and b"host-backed NetDisk-v3" in third and b"A>" in third,
            f"CP/M Plus sequential file read failed: {third!r}",
        )
        require(b"DIAG CPU" in fourth and b"CPU: PASS" in fourth,
                f"CP/M Plus transient diagnostic failed: {fourth!r}")
        require(b"WBOOT" in fifth and b"A>" in fifth,
                f"CP/M Plus warm boot did not return to CCP: {fifth!r}")
        require(b"ERA README.TXT" in sixth and b"A>" in sixth,
                f"CP/M Plus erase did not return to CCP: {sixth!r}")
        if drive_b is not None:
            require(
                b"B>" in selected_b and b"DIAG" in listed_b
                and b"README" in listed_b and b"CPU: PASS" in diagnosed_b
                and b"A>" in selected_a,
                "CP/M Plus native B: selection/load/return failed: "
                f"{selected_b!r} {listed_b!r} {diagnosed_b!r} {selected_a!r}",
            )
            require(stats.get("reads_b", 0) > 0,
                    f"CP/M Plus issued no native B: reads: {stats}")
        require(stats.get("reads", 0) >= 1,
                f"CP/M Plus issued no NetDisk reads: {stats}")
        require(stats.get("writes", 0) >= 1,
                f"CP/M Plus issued no NetDisk writes: {stats}")
        for name in ("boot", "dir", "type"):
            expected = os.environ.get(
                f"CPM_PLUS_JUKU_EXPECT_{name.upper()}_READS",
            )
            if expected is not None:
                require(
                    command_metrics[name]["read_requests"] == int(expected),
                    f"{name.upper()} read-request baseline differs: "
                    f"expected={expected} metrics={command_metrics}",
                )
        if remote_console:
            require(
                stats.get("console_polls", 0) > 0
                and stats.get("console_input_bytes", 0) > 0
                and stats.get("console_output_bytes", 0) > 0,
                f"N4 console did not carry bidirectional traffic: {stats}",
            )
        expected_status_reports = int(os.environ.get(
            "CPM_PLUS_JUKU_EXPECT_STATUS_REPORTS", "0",
        ))
        require(
            stats.get("status_reports", 0) == expected_status_reports,
            "target status report count differs: "
            f"expected={expected_status_reports} stats={stats}",
        )
        if expected_status_reports:
            require(
                len(status_reports) == expected_status_reports
                and status_reports[-1]["s21"] == s21_raw
                and status_reports[-1]["video_mode"] == video_mode
                and status_reports[-1]["features"] == 0x0F
                and status_reports[-1]["clock_status"] == 0,
                f"target status tuple differs: {status_reports}",
            )
        expected_diag_reports = int(os.environ.get(
            "CPM_PLUS_JUKU_EXPECT_DIAG_REPORTS", "0",
        ))
        require(
            stats.get("diag_reports", 0) == expected_diag_reports
            and len(diag_reports) == expected_diag_reports,
            "target diagnostic report count differs: "
            f"expected={expected_diag_reports} reports={diag_reports} "
            f"stats={stats}",
        )
        if os.environ.get("CPM_PLUS_JUKU_EXPECT_IO_DIAG") == "1":
            require(
                diag_reports[-1]["suite"] == 2
                and diag_reports[-1]["pass_mask"] == 0x7C
                and diag_reports[-1]["fail_mask"] == 0
                and diag_reports[-1]["flags"] == 0,
                f"target I/O diagnostic tuple differs: {diag_reports[-1]}",
            )
        expected_capability_queries = int(os.environ.get(
            "CPM_PLUS_JUKU_EXPECT_CAPABILITY_QUERIES", "0",
        ))
        require(
            stats.get("capability_queries", 0) ==
            expected_capability_queries,
            "host capability-query count differs: "
            f"expected={expected_capability_queries} stats={stats}",
        )
        if disk_fault == "compound-recovery":
            require(
                stats.get("short_replies") == 1
                and stats.get("extra_reply_bytes", 0) > 0
                and stats.get("retries", 0) >= 1,
                f"NetDisk recovery faults were not exercised: {stats}",
            )
            require(fault_evidence.get("corrupt_replies") == 1,
                    "NetDisk CRC corruption was not exercised")
        elif disk_fault in ("server-restart", "mid-session-restart"):
            require(fault_evidence.get("server_restarts") == 1,
                    "NetDisk server restart was not exercised")
            expected_soak = int(os.environ.get(
                "CPM_PLUS_JUKU_SOAK_CYCLES", "0",
            )) if disk_fault == "mid-session-restart" else 0
            require(fault_evidence.get("soak_cycles", 0) == expected_soak,
                    "NetDisk soak cycle count differs")
        else:
            require(stats.get("retries") == 0,
                    f"fixed NetDisk path required retries: {stats}")
    require(all(isinstance(error, OSError) for error in errors),
            f"CP/M Plus disk server failed: {errors!r}")
    state = dict(
        line.split("=", 1)
        for line in (case / "final.state").read_text().splitlines()
        if "=" in line
    )
    expected_mode = "1" if network_rom else "3"
    # The deliberately unmasked-PIC fixture proves live stale interrupts and
    # ensuing disk/console corruption. Where its random interrupt vector lands
    # is timing-dependent, so a later unintended memory-mode write is valid
    # failure evidence rather than a positive-path invariant. Every corrected
    # and transport-only fixture must retain its requested mode.
    if expect_disk_failure != "legacy-unmasked-pic":
        require(state.get("mode") == expected_mode,
                f"CP/M Plus did not retain memory mode {expected_mode}: {state}")
        require(
            state.get("video_console_mode") == str(video_mode),
            f"CP/M Plus did not select S21 video mode {video_mode}: {state}",
        )
    global ram_console_reference
    ram = (case / "final.ram").read_bytes()
    loader_address = 0x9A00 if network_rom else 0x7A00
    bdos_address = 0x9D00 if network_rom else 0x7D00
    if not expect_disk_failure:
        require(
            int.from_bytes(ram[6:8], "little") == loader_address + 6
            and ram[loader_address + 6] == 0xC3
            and ram[loader_address + 9] == 0xC3
            and int.from_bytes(
                ram[loader_address + 10:loader_address + 12], "little",
            ) == bdos_address + 6,
            "CP/M did not publish its expected TPA loader/BDOS chain",
        )
    screen = ram[0xD800:0xD800 + 9600]
    if not expect_disk_failure and direct_core and not network_rom:
        transcript = (profile_startup if expected_profile else first) \
            + second + third + fourth + fifth + sixth
        if drive_b is not None:
            transcript += selected_b + listed_b + diagnosed_b + selected_a
        expected_screen = render_console_transcript(
            transcript, mode=video_mode,
        )
        expected_screen_hidden = render_console_transcript(
            transcript, mode=video_mode, cursor=False,
        )
        (case / "console.bin").write_bytes(transcript)
        (case / "expected-screen.bin").write_bytes(expected_screen)
        if screen not in (expected_screen, expected_screen_hidden):
            first_difference = next(
                index for index, pair in enumerate(zip(screen, expected_screen))
                if pair[0] != pair[1]
            )
            require(
                False,
                "RAM console differs from independent source-font oracle at "
                f"framebuffer byte {first_difference}: "
                f"{screen[first_difference]:02X} != "
                f"{expected_screen[first_difference]:02X}",
            )
        ram_console_reference = screen
    if network_rom:
        gate = ram[0xD620:0xD700]
        signature = gate.rfind(b"JUKUABI\0")
        require(signature > 0 and gate[signature - 1] == 1,
                "CP/M Plus did not initialize the fixed ROM call gate")
        expected_local_key = 0 if remote_console else 0x0D
        native_record = os.environ.get(
            "CPM_PLUS_JUKU_EXPECT_NATIVE_BOOT_RECORD",
        ) == "1"
        abi_status_address = 0xC651 if native_record else 0xC5F1
        require(
            ram[abi_status_address] == 0 and ram[0xD785] == 1
            and ram[0xD788] == expected_local_key,
            "CP/M Plus did not retain ROM serial/keyboard binding state",
        )
        if native_record:
            require(
                ram[0xC640] == 1 and ram[0xC641] == 0,
                "native cold/warm or reset-POST record differs: "
                f"boot={ram[0xC640]:02X} post={ram[0xC641]:02X}",
            )
        if os.environ.get("CPM_PLUS_JUKU_EXPECT_PER_DRIVE_CACHE") == "1":
            require(
                ram[0xD7DA] > 0 and ram[0xD7DB] > 0
                and ram[0xD7DC:0xD7DE] == bytes((0x80, 0xC7))
                and ram[0xD7DE:0xD7E0] == bytes((0x80, 0xCB)),
                "C5 did not retain independent A:/B: read-ahead state: "
                f"{ram[0xD7DA:0xD7E0].hex()}",
            )
        if ram_console_reference is not None:
            require(
                screen == ram_console_reference,
                "resident and RAM console framebuffers differ after the "
                "same A>/DIR/TYPE/DIAG/warm-boot transcript",
            )
    if expect_disk_failure == "legacy-unmasked-pic":
        require(
            state.get("pic_mask") != "FF"
            and int(state.get("pic_frame_irq_count", "0")) > 0,
            f"legacy PIC fixture did not leave stale IRQs live: {state}",
        )
    else:
        require(state.get("pic_mask") == "FF",
                f"CP/M Plus did not retain a fully masked PIC: {state}")
    require(state.get("usart_mode") == "5E",
            "CP/M Plus adapter did not select NetDisk 8O1 framing")
    overruns = int(state.get("usart_rx_overruns", "-1"))
    resident_overruns = int(state.get("usart_rx_overruns_in_all_ram", "-1"))
    if expect_disk_failure:
        require(overruns > 0,
                f"legacy failure lacked a modeled 8251 overrun: {state}")
        print(
            "JUKU CP/M PLUS 3.1 TIMING: REPRODUCED "
            f"({expect_disk_failure}, Disk I/O, retries={stats['retries']}, "
            f"overruns={overruns})"
        )
        return
    if disk_fault == "compound-recovery":
        require(overruns > 0,
                f"compound recovery did not exercise an 8251 overrun: {state}")
    elif not network_rom:
        require(
            0 <= resident_overruns <= 8,
            "negotiated startup produced more than the bounded capability-"
            "marker "
            f"overruns: {state}",
        )
    else:
        require(resident_overruns == 0,
                f"fixed NetDisk path still overran the resident 8251: {state}")
    if command_metrics:
        (case / "disk-metrics.json").write_text(
            json.dumps(command_metrics, indent=2) + "\n",
        )
    print(
        "JUKU CP/M PLUS 3.1: PASS "
        f"({boot_label} "
        f"boot{', N4 remote console' if remote_console else ''}, A>, DIR, "
        f"TYPE README.TXT, DIAG CPU, warm boot, "
        f"ERA README.TXT, reads={stats['reads']}, "
        f"writes={stats['writes']}, retries={stats['retries']}, "
        f"native-B-reads={stats.get('reads_b', 0)}, "
        f"command-reads={command_metrics}, "
        f"resident-overruns={resident_overruns}, "
        f"bootstrap-overruns={overruns - resident_overruns}"
        f"{', soak-cycles=' + str(fault_evidence.get('soak_cycles', 0)) if fault_evidence.get('soak_cycles', 0) else ''}"
        f"{', recovered-faults=' + disk_fault if disk_fault else ''})"
    )


def main() -> None:
    require(check_console_font() == 0,
            "generated RAM console font differs from its source reference")
    for path in (
        ROM_DIRECT, ROM_STOCK, ROM_NETWORK, SYSTEM, FASTBOOT,
        ROM_SYSTEM, ROM_FASTBOOT, VOLUME,
    ):
        require(path.is_file(), f"build input is missing: {path}")
    if DRIVE_B is not None:
        require(DRIVE_B.is_file(), f"native B: image is missing: {DRIVE_B}")
    selected = os.environ.get("CPM_PLUS_JUKU_BOOT_PATH", "both")
    require(selected in (
        "both", "direct", "stock", "network", "network-smoke",
        "network-compound", "network-remote", "video",
        "remote", "distribution", "all",
    ),
            f"invalid CPM_PLUS_JUKU_BOOT_PATH={selected!r}")
    paths = (True, False) if selected in ("both", "all") else \
        (selected == "direct",) if selected in ("direct", "stock") else ()
    include_network = selected in ("network", "all")
    video_modes = range(4) if selected in ("video", "all") else ()
    retained = os.environ.get("CPM_PLUS_JUKU_WORK")
    if retained:
        work = Path(retained)
        work.mkdir(parents=True, exist_ok=True)
        trace = work / "trace"
        build_trace(trace)
        if selected == "network":
            run(trace, work, direct_core=True, network_rom=True)
            run(trace, work, direct_core=True, network_rom=True,
                disk_fault="compound-recovery")
            run(trace, work, direct_core=True, network_rom=True,
                disk_fault="server-restart")
            run(trace, work, direct_core=True, network_rom=True,
                disk_fault="mid-session-restart")
            return
        if selected in ("network-smoke", "network-compound"):
            run(trace, work, direct_core=True, network_rom=True,
                disk_fault=("compound-recovery"
                            if selected == "network-compound" else None))
            return
        if selected == "video":
            for video_mode in video_modes:
                run(trace, work, direct_core=True, video_mode=video_mode)
            return
        if selected == "remote":
            run(trace, work, direct_core=True, remote_console=True)
            return
        if selected == "network-remote":
            run(trace, work, direct_core=True, network_rom=True,
                remote_console=True)
            return
        if selected == "distribution":
            run(trace, work, direct_core=True)
            return
        legacy_fastboot, legacy_system = build_timing_fixture(
            work, "legacy-target-drain",
            netdisk_define="NETDISK_V3_LEGACY_DRAIN",
        )
        legacy_pic_fastboot, legacy_pic_system = build_timing_fixture(
            work, "legacy-unmasked-pic",
            adapter_define="CPM3_LEGACY_UNMASKED_PIC",
        )
        run(trace, work, direct_core=True, fastboot=legacy_fastboot,
            system=legacy_system,
            expect_disk_failure="legacy-target-drain")
        run(trace, work, direct_core=True,
            expect_disk_failure="legacy-host-guard")
        run(trace, work, direct_core=False, fastboot=legacy_pic_fastboot,
            system=legacy_pic_system,
            expect_disk_failure="legacy-unmasked-pic")
        for direct_core in paths:
            run(trace, work, direct_core=direct_core)
        if include_network:
            run(trace, work, direct_core=True, network_rom=True)
            run(trace, work, direct_core=True, network_rom=True,
                disk_fault="compound-recovery")
            run(trace, work, direct_core=True, network_rom=True,
                disk_fault="server-restart")
            run(trace, work, direct_core=True, network_rom=True,
                disk_fault="mid-session-restart")
        if selected == "all":
            for video_mode in range(3):
                run(trace, work, direct_core=True, video_mode=video_mode)
        return
    with tempfile.TemporaryDirectory(prefix="cpm-plus-juku-cosim.") as name:
        work = Path(name)
        trace = work / "trace"
        build_trace(trace)
        if selected == "network":
            run(trace, work, direct_core=True, network_rom=True)
            run(trace, work, direct_core=True, network_rom=True,
                disk_fault="compound-recovery")
            run(trace, work, direct_core=True, network_rom=True,
                disk_fault="server-restart")
            run(trace, work, direct_core=True, network_rom=True,
                disk_fault="mid-session-restart")
            return
        if selected in ("network-smoke", "network-compound"):
            run(trace, work, direct_core=True, network_rom=True,
                disk_fault=("compound-recovery"
                            if selected == "network-compound" else None))
            return
        if selected == "video":
            for video_mode in video_modes:
                run(trace, work, direct_core=True, video_mode=video_mode)
            return
        if selected == "remote":
            run(trace, work, direct_core=True, remote_console=True)
            return
        if selected == "network-remote":
            run(trace, work, direct_core=True, network_rom=True,
                remote_console=True)
            return
        if selected == "distribution":
            run(trace, work, direct_core=True)
            return
        legacy_fastboot, legacy_system = build_timing_fixture(
            work, "legacy-target-drain",
            netdisk_define="NETDISK_V3_LEGACY_DRAIN",
        )
        legacy_pic_fastboot, legacy_pic_system = build_timing_fixture(
            work, "legacy-unmasked-pic",
            adapter_define="CPM3_LEGACY_UNMASKED_PIC",
        )
        run(trace, work, direct_core=True, fastboot=legacy_fastboot,
            system=legacy_system,
            expect_disk_failure="legacy-target-drain")
        run(trace, work, direct_core=True,
            expect_disk_failure="legacy-host-guard")
        run(trace, work, direct_core=False, fastboot=legacy_pic_fastboot,
            system=legacy_pic_system,
            expect_disk_failure="legacy-unmasked-pic")
        for direct_core in paths:
            run(trace, work, direct_core=direct_core)
        if include_network:
            run(trace, work, direct_core=True, network_rom=True)
            run(trace, work, direct_core=True, network_rom=True,
                disk_fault="compound-recovery")
            run(trace, work, direct_core=True, network_rom=True,
                disk_fault="server-restart")
            run(trace, work, direct_core=True, network_rom=True,
                disk_fault="mid-session-restart")
        if selected == "all":
            for video_mode in range(3):
                run(trace, work, direct_core=True, video_mode=video_mode)


if __name__ == "__main__":
    main()
