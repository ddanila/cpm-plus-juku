PYTHON ?= python3
CC ?= cc
CXX ?= c++
BISON ?= bison

BUILD := build
OUT := out
BIN := $(BUILD)/bin
ZMAC := $(BIN)/zmac
LD80 := $(BIN)/ld80
ZX0 := $(BIN)/zx0
ZXCC := $(BIN)/zxcc
ZXCC_ARCHIVE := third_party/zxcc/releases/zxcc-0.5.7.tar.gz
ZXCC_SOURCE := $(BUILD)/zxcc-0.5.7
ZXCC_PREFIX := $(BUILD)/zxcc-install
COMMON := third_party/juku-common

SYSTEM := $(OUT)/cpm-plus-juku-system.bin
FASTBOOT := $(OUT)/cpm-plus-juku-fastboot-v15.bin
ROM_SYSTEM := $(OUT)/cpm-plus-juku-network-rom-system.bin
ROM_FASTBOOT := $(OUT)/cpm-plus-juku-network-rom-fastboot-v15.bin
NATIVE_ROM_SYS := $(BUILD)/cpm3-network-rom-native.sys
NATIVE_ROM_SYSTEM := $(OUT)/cpm-plus-juku-network-rom-native-system.bin
NATIVE_ROM_FASTBOOT := $(OUT)/cpm-plus-juku-network-rom-native-fastboot-v15.bin
NATIVE_TEST_VOLUME := $(OUT)/cpm-plus-juku-native-test.img
NATIVE_RECOVERY_VOLUME := $(OUT)/cpm-plus-juku-native-recovery.img
VOLUME := $(OUT)/cpm-plus-juku.img
RECOVERY_VOLUME := $(OUT)/cpm-plus-juku-recovery.img
FULL_VOLUME := $(OUT)/cpm-plus-juku-full.img
APPS_VOLUME := $(OUT)/cpm-plus-juku-apps.juk
DEMO_VOLUME := $(OUT)/cpm-plus-juku-museum-demo.img
RECOVERY_REPORT := $(OUT)/cpm-plus-juku-recovery.report.json
NATIVE_RECOVERY_REPORT := $(OUT)/cpm-plus-juku-native-recovery.report.json
FULL_REPORT := $(OUT)/cpm-plus-juku-full.report.json
APPS_REPORT := $(OUT)/cpm-plus-juku-apps.report.json
DEMO_REPORT := $(OUT)/cpm-plus-juku-museum-demo.report.json

.PHONY: all check clean tools verify-prebuilt rom-budget-check \
	network-rom-cosim-check network-rom-soak-check bench-candidate \
	distribution distribution-check distribution-cosim-check \
	distribution-input-check \
	cpm3-toolchain cpm3-system-check native-services-check \
	regenerate-cpm3 regenerate-cpm3-rom
all: $(SYSTEM) $(FASTBOOT) $(ROM_SYSTEM) $(ROM_FASTBOOT) $(VOLUME) distribution

distribution: $(RECOVERY_VOLUME) $(RECOVERY_REPORT) \
	$(NATIVE_RECOVERY_VOLUME) $(NATIVE_RECOVERY_REPORT) \
	$(FULL_VOLUME) $(FULL_REPORT) $(APPS_VOLUME) $(APPS_REPORT) \
	$(DEMO_VOLUME) $(DEMO_REPORT)

tools: $(ZMAC) $(LD80) $(ZX0)

verify-prebuilt: all
	cmp $(SYSTEM) prebuilt/cpm-plus-juku-system.bin
	cmp $(FASTBOOT) prebuilt/cpm-plus-juku-fastboot-v15.bin
	cmp $(ROM_SYSTEM) prebuilt/cpm-plus-juku-network-rom-system.bin
	cmp $(ROM_FASTBOOT) prebuilt/cpm-plus-juku-network-rom-fastboot-v15.bin
	cmp $(VOLUME) prebuilt/cpm-plus-juku.img

