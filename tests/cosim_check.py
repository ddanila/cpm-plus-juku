#!/usr/bin/env python3
"""Boot non-banked CP/M Plus through Ekta4402 and exercise NetDisk."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import signal
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tty

ROOT = Path(__file__).resolve().parents[1]
COSIM = Path(os.environ.get("JUKU_COSIM_ROOT", ROOT.parent / "8080-cosim"))
COMMON = Path(os.environ.get(
    "JUKU_COMMON_ROOT", ROOT / "third_party" / "juku-common",
)).resolve()
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
sys.path.insert(0, str(COMMON / "tools"))
sys.path.insert(0, str(ROOT / "tools"))

from janet_disk_server import juku_image_to_volume, serve_disk  # noqa: E402
from janet_fastboot import serve_fast  # noqa: E402
from creep_console_oracle import (  # noqa: E402
    main as check_console_font,
    render_transcript as render_console_transcript,
)
from vidtest_oracle import framebuffer as vidtest_framebuffer  # noqa: E402
from panel_oracle import framebuffer as panel_framebuffer  # noqa: E402

ram_console_reference: bytes | None = None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def artifact_identity(path: Path) -> dict[str, int | str]:
    payload = path.read_bytes()
    return {
        "name": path.name,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def build_trace(output: Path) -> None:
    packaged = os.environ.get("JUKU_COSIM_TRACE")
    if packaged:
        source = Path(packaged)
        require(source.is_file(), f"packaged simulator is missing: {source}")
        shutil.copy2(source, output)
        output.chmod(0o755)
        return
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
    platform = fixture / "platform-adapter.rel"
    keyboard = fixture / "ram-keyboard.rel"
    netdisk = fixture / "netdisk-v3.rel"
    netconsole = fixture / "netconsole.rel"
    adapter_all = fixture / "adapter.all"
    adapter = fixture / "adapter.bin"
    system = fixture / "system.bin"
    fastboot = fixture / "fastboot.bin"
    required = (
        ZMAC, LD80, ZX0,
        ROOT / "build" / "fastboot-core.cim",
        ROOT / "build" / "fastboot-extension.cim",
    )
    require(all(path.is_file() for path in required),
            "legacy timing regression requires a completed make all")

    def assemble(command: list[str], module: str) -> int:
        result = subprocess.run(
            command, cwd=ROOT, check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        matches = re.findall(
            r"^\s*(\d+)\s+bytes\s*$", result.stdout, re.MULTILINE,
        )
        require(len(matches) == 1,
                f"cannot measure legacy fixture module {module}")
        return int(matches[0])

    platform_command = [
        str(ZMAC), "--nmnv", "--zmac", "-m", "--rel7", "-8", "-l",
    ]
    if adapter_define:
        platform_command.append(f"-D{adapter_define}")
    platform_command.extend([
        f"-I{COMMON / 'platform'}", "-o", str(platform),
        str(ROOT / "src" / "platform-adapter.asm"),
    ])
    platform_size = assemble(platform_command, "platform adapter")
    keyboard_size = assemble([
        str(ZMAC), "--nmnv", "--zmac", "-m", "--rel7", "-8", "-l",
        "-o", str(keyboard), str(COMMON / "platform" / "ram-keyboard.asm"),
    ], "keyboard")
    netdisk_command = [
        str(ZMAC), "--nmnv", "--zmac", "-m", "--rel7", "-8", "-l",
        "-DCPM3ADAPTER",
    ]
    if netdisk_define:
        netdisk_command.append(f"-D{netdisk_define}")
    netdisk_command.extend([
        "-o", str(netdisk), str(COMMON / "platform" / "netdisk-v3.asm"),
    ])
    netdisk_size = assemble(netdisk_command, "NetDisk v3")
    netconsole_size = assemble([
        str(ZMAC), "--nmnv", "--zmac", "-m", "--rel7", "-8", "-l",
        "-o", str(netconsole), str(COMMON / "platform" / "netconsole.asm"),
    ], "NetConsole")
    position = 0xA000
    placements: list[str] = []
    for module, size in (
            (platform, platform_size), (keyboard, keyboard_size),
            (netdisk, netdisk_size), (netconsole, netconsole_size)):
        placements.extend((f"-P0x{position:04x}", str(module)))
        position += size
    require(position <= 0xB000,
            f"legacy timing fixture exceeds A000h..AFFFh by "
            f"{position - 0xB000} bytes")
    subprocess.run([
        str(LD80), "-m", "-O", "bin", "-o", str(adapter_all),
        "-s", "/dev/null", *placements,
    ], cwd=ROOT, check=True)
    adapter_payload = adapter_all.read_bytes()[0xA000:]
    require(len(adapter_payload) <= 0x1000,
            "linked legacy timing adapter exceeds A000h..AFFFh")
    adapter.write_bytes(adapter_payload)
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
        video_mode: int = 3, locale: int | None = None,
        remote_console: bool = False,
        drive_b: Path | None = DRIVE_B) -> None:
    if "CPM_PLUS_JUKU_VIDEO_MODE" in os.environ:
        video_mode = int(os.environ["CPM_PLUS_JUKU_VIDEO_MODE"], 0)
    require(not network_rom or direct_core,
            "network ROM requires direct-core fastboot")
    require(video_mode in range(4), "video mode must be 0..3")
    require(locale is None or locale in range(4), "locale must be 0..3")
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
    entry_address = int.from_bytes(container[10:12], "little")
    expected_entries = (0xBC00, 0xBE00) if network_rom else (0x9C00,)
    require(entry_address in expected_entries,
            f"CP/M Plus entry {entry_address:04X}h is unsupported")
    adapter_address = entry_address + 0x0400
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
    if locale is not None:
        case_name += f"-locale{locale}"
    if remote_console:
        case_name += "-remote-console"
    expected_profile = os.environ.get("CPM_PLUS_JUKU_EXPECT_PROFILE")
    expected_profile_output = os.environ.get(
        "CPM_PLUS_JUKU_EXPECT_PROFILE_OUTPUT",
    )
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
    s21_extra = int(os.environ.get("CPM_PLUS_JUKU_S21_EXTRA", "0"), 0)
    if locale is not None:
        s21_extra = (s21_extra & ~0x18) | (locale << 3)
    active_locale = (s21_extra >> 3) & 3
    s21_raw = (video_mode << 1) | s21_extra
    environment.update(
        JUKU_USART_PTY=os.ttyname(slave),
        JUKU_CONSOLE_PTY=os.ttyname(console_slave),
        JUKU_CONSOLE_OUT_PC=f"0x{conout_pc:04X}",
        JUKU_CONSOLE_OUT_REGISTER="C",
        JUKU_USART_TRANSFER_CYCLES=os.environ.get(
            "CPM_PLUS_JUKU_USART_TRANSFER_CYCLES", "64",
        ),
        JUKU_USART_BYTE_CYCLES=os.environ.get(
            "CPM_PLUS_JUKU_USART_BYTE_CYCLES", "2300",
        ),
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
    boot_reports: list[dict[str, int]] = []
    command_metrics: dict[str, dict[str, int | float | str]] = {}
    checkpoint_generation = 0
    last_captured_program_start = 0
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

            def fastboot_filter(
                sequence: int, attempt: int, packet: bytes,
            ) -> bytes:
                if os.environ.get(
                    "CPM_PLUS_JUKU_CORRUPT_FASTBOOT_ONCE", "0",
                ) != "1" or sequence != 0 or attempt != 0:
                    return packet
                corrupted = bytearray(packet)
                corrupted[-1] ^= 1
                return bytes(corrupted)

            # A network-first target emits its readiness only once before it
            # blocks in the self-synchronising stream scanner. Delaying the
            # host here exercises a real restarted/missed-ready session rather
            # than an injected protocol shortcut in either endpoint.
            host_delay = float(os.environ.get(
                "CPM_PLUS_JUKU_BOOT_HOST_DELAY", "0",
            ))
            if host_delay:
                time.sleep(host_delay)
            if os.environ.get(
                "CPM_PLUS_JUKU_DISCARD_BOOT_READY", "0",
            ) == "1":
                discarded = bytearray()
                while select.select([master], [], [], 0.05)[0]:
                    discarded.extend(os.read(master, 4096))
                require(
                    bytes((0xC7,)) in discarded
                    and b"JR\x10\x01" in discarded,
                    "delayed-host fixture did not capture the one-shot "
                    f"V16 readiness bytes: {discarded.hex()}",
                )
                print(
                    "COSIM: discarded one-shot C7/JR16 readiness before "
                    "starting the restarted host",
                    flush=True,
                )
            boot = serve_fast(
                master, fastboot.read_bytes(), container,
                stock_timeout=120, reply_timeout=8,
                verbose=os.environ.get(
                    "CPM_PLUS_JUKU_FASTBOOT_VERBOSE", "0",
                ) == "1",
                configure_rate=False, direct_core=direct_core,
                auto_rom_ready=network_rom,
                block_filter=fastboot_filter,
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
                            # Utility and soak suites are intentionally open-
                            # ended active sessions.  The server now exits on
                            # transport EOF, so a fixed wall-clock deadline
                            # cannot turn a long, healthy run into Disk I/O.
                            timeout=None, idle_timeout=None,
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
                            accumulate_stats=resume,
                            resume=resume or network_rom,
                            console_protocol=remote_console,
                            console_input=remote.input,
                            console_output=remote.output,
                            status_report_hook=status_reports.append,
                            diag_report_hook=diag_reports.append,
                            boot_report_hook=boot_reports.append,
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
                default_command_timeout = 600 if network_rom \
                    and remote_console else 120
                command_timeout = float(os.environ.get(
                    "CPM_PLUS_JUKU_COMMAND_TIMEOUT",
                    str(default_command_timeout),
                ))

                def request_checkpoint() -> tuple[dict[str, str], bytes]:
                    nonlocal checkpoint_generation
                    process.send_signal(signal.SIGUSR1)
                    deadline = time.monotonic() + 5
                    checkpoint_state: dict[str, str] = {}
                    while time.monotonic() < deadline:
                        state_path = case / "final.state"
                        if state_path.is_file():
                            checkpoint_state = dict(
                                line.split("=", 1)
                                for line in state_path.read_text().splitlines()
                                if "=" in line
                            )
                            generation = int(checkpoint_state.get(
                                "checkpoint_generation", "0",
                            ))
                            if generation > checkpoint_generation:
                                checkpoint_generation = generation
                                break
                        time.sleep(0.01)
                    else:
                        raise AssertionError(
                            "simulator did not produce an on-demand checkpoint",
                        )
                    return checkpoint_state, (case / "final.ram").read_bytes()

                def capture_transient_stack() -> dict[str, int]:
                    nonlocal last_captured_program_start
                    # The console hook exposes a byte when the target enters
                    # CONOUT, so an accelerated run can observe the final A>
                    # before that BDOS call returns and freezes the transient
                    # measurement. Poll the authoritative CPU state instead
                    # of treating a host-visible prompt byte as completion.
                    deadline = time.monotonic() + 5
                    checkpoint_state: dict[str, str] = {}
                    program_start = 0
                    while time.monotonic() < deadline:
                        checkpoint_state, _ram = request_checkpoint()
                        program_start = int(checkpoint_state.get(
                            "tpa_program_starts", "0",
                        ))
                        if program_start > last_captured_program_start and \
                                checkpoint_state.get(
                                    "tpa_measurement_frozen",
                                ) == "1" and checkpoint_state.get(
                                    "tpa_measurement_armed",
                                ) == "0":
                            break
                        time.sleep(0.01)
                    require(
                        program_start > last_captured_program_start,
                        "checkpoint did not observe a new CP/M transient: "
                        f"{checkpoint_state}",
                    )
                    require(
                        checkpoint_state.get("tpa_measurement_frozen") == "1"
                        and checkpoint_state.get(
                            "tpa_measurement_armed",
                        ) == "0",
                        "checkpoint did not freeze the requested transient: "
                        f"{checkpoint_state}",
                    )
                    last_captured_program_start = program_start
                    return {
                        "stack_entry_sp": int(
                            checkpoint_state["tpa_program_entry_sp"], 16,
                        ),
                        "stack_anchor_sp": int(
                            checkpoint_state[
                                "tpa_program_stack_anchor_sp"
                            ], 16,
                        ),
                        "stack_low_sp": int(
                            checkpoint_state["tpa_program_stack_low_sp"], 16,
                        ),
                        "stack_segment_min_anchor_sp": int(
                            checkpoint_state[
                                "tpa_program_segment_min_anchor_sp"
                            ], 16,
                        ),
                        "stack_segment_max_anchor_sp": int(
                            checkpoint_state[
                                "tpa_program_segment_max_anchor_sp"
                            ], 16,
                        ),
                        "stack_segments": int(
                            checkpoint_state["tpa_program_stack_segments"],
                        ),
                        "stack_bytes_observed": int(
                            checkpoint_state["tpa_program_stack_bytes"],
                        ),
                        "explicit_sp_writes": int(
                            checkpoint_state[
                                "tpa_program_explicit_sp_writes"
                            ],
                        ),
                    }

                def capture_vidtest() -> None:
                    expected = {
                        "hidden": vidtest_framebuffer(
                            video_mode, active_locale, cursor=False,
                        ),
                        "visible": vidtest_framebuffer(
                            video_mode, active_locale, cursor=True,
                        ),
                    }
                    seen: set[str] = set()
                    samples = 0
                    last_screen = b""
                    deadline = time.monotonic() + 8
                    # The output hook observes the last marker byte at CONOUT
                    # entry. Let that final cell finish before checkpointing.
                    time.sleep(0.05)
                    while time.monotonic() < deadline and len(seen) < 2:
                        _state, checkpoint_ram = request_checkpoint()
                        last_screen = checkpoint_ram[0xD800:0xD800 + 9600]
                        samples += 1
                        for phase, frame in expected.items():
                            if last_screen == frame:
                                seen.add(phase)
                                (case / f"vidtest-{phase}.bin").write_bytes(
                                    last_screen,
                                )
                        if len(seen) < 2:
                            time.sleep(0.04)
                    if len(seen) != 2:
                        differences = {
                            phase: next((
                                index for index, pair in enumerate(
                                    zip(last_screen, frame)
                                ) if pair[0] != pair[1]
                            ), None)
                            for phase, frame in expected.items()
                        }
                        raise AssertionError(
                            "VIDTEST did not reproduce both exact cursor "
                            f"phases for mode {video_mode}/locale "
                            f"{active_locale}; seen={sorted(seen)} "
                            f"samples={samples} first_differences="
                            f"{differences}",
                        )
                    print(
                        f"COSIM {case.name}: VIDTEST exact hidden/visible "
                        f"frames ({samples} checkpoints)",
                        flush=True,
                    )

                def capture_panel() -> None:
                    values = {
                        "s21": s21_raw,
                        "abi_major": 1,
                        "abi_minor": int(os.environ.get(
                            "CPM_PLUS_JUKU_EXPECT_BOOT_ABI_MINOR", "2",
                        ), 0),
                        "boot_stage": int(os.environ.get(
                            "CPM_PLUS_JUKU_EXPECT_BOOT_STAGE", "0x50",
                        ), 0),
                        "boot_retries": int(os.environ.get(
                            "CPM_PLUS_JUKU_EXPECT_BOOT_RETRIES", "0",
                        ), 0),
                        "reconnects": int(os.environ.get(
                            "CPM_PLUS_JUKU_EXPECT_PANEL_RECONNECTS", "0",
                        ), 0),
                        "disk_status": 0,
                    }
                    expected = {
                        "hidden": panel_framebuffer(
                            cursor=False, **values,
                        ),
                        "visible": panel_framebuffer(
                            cursor=True, **values,
                        ),
                    }
                    seen: set[str] = set()
                    samples = 0
                    last_screen = b""
                    deadline = time.monotonic() + 8
                    time.sleep(0.05)
                    while time.monotonic() < deadline and len(seen) < 2:
                        _state, checkpoint_ram = request_checkpoint()
                        last_screen = checkpoint_ram[0xD800:0xD800 + 9600]
                        samples += 1
                        for phase, frame in expected.items():
                            if last_screen == frame:
                                seen.add(phase)
                                (case / f"panel-{phase}.bin").write_bytes(
                                    last_screen,
                                )
                        if len(seen) < 2:
                            time.sleep(0.04)
                    if len(seen) != 2:
                        (case / "panel-last.bin").write_bytes(last_screen)
                        for phase, frame in expected.items():
                            (case / f"panel-expected-{phase}.bin").write_bytes(
                                frame,
                            )
                        differences = {
                            phase: next((
                                index for index, pair in enumerate(
                                    zip(last_screen, frame)
                                ) if pair[0] != pair[1]
                            ), None)
                            for phase, frame in expected.items()
                        }
                        raise AssertionError(
                            "PANEL did not reproduce both exact cursor phases; "
                            f"values={values} seen={sorted(seen)} "
                            f"samples={samples} first_differences={differences}",
                        )
                    print(
                        f"COSIM {case.name}: PANEL exact hidden/visible "
                        f"frames ({samples} checkpoints)",
                        flush=True,
                    )

                def run_extra_command(suffix: str = "") -> bytes:
                    command_name = f"CPM_PLUS_JUKU_EXTRA_COMMAND{suffix}"
                    marker_name = f"CPM_PLUS_JUKU_EXTRA_MARKER{suffix}"
                    markers_name = f"CPM_PLUS_JUKU_EXTRA_MARKERS{suffix}"
                    ready_name = \
                        f"CPM_PLUS_JUKU_EXTRA_READY_MARKER{suffix}"
                    input_name = f"CPM_PLUS_JUKU_EXTRA_INPUT_HEX{suffix}"
                    script_name = \
                        f"CPM_PLUS_JUKU_EXTRA_INPUT_SCRIPT{suffix}"
                    input_delay_name = \
                        f"CPM_PLUS_JUKU_EXTRA_INPUT_DELAY{suffix}"
                    command = os.environ.get(command_name)
                    if not command:
                        return b""
                    metric_name = f"extra{suffix}"
                    metric_started_at = time.monotonic()
                    metric_before = {
                        name: stats.get(name, 0)
                        for name in (
                            "reads", "read_records", "writes",
                            "request_wire_bytes",
                            "reply_wire_bytes",
                        )
                    }
                    capture_stack = os.environ.get(
                        "CPM_PLUS_JUKU_CAPTURE_EXTRA_STACK", "0",
                    ) == "1"
                    selected_stack_metrics = {
                        value.strip() for value in os.environ.get(
                            "CPM_PLUS_JUKU_CAPTURE_EXTRA_STACK_METRICS", "",
                        ).split(",") if value.strip()
                    }
                    capture_stack = capture_stack and (
                        not selected_stack_metrics
                        or metric_name in selected_stack_metrics
                    )
                    if capture_stack:
                        process.send_signal(signal.SIGUSR2)
                        # The emulator processes the signal at its next
                        # instruction boundary; key-matrix delivery is much
                        # slower, but this small guard makes that ordering
                        # explicit even with non-realtime test settings.
                        time.sleep(0.02)
                    send_console(command.encode("ascii") + b"\r")
                    ready_marker = os.environ.get(ready_name)
                    input_hex = os.environ.get(input_name)
                    input_script = os.environ.get(script_name)
                    if input_script and (ready_marker or input_hex):
                        raise AssertionError(
                            f"{script_name} is exclusive with {ready_name} "
                            f"and {input_name}"
                        )
                    if bool(ready_marker) != bool(input_hex):
                        raise AssertionError(
                            f"{ready_name} and {input_name} must be paired"
                        )
                    response = b""
                    if input_script:
                        steps = json.loads(input_script)
                        require(
                            isinstance(steps, list) and steps,
                            f"{script_name} must be a non-empty JSON list",
                        )
                        for step_index, step in enumerate(steps, 1):
                            require(
                                isinstance(step, dict)
                                and isinstance(step.get("wait"), str)
                                and isinstance(step.get("hex"), str),
                                f"{script_name} step {step_index} requires "
                                "string wait and hex fields",
                            )
                            print(
                                f"COSIM {case.name}: {command} input step "
                                f"{step_index} waiting for {step['wait']!r}",
                                flush=True,
                            )
                            response += read_until(
                                step["wait"].encode("ascii"), command_timeout,
                            )
                            print(
                                f"COSIM {case.name}: {command} input step "
                                f"{step_index} ready",
                                flush=True,
                            )
                            delay = float(step.get("delay", 0))
                            if delay:
                                time.sleep(delay)
                            send_console(bytes.fromhex(step["hex"]))
                    elif ready_marker is not None and input_hex is not None:
                        response += read_until(
                            ready_marker.encode("ascii"), command_timeout,
                        )
                        if os.environ.get(
                            "CPM_PLUS_JUKU_CAPTURE_VIDTEST", "0",
                        ) == "1":
                            require(
                                command == "VIDTEST",
                                "VIDTEST capture was armed for another command",
                            )
                            capture_vidtest()
                        if os.environ.get(
                            "CPM_PLUS_JUKU_CAPTURE_PANEL", "0",
                        ) == "1":
                            require(
                                command == "PANEL",
                                "PANEL capture was armed for another command",
                            )
                            capture_panel()
                        input_delay = float(os.environ.get(
                            input_delay_name, "0",
                        ))
                        if input_delay:
                            time.sleep(input_delay)
                        send_console(bytes.fromhex(input_hex))
                    response += read_until(b"A>", command_timeout)
                    marker = os.environ.get(
                        marker_name, command,
                    ).encode("ascii")
                    require(
                        marker in response,
                        f"extra command lacks {marker!r}: {response!r}",
                    )
                    for expected in os.environ.get(
                            markers_name, "").split("|"):
                        if expected:
                            encoded = expected.encode("ascii")
                            require(
                                encoded in response,
                                f"extra command lacks {encoded!r}: "
                                f"{response!r}",
                            )
                    command_metrics[metric_name] = {
                        "command": command,
                        "read_requests": stats.get("reads", 0)
                        - metric_before["reads"],
                        "read_records": stats.get("read_records", 0)
                        - metric_before["read_records"],
                        "write_requests": stats.get("writes", 0)
                        - metric_before["writes"],
                        "request_wire_bytes":
                        stats.get("request_wire_bytes", 0)
                        - metric_before["request_wire_bytes"],
                        "reply_wire_bytes": stats.get("reply_wire_bytes", 0)
                        - metric_before["reply_wire_bytes"],
                        "elapsed_seconds": round(
                            time.monotonic() - metric_started_at, 3,
                        ),
                    }
                    if capture_stack:
                        command_metrics[metric_name].update(
                            capture_transient_stack(),
                        )
                    print(f"COSIM {case.name}: {command}", flush=True)
                    return response

                profile_startup = first
                if expected_profile:
                    while profile_startup.count(b"A>") < 2:
                        profile_startup += read_until(b"A>", command_timeout)
                    require(
                        expected_profile.encode("ascii") in profile_startup
                        and (
                            expected_profile_output is None
                            or expected_profile_output.encode("ascii")
                            in profile_startup
                        ),
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
                if os.environ.get("CPM_PLUS_JUKU_QUICK_SMOKE") == "1":
                    require(
                        b"VER" in second and b"TOOLS" in second,
                        f"CI smoke directory lacks expected tools: {second!r}",
                    )
                    send_console(b"VER\r")
                    version = read_until(b"A>", command_timeout)
                    require(
                        b"CP/M Plus 3.1 for Juku" in version,
                        f"CI smoke version report differs: {version!r}",
                    )
                    if os.environ.get(
                        "CPM_PLUS_JUKU_QUICK_C8_SERVICES",
                    ) == "1":
                        send_console(b"STATUS\r")
                        status = read_until(b"A>", command_timeout)
                        require(
                            b"ROM: Juku ABI 01.03" in status
                            and b"TPA 0100-9BFF" in status
                            and b"BIOS BE00-C1FF" in status,
                            f"C8 status/map report differs: {status!r}",
                        )
                        print(f"COSIM {case.name}: C8 STATUS", flush=True)
                        send_console(b"DIAG CPU\r")
                        diagnostic = read_until(b"A>", command_timeout)
                        require(
                            b"CPU: PASS" in diagnostic,
                            f"C8 diagnostic report differs: {diagnostic!r}",
                        )
                        print(f"COSIM {case.name}: C8 DIAG", flush=True)
                        send_console(b"WBOOT\r")
                        warm = read_until(b"A>", command_timeout)
                        require(
                            warm.endswith(b"A>"),
                            f"C8 warm boot differs: {warm!r}",
                        )
                        send_console(b"STATUS\r")
                        warm_status = read_until(b"A>", command_timeout)
                        require(
                            b"Boot marker (00 cold/01 warm): 01" in
                            warm_status,
                            f"C8 warm status differs: {warm_status!r}",
                        )
                        print(f"COSIM {case.name}: C8 WBOOT", flush=True)
                    print(
                        f"JUKU CP/M PLUS 3.1: PASS ({boot_label}, A>, DIR, "
                        + (
                            "VER, STATUS, DIAG, WBOOT)"
                            if os.environ.get(
                                "CPM_PLUS_JUKU_QUICK_C8_SERVICES",
                            ) == "1" else "VER)"
                        ),
                        flush=True,
                    )
                    return
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
                extra_transcript = run_extra_command()
                for extra_number in range(2, 25):
                    extra_transcript += run_extra_command(str(extra_number))
                send_console(b"WBOOT\r")
                fifth = read_until(b"A>", command_timeout)
                print(f"COSIM {case.name}: WBOOT", flush=True)
                # Native recovery profiles deliberately warm boot from user 1
                # to prove that public CCP.COM can be reloaded.  Return to user
                # 0 before the shared erase/write regression continues.
                send_console(b"USER 0\r")
                read_until(b"A>", command_timeout)
                soak_cycles = int(os.environ.get(
                    "CPM_PLUS_JUKU_SOAK_CYCLES", "0",
                )) if disk_fault == "mid-session-restart" else 0
                soak_writes = os.environ.get(
                    "CPM_PLUS_JUKU_SOAK_WRITES", "0",
                ) == "1"
                for _ in range(soak_cycles):
                    send_console(b"DIR\r")
                    read_until(b"A>", 120)
                    send_console(b"DIAG CPU\r")
                    soak_diag = read_until(b"A>", 120)
                    require(b"CPU: PASS" in soak_diag,
                            "NetDisk soak diagnostic failed")
                    if soak_writes:
                        writes_before = stats.get("writes", 0)
                        send_console(b"SOAK\r")
                        soak_save = read_until(b"A>", 120)
                        require(
                            b"SOAK: PASS" in soak_save
                            and stats.get("writes", 0) > writes_before,
                            f"NetDisk soak write cycle failed: {soak_save!r}",
                        )
                fault_evidence["soak_cycles"] = soak_cycles
                fault_evidence["soak_write_cycles"] = \
                    soak_cycles if soak_writes else 0
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
            worker.join(timeout=3)
            os.close(master)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            try:
                os.close(master)
            except OSError:
                pass
            os.close(console_master)
            # Keep the exact host-side media state even when a command or an
            # assertion fails.  Directory-creation regressions otherwise
            # disappear with the temporary server bytearray before cpmtools
            # can distinguish a target write bug from a stale-cache bug.
            if "worker" in locals() and worker.is_alive():
                worker.join(timeout=3)
            (case / "served-volume.img").write_bytes(volume)

    if os.environ.get("CPM_PLUS_JUKU_PRINT_TRACE_STDERR", "0") == "1":
        print((case / "stderr.txt").read_text(), end="", flush=True)

    # Preserve completed command evidence before evaluating the independent
    # post-run oracles. A late count or framebuffer failure must not erase the
    # measurements needed to diagnose an otherwise expensive full matrix.
    if command_metrics:
        metrics_document = {
            "_platform": {
                "network_rom": artifact_identity(rom),
                "system": artifact_identity(system),
                "fastboot": artifact_identity(fastboot),
            },
            **command_metrics,
        }
        metrics_text = json.dumps(metrics_document, indent=2) + "\n"
        (case / "disk-metrics.json").write_text(metrics_text)
        metrics_output = os.environ.get("CPM_PLUS_JUKU_METRICS_OUTPUT")
        if metrics_output:
            Path(metrics_output).write_text(metrics_text)

    if direct_core:
        expected_auto_ready = int(os.environ.get(
            "CPM_PLUS_JUKU_EXPECT_AUTO_READY_SEEN",
            str(int(network_rom)),
        ))
        require(
            boot["direct_core"] == 1
            and boot["stock_sent_frames"] == 0
            and boot["auto_rom_ready"] == int(network_rom)
            and boot["auto_ready_seen"] == expected_auto_ready,
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
        require(
            b"DIR" in second
            and b"DIAG" in second
            and b"A>" in second,
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
        for name in ("boot", "dir", "type", "b_login", "b_dir"):
            expected = os.environ.get(
                f"CPM_PLUS_JUKU_EXPECT_{name.upper()}_READS",
            )
            if expected is not None:
                require(
                    name in command_metrics,
                    f"{name.upper()} read-request baseline requested "
                    "without a matching workload phase",
                )
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
        expected_console_bulk = int(os.environ.get(
            "CPM_PLUS_JUKU_EXPECT_CONSOLE_BULK", "0",
        ))
        require(
            stats.get("console_bulk_requests", 0) == expected_console_bulk,
            "bounded N4 console-output count differs: "
            f"expected={expected_console_bulk} stats={stats}",
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
                and status_reports[-1]["features"] == 0x1F
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
        expected_boot_reports = int(os.environ.get(
            "CPM_PLUS_JUKU_EXPECT_BOOT_REPORTS", "0",
        ))
        require(
            stats.get("boot_reports", 0) == expected_boot_reports
            and len(boot_reports) == expected_boot_reports,
            "target bootstrap report count differs: "
            f"expected={expected_boot_reports} reports={boot_reports} "
            f"stats={stats}",
        )
        if expected_boot_reports:
            expected_stage = int(os.environ.get(
                "CPM_PLUS_JUKU_EXPECT_BOOT_STAGE", "0",
            ), 0)
            expected_protocol = int(os.environ.get(
                "CPM_PLUS_JUKU_EXPECT_BOOT_PROTOCOL", "0",
            ), 0)
            expected_abi_minor = int(os.environ.get(
                "CPM_PLUS_JUKU_EXPECT_BOOT_ABI_MINOR", "0",
            ), 0)
            expected_boot_retries = int(os.environ.get(
                "CPM_PLUS_JUKU_EXPECT_BOOT_RETRIES", "0",
            ), 0)
            report = boot_reports[-1]
            require(
                report["stage"] == expected_stage
                and report["retries"] == expected_boot_retries
                and report["protocol"] == expected_protocol
                and report["abi_minor"] == expected_abi_minor,
                f"target bootstrap tuple differs: {boot_reports[-1]}",
            )
            require(
                boot["retries"] == expected_boot_retries,
                "host/target bootstrap retry counts differ: "
                f"host={boot['retries']} target={report}",
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
            expected_writes = expected_soak if os.environ.get(
                "CPM_PLUS_JUKU_SOAK_WRITES", "0",
            ) == "1" else 0
            require(
                fault_evidence.get("soak_write_cycles", 0) == expected_writes,
                "NetDisk soak write cycle count differs",
            )
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
    if os.environ.get("CPM_PLUS_JUKU_EXPECT_STRICT_TPA_OPCODES") == "1":
        require(
            int(state.get("tpa_opcode_fetches", "0")) > 0
            and state.get("tpa_z80_prefix_fetches") == "0"
            and state.get("tpa_undocumented_opcode_fetches") == "0",
            "TPA executed a Z80-prefix or undocumented 8080 opcode: "
            f"fetches={state.get('tpa_opcode_fetches')} "
            f"z80={state.get('tpa_z80_prefix_fetches')} "
            f"undocumented={state.get('tpa_undocumented_opcode_fetches')}",
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
    loader_address = entry_address - 0x2200
    bdos_address = entry_address - 0x1F00
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
            + second + third + fourth + extra_transcript + fifth + sixth
        if drive_b is not None:
            transcript += selected_b + listed_b + diagnosed_b + selected_a
        (case / "console.bin").write_bytes(transcript)
        # SYSTEM is an immutable C4 artifact built at its recorded historical
        # source boundary. Do not compare it with today's evolved renderer;
        # its checked bytes and physical qualification are authoritative, and
        # its captured framebuffer remains the cross-path reference below.
        # A newly linked RAM-console fixture must still match the independent
        # current source oracle exactly.
        if system.resolve() != SYSTEM.resolve():
            expected_screen = render_console_transcript(
                transcript, mode=video_mode,
            )
            expected_screen_hidden = render_console_transcript(
                transcript, mode=video_mode, cursor=False,
            )
            (case / "expected-screen.bin").write_bytes(expected_screen)
            if screen not in (expected_screen, expected_screen_hidden):
                first_difference = next(
                    index for index, pair in enumerate(
                        zip(screen, expected_screen),
                    ) if pair[0] != pair[1]
                )
                require(
                    False,
                    "RAM console differs from independent source-font oracle "
                    f"at framebuffer byte {first_difference}: "
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
                and ram[0xD7DC:0xD7DE] == bytes((0x80, 0xCB))
                and ram[0xD7DE:0xD7E0] == bytes((0xA0, 0xCF)),
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
        "network-compound", "network-soak", "network-remote", "video",
        "vidtest", "remote", "distribution", "all",
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
        if selected == "network-soak":
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
        if selected == "vidtest":
            for video_mode, locale in (
                (0, 0), (1, 0), (2, 0), (3, 0),
                (3, 1), (3, 2), (3, 3),
            ):
                run(
                    trace, work, direct_core=True, network_rom=True,
                    video_mode=video_mode, locale=locale,
                )
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
        if selected == "network-soak":
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
        if selected == "vidtest":
            for video_mode, locale in (
                (0, 0), (1, 0), (2, 0), (3, 0),
                (3, 1), (3, 2), (3, 3),
            ):
                run(
                    trace, work, direct_core=True, network_rom=True,
                    video_mode=video_mode, locale=locale,
                )
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
