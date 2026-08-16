#!/usr/bin/env python3
"""Boot non-banked CP/M Plus through Ekta4402 and exercise NetDisk."""

from __future__ import annotations

from collections.abc import Callable
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
ROM_NETWORK = (
    COSIM / "spinoffs" / "jukuravi" / "network-rom" /
    "juku-network-rom-abi1.bin"
)
SYSTEM = ROOT / "out" / "cpm-plus-juku-system.bin"
FASTBOOT = ROOT / "out" / "cpm-plus-juku-fastboot-v15.bin"
ROM_SYSTEM = ROOT / "out" / "cpm-plus-juku-network-rom-system.bin"
ROM_FASTBOOT = ROOT / "out" / "cpm-plus-juku-network-rom-fastboot-v15.bin"
VOLUME = ROOT / "out" / "cpm-plus-juku.img"
ZMAC = ROOT / "build" / "bin" / "zmac"
LD80 = ROOT / "build" / "bin" / "ld80"
ZX0 = ROOT / "build" / "bin" / "zx0"
sys.path.insert(0, str(COSIM / "tools"))

from janet_disk_server import serve_disk  # noqa: E402
from janet_fastboot import serve_fast  # noqa: E402

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
        str(platform), "-P0xa900",
        str(ROOT / "build" / "ram-keyboard.rel"), "-P0xac10",
        str(netdisk), "-P0xae80", str(ROOT / "build" / "netconsole.rel"),
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


def read_console_until(fd: int, marker: bytes, timeout: float) -> bytes:
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