rom-budget-check: tools $(BUILD)/fastboot-core.cim $(BUILD)/fastboot-extension.cim
	$(PYTHON) tools/rom_budget.py --check

check: verify-prebuilt rom-budget-check distribution-input-check \
	distribution-check cpm3-system-check native-services-check
	CPM_PLUS_JUKU_BOOT_PATH=all $(PYTHON) tests/cosim_check.py

distribution-input-check:
	$(PYTHON) tools/extract_cpm3_utilities.py --verify
	$(PYTHON) tools/extract_cpm3_utilities.py
	$(PYTHON) tools/extract_cpm3_utilities.py --check
	$(PYTHON) tests/cpm3_utility_inputs_test.py

distribution-check: distribution
	$(PYTHON) tests/distribution_test.py

distribution-cosim-check: all
	CPM_PLUS_JUKU_VOLUME=$(DEMO_VOLUME) \
	CPM_PLUS_JUKU_DRIVE_B=$(APPS_VOLUME) \
	CPM_PLUS_JUKU_EXPECT_PROFILE=DIR \
	CPM_PLUS_JUKU_BOOT_PATH=distribution $(PYTHON) tests/cosim_check.py

network-rom-cosim-check: all
	CPM_PLUS_JUKU_BOOT_PATH=network $(PYTHON) tests/cosim_check.py

network-rom-soak-check: all
	CPM_PLUS_JUKU_BOOT_PATH=network \
	CPM_PLUS_JUKU_SOAK_CYCLES=16 CPM_PLUS_JUKU_REALTIME_HZ=20000000 \
	$(PYTHON) tests/cosim_check.py

bench-candidate: check
	$(PYTHON) ../8080-cosim/spinoffs/jukuravi/network-rom/build_network_rom.py --check
	../8080-cosim/sync/network_first_rom_hdl_check.sh
	$(PYTHON) tools/package_bench_candidate.py
	$(PYTHON) tests/physical_qualification_test.py

clean:
	rm -r $(BUILD) $(OUT)

$(BUILD) $(OUT) $(BIN) $(BUILD)/zmac:
	mkdir -p $@

$(BUILD)/zmac/docgen: third_party/zmac/doc.c | $(BUILD)/zmac
	$(CC) -O2 -DMK_DOC -Wno-main -o $@ $<

$(BUILD)/zmac/doc.inl: $(BUILD)/zmac/docgen third_party/zmac/doc.txt | $(BUILD)/zmac
	cp third_party/zmac/doc.txt $(BUILD)/zmac/doc.txt
	cd $(BUILD)/zmac && ./docgen >/dev/null

$(BUILD)/zmac/parser.c $(BUILD)/zmac/parser.h &: third_party/zmac/zmac.y | $(BUILD)/zmac
	$(BISON) --defines=$(BUILD)/zmac/parser.h \
		--output=$(BUILD)/zmac/parser.c $<

$(BUILD)/zmac/parser.o: $(BUILD)/zmac/parser.c $(BUILD)/zmac/parser.h \
		$(BUILD)/zmac/doc.inl third_party/zmac/mio.h
	$(CC) -O2 -c -I$(BUILD)/zmac -Ithird_party/zmac -o $@ $<

$(BUILD)/zmac/doc.o: third_party/zmac/doc.c $(BUILD)/zmac/doc.inl \
		$(BUILD)/zmac/parser.h
	$(CC) -O2 -c -I$(BUILD)/zmac -Ithird_party/zmac -o $@ $<

$(BUILD)/zmac/mio.o: third_party/zmac/mio.c $(BUILD)/zmac/parser.h \
		$(BUILD)/zmac/doc.inl
	$(CC) -O2 -c -I$(BUILD)/zmac -Ithird_party/zmac -o $@ $<

$(BUILD)/zmac/zi80dis.o: third_party/zmac/zi80dis.cpp \
		third_party/zmac/zi80dis.h $(BUILD)/zmac/parser.h
	$(CXX) -O2 -Wno-unused-result -c -I$(BUILD)/zmac \
		-Ithird_party/zmac -o $@ $<