def run(trace: Path, work: Path, *, direct_core: bool,
        fastboot: Path = FASTBOOT, system: Path = SYSTEM,
        expect_disk_failure: str | None = None,
        network_rom: bool = False, disk_fault: str | None = None) -> None:
    require(not network_rom or direct_core,
            "network ROM requires direct-core fastboot")
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
    case = work / case_name
    case.mkdir()
    master, slave = pty.openpty()
    tty.setraw(slave)
    console_master, console_slave = pty.openpty()
    tty.setraw(console_slave)
    environment = os.environ.copy()
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
        JUKU_CHECKPOINT_PREFIX=str(case / "final"),
    )
    if network_rom:
        environment.pop("JUKU_KEYS", None)
    else:
        environment["JUKU_KEYS"] = "N" if direct_core else "TN0201"
    volume = bytearray(VOLUME.read_bytes())
    stats: dict[str, int] = {}
    fault_evidence: dict[str, int] = {}
    restart_armed = threading.Event()
    errors: list[BaseException] = []
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
                    ) -> None:
                        serve_disk(
                            master, volume, timeout=180, idle_timeout=None,
                            writable=True, verbose=False, stats=stats_target,
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
                            resume=True,
                        )

                    if disk_fault in ("server-restart", "mid-session-restart"):
                        def stop_server(_attempt: int, _reply: bytes) -> bytes:
                            if disk_fault == "mid-session-restart" and \
                                    not restart_armed.is_set():
                                return _reply
                            raise RestartDiskServer

                        try:
                            serve(stats, stop_server)
                        except RestartDiskServer:
                            fault_evidence["server_restarts"] = 1
                        serve(stats, None)
                    else:
                        serve(stats, filter_reply)
                except BaseException as error:
                    errors.append(error)

            worker = threading.Thread(target=disk_worker)
            worker.start()
            if expect_disk_failure:
                first = read_console_until(
                    console_master, b"Disk I/O",
                    float(os.environ.get(
                        "CPM_PLUS_JUKU_FAILURE_TIMEOUT", "120",
                    )),
                )
                second = third = b""
            else:
                first = read_console_until(
                    console_master, b"A>",
                    float(os.environ.get(
                        "CPM_PLUS_JUKU_PROMPT_TIMEOUT", "120",
                    )),
                )
                if disk_fault == "mid-session-restart":
                    restart_armed.set()
                os.write(console_master, b"DIR\r")
                second = read_console_until(console_master, b"A>", 120)
                os.write(console_master, b"TYPE README.TXT\r")
                third = read_console_paged(console_master, 120)
                os.write(console_master, b"DIAG CPU\r")
                fourth = read_console_until(console_master, b"A>", 120)
                os.write(console_master, b"WBOOT\r")
                fifth = read_console_until(console_master, b"A>", 120)
                soak_cycles = int(os.environ.get(
                    "CPM_PLUS_JUKU_SOAK_CYCLES", "0",
                )) if disk_fault == "mid-session-restart" else 0
                for _ in range(soak_cycles):
                    os.write(console_master, b"DIR\r")
                    read_console_until(console_master, b"A>", 120)
                    os.write(console_master, b"DIAG CPU\r")
                    soak_diag = read_console_until(
                        console_master, b"A>", 120,
                    )
                    require(b"CPU: PASS" in soak_diag,
                            "NetDisk soak diagnostic failed")
                fault_evidence["soak_cycles"] = soak_cycles
                os.write(console_master, b"ERA README.TXT\r")
                sixth = read_console_until(console_master, b"A>", 120)
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
    require(b"CP/M Plus" in first or b"CP/M Version 3" in first,
            f"CP/M Plus banner is missing: {first!r}")
    if expect_disk_failure:
        require(b"Disk I/O" in first,
                f"legacy drain did not reproduce the disk error: {first!r}")
        require(stats.get("retries", 0) >= 2,
                f"legacy drain did not provoke three N3 attempts: {stats}")
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
        require(stats.get("reads", 0) >= 1,
                f"CP/M Plus issued no NetDisk reads: {stats}")
        require(stats.get("writes", 0) >= 1,
                f"CP/M Plus issued no NetDisk writes: {stats}")
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
        ram_console_reference = screen
    if network_rom:
        gate = ram[0xD620:0xD700]
        signature = gate.rfind(b"JUKUABI\0")
        require(signature > 0 and gate[signature - 1] == 1,
                "CP/M Plus did not initialize the fixed ROM call gate")
        require(
            ram[0xC5F1] == 0 and ram[0xD785] == 1
            and ram[0xD788] == 0x0D,
            "CP/M Plus did not retain ROM serial/keyboard binding state",
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
    else:
        require(resident_overruns == 0,
                f"fixed NetDisk path still overran the resident 8251: {state}")
    print(
        "JUKU CP/M PLUS 3.1: PASS "
        f"({boot_label} "
        f"boot, A>, DIR, TYPE README.TXT, DIAG CPU, warm boot, "
        f"ERA README.TXT, reads={stats['reads']}, "
        f"writes={stats['writes']}, retries={stats['retries']}, "
        f"resident-overruns={resident_overruns}, "
        f"bootstrap-overruns={overruns - resident_overruns}"
        f"{', soak-cycles=' + str(fault_evidence.get('soak_cycles', 0)) if fault_evidence.get('soak_cycles', 0) else ''}"
        f"{', recovered-faults=' + disk_fault if disk_fault else ''})"
    )


def main() -> None:
    for path in (
        ROM_DIRECT, ROM_STOCK, ROM_NETWORK, SYSTEM, FASTBOOT,
        ROM_SYSTEM, ROM_FASTBOOT, VOLUME,
    ):
        require(path.is_file(), f"build input is missing: {path}")
    selected = os.environ.get("CPM_PLUS_JUKU_BOOT_PATH", "both")
    require(selected in ("both", "direct", "stock", "network", "all"),
            f"invalid CPM_PLUS_JUKU_BOOT_PATH={selected!r}")
    paths = (True, False) if selected in ("both", "all") else \
        (selected == "direct",) if selected in ("direct", "stock") else ()
    include_network = selected in ("network", "all")
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


if __name__ == "__main__":
    main()