$(ZMAC): $(BUILD)/zmac/parser.o $(BUILD)/zmac/doc.o \
		$(BUILD)/zmac/mio.o $(BUILD)/zmac/zi80dis.o | $(BIN)
	$(CXX) -o $@ $^

LD80_SOURCES := $(wildcard third_party/ld80/*.c)
$(LD80): $(LD80_SOURCES) third_party/ld80/ld80.h | $(BIN)
	$(CC) -O2 -Wno-stringop-truncation \
		-Wno-format-overflow -Ithird_party/ld80 -o $@ $(LD80_SOURCES)

ZX0_SOURCES := $(wildcard third_party/zx0/*.c)
$(ZX0): $(ZX0_SOURCES) third_party/zx0/zx0.h | $(BIN)
	$(CC) -O2 -Wno-sign-compare -Ithird_party/zx0 -o $@ $(ZX0_SOURCES)

$(ZXCC): $(ZXCC_ARCHIVE) | $(BUILD) $(BIN)
	test "$$(sha256sum $< | cut -d' ' -f1)" = \
		6095119a31a610de84ff8f049d17421dd912c6fd2df18373e5f0a3bc796eb4bf
	mkdir -p $(ZXCC_SOURCE) $(ZXCC_PREFIX)
	tar -xzf $< --strip-components=1 -C $(ZXCC_SOURCE)
	cd $(ZXCC_SOURCE) && CFLAGS='-O2 -std=gnu17' \
		./configure --prefix=$(abspath $(ZXCC_PREFIX))
	$(MAKE) -C $(ZXCC_SOURCE)
	$(MAKE) -C $(ZXCC_SOURCE) install
	cp $(ZXCC_PREFIX)/bin/zxcc $@

$(BUILD)/platform-adapter.rel: src/platform-adapter.asm \
		$(COMMON)/platform/ram-console.asm \
		$(COMMON)/platform/ram-console-font.asm \
		$(COMMON)/platform/creep-console-font.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 \
		-I$(COMMON)/platform -o $@ $<

$(BUILD)/platform-adapter-romabi.rel: src/platform-adapter.asm \
		$(COMMON)/platform/rom-abi.inc $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -DROMABI \
		-I$(COMMON)/platform -o $@ $<

$(BUILD)/platform-adapter-romabi-native.rel: src/platform-adapter.asm \
		$(COMMON)/platform/rom-abi.inc $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -DROMABI -DNATIVE_SERVICES \
		-I$(COMMON)/platform -o $@ $<

$(BUILD)/cpm3-native-services.rel: src/cpm3-native-services.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -o $@ $<

$(BUILD)/ram-keyboard.rel: $(COMMON)/platform/ram-keyboard.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -o $@ $<

$(BUILD)/netdisk-v3.rel: $(COMMON)/platform/netdisk-v3.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -DCPM3ADAPTER -o $@ $<

$(BUILD)/netconsole.rel: $(COMMON)/platform/netconsole.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -o $@ $<

$(BUILD)/netconsole-romabi.rel: $(COMMON)/platform/netconsole.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -DNETCONSOLE_EAGER_POLL -o $@ $<

$(BUILD)/netconsole-romabi-native.rel: \
		$(COMMON)/platform/netconsole.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -DNETCONSOLE_EAGER_POLL \
		-DNATIVE_SERVICES -o $@ $<

$(BUILD)/adapter.all: $(BUILD)/platform-adapter.rel \
		$(BUILD)/ram-keyboard.rel $(BUILD)/netdisk-v3.rel \
		$(BUILD)/netconsole.rel $(LD80)
	$(LD80) -m -O bin -o $@ -s /dev/null \
		-P0xa000 $(BUILD)/platform-adapter.rel \
		-P0xaa90 $(BUILD)/ram-keyboard.rel \
		-P0xac10 $(BUILD)/netdisk-v3.rel \
		-P0xae40 $(BUILD)/netconsole.rel

$(BUILD)/adapter.bin: $(BUILD)/adapter.all
	tail -c+40961 $< >$@
	test $$(stat -c %s $@) -le 4096

$(BUILD)/adapter-romabi.all: $(BUILD)/platform-adapter-romabi.rel \
		$(BUILD)/netconsole-romabi.rel $(LD80)
	$(LD80) -m -O bin -o $@ -s /dev/null \
		-P0xc000 $(BUILD)/platform-adapter-romabi.rel \
		-P0xc22c $(BUILD)/netconsole-romabi.rel

$(BUILD)/adapter-romabi.bin: $(BUILD)/adapter-romabi.all
	tail -c+49153 $< >$@
	test $$(stat -c %s $@) -le 4096

$(BUILD)/adapter-romabi-native.all: \
		$(BUILD)/platform-adapter-romabi-native.rel \
		$(BUILD)/netconsole-romabi-native.rel $(BUILD)/cpm3-native-services.rel \
		$(LD80)
	$(LD80) -m -O bin -o $@ -s /dev/null \
		-P0xc000 $(BUILD)/platform-adapter-romabi-native.rel \
		-P0xc250 $(BUILD)/netconsole-romabi-native.rel \
		-P0xc500 $(BUILD)/cpm3-native-services.rel

$(BUILD)/adapter-romabi-native.bin: $(BUILD)/adapter-romabi-native.all
	tail -c+49153 $< >$@
	test $$(stat -c %s $@) -le 1536

$(SYSTEM): $(BUILD)/adapter.bin third_party/cpm3/cpm3.sys \
		tools/mksystem3.py | $(OUT)
	$(PYTHON) tools/mksystem3.py $(BUILD)/adapter.bin \
		third_party/cpm3/cpm3.sys $@

$(ROM_SYSTEM): $(BUILD)/adapter-romabi.bin \
		third_party/cpm3/cpm3-network-rom.sys \
		tools/mksystem3.py | $(OUT)
	$(PYTHON) tools/mksystem3.py $(BUILD)/adapter-romabi.bin \
		third_party/cpm3/cpm3-network-rom.sys $@ \
		--load-address 0x9000 --adapter-address 0xc000 \
		--entry-address 0xbc00 --end-address 0xd600

$(NATIVE_ROM_SYS): src/cpm3-bios.asm tools/regenerate_cpm3.py \
		third_party/cpm3/bdos3.spr third_party/cpm3/gencpm.dat \
		third_party/cpm3/scb.asm $(ZXCC) | $(BUILD)
	$(PYTHON) tools/regenerate_cpm3.py --native-services \
		--adapter-address 0xc000 --top-page 0xbf \
		--metadata-policy gencpm --output $@

$(NATIVE_ROM_SYSTEM): $(BUILD)/adapter-romabi-native.bin \
		$(NATIVE_ROM_SYS) tools/mksystem3.py | $(OUT)
	$(PYTHON) tools/mksystem3.py $(BUILD)/adapter-romabi-native.bin \
		$(NATIVE_ROM_SYS) $@ --load-address 0x9000 \
		--adapter-address 0xc000 --entry-address 0xbc00 \
		--end-address 0xd600

FASTBOOT_CORE_DEFS := FASTBOOT_8N1 FASTBOOT_ZX0 FASTBOOT_STREAM \
	FASTBOOT_V15 FASTBOOT_EXACT FASTBOOT_EXT_ACK FASTBOOT_PROBE_SYNC
FASTBOOT_EXTENSION_DEFS := FASTBOOT_8N1 FASTBOOT_ZX0 FASTBOOT_TIGHT \
	FASTBOOT_V15 FASTBOOT_STREAM_ACK FASTBOOT_CPM3

$(BUILD)/fastboot-core.cim: $(COMMON)/transport/fastboot-core.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 \
		$(addprefix -D,$(FASTBOOT_CORE_DEFS)) -o $@ $<

$(BUILD)/fastboot-extension.cim: \
		$(COMMON)/transport/fastboot-extension.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 \
		$(addprefix -D,$(FASTBOOT_EXTENSION_DEFS)) -o $@ $<

$(BUILD)/fastboot-extension-rom.cim: \
		$(COMMON)/transport/fastboot-extension.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 \
		$(addprefix -D,$(FASTBOOT_EXTENSION_DEFS) FASTBOOT_CPM3_ROM) \
		-o $@ $<

$(FASTBOOT): $(BUILD)/fastboot-core.cim \
		$(BUILD)/fastboot-extension.cim $(SYSTEM) $(ZX0) \
		tools/build_fastboot.py | $(OUT)
	$(PYTHON) tools/build_fastboot.py $(BUILD)/fastboot-core.cim \
		$(BUILD)/fastboot-extension.cim $(SYSTEM) $(ZX0) $@

$(ROM_FASTBOOT): $(BUILD)/fastboot-core.cim \
		$(BUILD)/fastboot-extension-rom.cim $(ROM_SYSTEM) $(ZX0) \
		tools/build_fastboot.py | $(OUT)
	$(PYTHON) tools/build_fastboot.py $(BUILD)/fastboot-core.cim \
		$(BUILD)/fastboot-extension-rom.cim $(ROM_SYSTEM) $(ZX0) $@

$(NATIVE_ROM_FASTBOOT): $(BUILD)/fastboot-core.cim \
		$(BUILD)/fastboot-extension-rom.cim $(NATIVE_ROM_SYSTEM) $(ZX0) \
		tools/build_fastboot.py | $(OUT)
	$(PYTHON) tools/build_fastboot.py $(BUILD)/fastboot-core.cim \
		$(BUILD)/fastboot-extension-rom.cim $(NATIVE_ROM_SYSTEM) $(ZX0) $@

$(BUILD)/diag.cim: src/diag.asm $(wildcard $(COMMON)/diag/*.asm) $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -I$(COMMON)/diag -o $@ $<

$(BUILD)/wboot.cim: src/wboot.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/nativecheck.cim: src/nativecheck.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/status.cim: src/status.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(NATIVE_TEST_VOLUME): third_party/cpm3/ccp.com $(BUILD)/diag.cim \
		$(BUILD)/wboot.cim $(BUILD)/status.cim $(BUILD)/nativecheck.cim \
		volume/README.txt volume/profiles/recovery.json \
		volume/profiles/native-recovery.json volume/profiles/native-test.json \
		tools/build_volume.py diskdefs | $(OUT)
	$(PYTHON) tools/build_volume.py --profile volume/profiles/native-test.json \
		--output $@

$(BUILD)/cpm3-utilities/manifest.json: \
		third_party/cpm3/releases/provenance.json \
		third_party/cpm3/releases/cpm3src_unix-20260607.zip \
		third_party/cpm3/releases/cpm3bin_unix-20260607.zip \
		tools/extract_cpm3_utilities.py | $(BUILD)
	$(PYTHON) tools/extract_cpm3_utilities.py

$(RECOVERY_VOLUME) $(RECOVERY_REPORT) &: third_party/cpm3/ccp.com \
		$(BUILD)/diag.cim $(BUILD)/wboot.cim volume/README.txt \
		volume/profiles/recovery.json tools/build_volume.py diskdefs | $(OUT)
	$(PYTHON) tools/build_volume.py --profile volume/profiles/recovery.json \
		--output $(RECOVERY_VOLUME) --report $(RECOVERY_REPORT)

$(VOLUME): $(RECOVERY_VOLUME) | $(OUT)
	cp $(RECOVERY_VOLUME) $@

$(NATIVE_RECOVERY_VOLUME) $(NATIVE_RECOVERY_REPORT) &: \
		third_party/cpm3/ccp.com $(BUILD)/diag.cim $(BUILD)/wboot.cim \
		$(BUILD)/status.cim volume/README.txt \
		volume/profiles/recovery.json volume/profiles/native-recovery.json \
		tools/build_volume.py diskdefs | $(OUT)
	$(PYTHON) tools/build_volume.py \
		--profile volume/profiles/native-recovery.json \
		--output $(NATIVE_RECOVERY_VOLUME) \
		--report $(NATIVE_RECOVERY_REPORT)

$(FULL_VOLUME) $(FULL_REPORT) &: third_party/cpm3/ccp.com \
		$(BUILD)/diag.cim $(BUILD)/wboot.cim $(BUILD)/status.cim volume/README.txt \
		$(BUILD)/cpm3-utilities/manifest.json volume/profiles/full.json \
		tools/build_volume.py diskdefs | $(OUT)
	$(PYTHON) tools/build_volume.py --profile volume/profiles/full.json \
		--output $(FULL_VOLUME) --report $(FULL_REPORT)

$(APPS_VOLUME) $(APPS_REPORT) &: $(BUILD)/diag.cim volume/APPS.txt \
		volume/profiles/apps.json tools/build_volume.py diskdefs | $(OUT)
	$(PYTHON) tools/build_volume.py --profile volume/profiles/apps.json \
		--output $(APPS_VOLUME) --report $(APPS_REPORT)

$(DEMO_VOLUME) $(DEMO_REPORT) &: third_party/cpm3/ccp.com \
		$(BUILD)/diag.cim $(BUILD)/wboot.cim $(BUILD)/status.cim volume/README.txt \
		volume/PROFILE.sub $(BUILD)/cpm3-utilities/manifest.json \
		volume/profiles/full.json volume/profiles/demo.json \
		tools/build_volume.py diskdefs | $(OUT)
	$(PYTHON) tools/build_volume.py --profile volume/profiles/demo.json \
		--output $(DEMO_VOLUME) --report $(DEMO_REPORT)

cpm3-toolchain: $(ZXCC)

cpm3-system-check: $(ZXCC)
	$(PYTHON) tools/regenerate_cpm3.py --check
	$(PYTHON) tools/regenerate_cpm3.py --check \
		--adapter-address 0xc000 --top-page 0xbf \
		--metadata-policy gencpm \
		--output third_party/cpm3/cpm3-network-rom.sys

native-services-check: $(NATIVE_ROM_SYSTEM) $(NATIVE_ROM_FASTBOOT) \
		$(NATIVE_TEST_VOLUME)
	$(PYTHON) tests/native_services_test.py
	CPM_PLUS_JUKU_ROM_SYSTEM=$(NATIVE_ROM_SYSTEM) \
	CPM_PLUS_JUKU_ROM_FASTBOOT=$(NATIVE_ROM_FASTBOOT) \
	CPM_PLUS_JUKU_VOLUME=$(NATIVE_TEST_VOLUME) \
	CPM_PLUS_JUKU_EXTRA_COMMAND=NATIVE \
	CPM_PLUS_JUKU_EXTRA_MARKER='NATIVE: PASS' \
	CPM_PLUS_JUKU_BOOT_PATH=network-smoke $(PYTHON) tests/cosim_check.py
	CPM_PLUS_JUKU_ROM_SYSTEM=$(NATIVE_ROM_SYSTEM) \
	CPM_PLUS_JUKU_ROM_FASTBOOT=$(NATIVE_ROM_FASTBOOT) \
	CPM_PLUS_JUKU_VOLUME=$(NATIVE_TEST_VOLUME) \
	CPM_PLUS_JUKU_EXTRA_COMMAND=STATUS \
	CPM_PLUS_JUKU_EXTRA_MARKER='Juku Status 1.0' \
	CPM_PLUS_JUKU_EXPECT_STATUS_REPORTS=1 \
	CPM_PLUS_JUKU_BOOT_PATH=network-smoke $(PYTHON) tests/cosim_check.py

regenerate-cpm3: $(ZXCC)
	$(PYTHON) tools/regenerate_cpm3.py

regenerate-cpm3-rom: $(ZXCC)
	$(PYTHON) tools/regenerate_cpm3.py --adapter-address 0xc000 \
		--top-page 0xbf --metadata-policy gencpm \
		--output third_party/cpm3/cpm3-network-rom.sys
