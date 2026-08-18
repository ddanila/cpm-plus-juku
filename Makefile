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
export JUKU_COMMON_ROOT := $(abspath $(COMMON))

SYSTEM := $(OUT)/cpm-plus-juku-system.bin
FASTBOOT := $(OUT)/cpm-plus-juku-fastboot-v15.bin
ROM_SYSTEM := $(OUT)/cpm-plus-juku-network-rom-system.bin
ROM_FASTBOOT := $(OUT)/cpm-plus-juku-network-rom-fastboot-v15.bin
NATIVE_ROM_SYS := $(BUILD)/cpm3-network-rom-native.sys
NATIVE_ROM_SYSTEM := $(OUT)/cpm-plus-juku-network-rom-native-system.bin
NATIVE_ROM_FASTBOOT := $(OUT)/cpm-plus-juku-network-rom-native-fastboot-v15.bin
LOCALE_NATIVE_ROM_SYSTEM := $(OUT)/cpm-plus-juku-network-rom-locale-native-system.bin
LOCALE_NATIVE_ROM_FASTBOOT := $(OUT)/cpm-plus-juku-network-rom-locale-native-fastboot-v15.bin
EXTENDED_NATIVE_ROM_SYSTEM := $(OUT)/cpm-plus-juku-network-rom-extended-native-system.bin
EXTENDED_NATIVE_ROM_FASTBOOT := $(OUT)/cpm-plus-juku-network-rom-extended-native-fastboot-v16.bin
NATIVE_TEST_VOLUME := $(OUT)/cpm-plus-juku-native-test.img
C4_DIAG := $(BUILD)/diag-c4.cim
NATIVE_RECOVERY_VOLUME := $(OUT)/cpm-plus-juku-native-recovery.img
VOLUME := $(OUT)/cpm-plus-juku.img
RECOVERY_VOLUME := $(OUT)/cpm-plus-juku-recovery.img
FULL_VOLUME := $(OUT)/cpm-plus-juku-full.img
DEV_VOLUME := $(OUT)/cpm-plus-juku-dev.img
APPS_VOLUME := $(OUT)/cpm-plus-juku-apps.juk
DEMO_VOLUME := $(OUT)/cpm-plus-juku-museum-demo.img
RECOVERY_REPORT := $(OUT)/cpm-plus-juku-recovery.report.json
NATIVE_RECOVERY_REPORT := $(OUT)/cpm-plus-juku-native-recovery.report.json
FULL_REPORT := $(OUT)/cpm-plus-juku-full.report.json
DEV_REPORT := $(OUT)/cpm-plus-juku-dev.report.json
APPS_REPORT := $(OUT)/cpm-plus-juku-apps.report.json
DEMO_REPORT := $(OUT)/cpm-plus-juku-museum-demo.report.json
DRI_FULL_RUNTIME_METRICS := $(BUILD)/cpm3-dri-full-runtime.json
DRI_DEV_RUNTIME_METRICS := $(BUILD)/cpm3-dri-dev-runtime.json
BOOT_MANIFEST := $(OUT)/cpm-plus-juku-native-manifest.json
C5_BOOT_MANIFEST := $(OUT)/cpm-plus-juku-c5-manifest.json
C5_ROM_DIR := ../8080-cosim/spinoffs/jukuravi/network-rom
C5_ROM := $(C5_ROM_DIR)/juku-network-rom-abi1.1-c5.bin
C5_ROM_METADATA := $(C5_ROM_DIR)/juku-network-rom-abi1.1-c5.json
C5_RELEASE := $(OUT)/cpm-plus-3.1-juku-c5-desk
C6_RELEASE := $(OUT)/cpm-plus-3.1-juku-c6-simulator
C6_BOOT_MANIFEST := $(OUT)/cpm-plus-juku-c6-manifest.json
C6_ROM := $(C5_ROM_DIR)/juku-network-rom-abi1.2-c6.bin
C6_ROM_METADATA := $(C5_ROM_DIR)/juku-network-rom-abi1.2-c6.json
C6_RECOVERY_VOLUME := $(OUT)/cpm-plus-juku-c6-recovery.img
C6_RECOVERY_REPORT := $(OUT)/cpm-plus-juku-c6-recovery.report.json

.PHONY: all check clean tools verify-prebuilt rom-budget-check \
	network-rom-cosim-check network-rom-soak-check \
	network-rom-long-soak-check bench-candidate \
	distribution distribution-check distribution-cosim-check \
	distribution-input-check utility-catalogue-check \
	development-tool-audit-check \
	compiler-comparison-check compiler-comparison-rebuild-check \
	external-software-audit-check external-software-rebuild-check \
	dev-utility-rebuild-check development-cosim-check \
	physical-acceptance-check vidtest-cosim-check \
	cpm3-toolchain cpm3-system-check native-services-check \
	manifest-check c5-manifest-check c6-manifest-check release-candidate \
	release-candidate-check c6-release-candidate c6-release-candidate-check \
	regenerate-cpm3 regenerate-cpm3-rom \
	network-rom-locale-cosim-check network-rom-extended-local-cosim-check \
	network-rom-extended-cosim-check \
	bootstrap-observability-check
all: $(SYSTEM) $(FASTBOOT) $(ROM_SYSTEM) $(ROM_FASTBOOT) $(VOLUME) \
	$(LOCALE_NATIVE_ROM_SYSTEM) $(LOCALE_NATIVE_ROM_FASTBOOT) \
	$(EXTENDED_NATIVE_ROM_SYSTEM) $(EXTENDED_NATIVE_ROM_FASTBOOT) \
	distribution $(BOOT_MANIFEST)

distribution: $(RECOVERY_VOLUME) $(RECOVERY_REPORT) \
	$(NATIVE_RECOVERY_VOLUME) $(NATIVE_RECOVERY_REPORT) \
	$(FULL_VOLUME) $(FULL_REPORT) $(DEV_VOLUME) $(DEV_REPORT) \
	$(APPS_VOLUME) $(APPS_REPORT) \
	$(DEMO_VOLUME) $(DEMO_REPORT)

tools: $(ZMAC) $(LD80) $(ZX0)

verify-prebuilt: all
	cmp $(SYSTEM) prebuilt/cpm-plus-juku-system.bin
	cmp $(FASTBOOT) prebuilt/cpm-plus-juku-fastboot-v15.bin
	cmp $(ROM_SYSTEM) prebuilt/cpm-plus-juku-network-rom-system.bin
	cmp $(ROM_FASTBOOT) prebuilt/cpm-plus-juku-network-rom-fastboot-v15.bin
	cmp $(VOLUME) prebuilt/cpm-plus-juku.img
	test "$$(sha256sum prebuilt/cpm-plus-juku-system.bin | cut -d' ' -f1)" = \
		254f940e36501dcf3f46c5ba23b2b6cb3b1b7f3a13b1e42ae9786f2fa337a4a4
	test "$$(sha256sum prebuilt/cpm-plus-juku-fastboot-v15.bin | cut -d' ' -f1)" = \
		881befd8ebd306ae7313b2dff8b83cb8d964988e17627d76efedaa49e6a19a5d
	test "$$(sha256sum prebuilt/cpm-plus-juku-c5-system.bin | cut -d' ' -f1)" = \
		86b36bd70156d10bafba332bd02e8756473c76bde3e9cc4a50fbc530bfb8a3f2
	test "$$(sha256sum prebuilt/cpm-plus-juku-c5-fastboot-v15.bin | cut -d' ' -f1)" = \
		4aaff8f9a78c289e96bb1699453d3136f7c2f6c82f3bfb2323d46145028178b0

rom-budget-check: tools $(BUILD)/fastboot-core.cim \
		$(BUILD)/fastboot-extension.cim $(BUILD)/fastboot-extension-rom-locale.cim \
		$(BUILD)/fastboot-core-v16.cim $(BUILD)/fastboot-extension-rom-v16.cim
	$(PYTHON) tools/rom_budget.py --check

check: verify-prebuilt rom-budget-check distribution-input-check \
	utility-catalogue-check dev-utility-rebuild-check \
	development-tool-audit-check \
	compiler-comparison-check external-software-audit-check \
	distribution-check manifest-check c5-manifest-check \
	c6-manifest-check c6-release-candidate-check \
	release-candidate-check cpm3-system-check native-services-check \
	distribution-cosim-check development-cosim-check \
	physical-acceptance-check vidtest-cosim-check \
	bootstrap-observability-check
	CPM_PLUS_JUKU_BOOT_PATH=all $(PYTHON) tests/cosim_check.py

distribution-input-check:
	$(PYTHON) tools/extract_cpm3_utilities.py --verify
	$(PYTHON) tools/extract_cpm3_utilities.py
	$(PYTHON) tools/extract_cpm3_utilities.py --check
	$(PYTHON) tests/cpm3_utility_inputs_test.py

utility-catalogue-check:
	$(PYTHON) tools/audit_cpm3_candidates.py --check
	$(PYTHON) tests/cpm3_candidate_audit_test.py
	$(PYTHON) tools/audit_cpm3_runtime.py --check
	$(PYTHON) tests/cpm3_runtime_audit_test.py

development-tool-audit-check:
	$(PYTHON) tools/audit_cpm3_development_tools.py --check
	$(PYTHON) tests/cpm3_development_tool_audit_test.py

physical-acceptance-check: $(C6_BOOT_MANIFEST)
	$(PYTHON) tests/physical_acceptance_test.py

vidtest-cosim-check: all $(BUILD)/vidtest.cim
	$(PYTHON) tools/vidtest_oracle.py
	$(PYTHON) tools/audit_8080_com.py $(BUILD)/vidtest.cim >/dev/null
	CPM_PLUS_JUKU_NETWORK_ROM=$(C6_ROM) \
	CPM_PLUS_JUKU_ROM_SYSTEM=$(EXTENDED_NATIVE_ROM_SYSTEM) \
	CPM_PLUS_JUKU_ROM_FASTBOOT=$(EXTENDED_NATIVE_ROM_FASTBOOT) \
	CPM_PLUS_JUKU_VOLUME=$(FULL_VOLUME) \
	CPM_PLUS_JUKU_S21_EXTRA=0x01 \
	CPM_PLUS_JUKU_EXTRA_COMMAND=VIDTEST \
	CPM_PLUS_JUKU_EXTRA_READY_MARKER='VIDTEST READY' \
	CPM_PLUS_JUKU_EXTRA_INPUT_HEX=0d \
	CPM_PLUS_JUKU_EXTRA_MARKER='Juku Vidtest 1.0 DONE' \
	CPM_PLUS_JUKU_CAPTURE_VIDTEST=1 \
	CPM_PLUS_JUKU_READ_AHEAD_RECORDS=8 \
	CPM_PLUS_JUKU_EXPECT_BOOT_STAGE=0x50 \
	CPM_PLUS_JUKU_EXPECT_BOOT_PROTOCOL=16 \
	CPM_PLUS_JUKU_EXPECT_BOOT_ABI_MINOR=2 \
	CPM_PLUS_JUKU_EXPECT_CAPABILITY_QUERIES=1 \
	CPM_PLUS_JUKU_EXPECT_DIAG_REPORTS=1 \
	CPM_PLUS_JUKU_BOOT_PATH=vidtest $(PYTHON) tests/cosim_check.py

compiler-comparison-check:
	$(PYTHON) tests/audit_8080_com_test.py
	$(PYTHON) tools/compiler_comparison.py
	$(PYTHON) tests/compiler_comparison_test.py

compiler-comparison-rebuild-check:
	@test -n "$(MILLFORK)" -a -n "$(Z88DK_ROOT)" || \
		{ echo 'set MILLFORK and Z88DK_ROOT'; exit 2; }
	$(PYTHON) tools/compiler_comparison.py --millfork "$(MILLFORK)" \
		--z88dk-root "$(Z88DK_ROOT)" --strict-cosim

external-software-audit-check:
	$(PYTHON) tools/external_software_audit.py --check
	$(PYTHON) tests/external_software_audit_test.py

external-software-rebuild-check: $(ZMAC)
	@test -n "$(CPM_LS_TREE)" -a -n "$(Z88DK_ROOT)" \
		-a -n "$(FIG_FORTH_SOURCE)" || \
		{ echo 'set CPM_LS_TREE, Z88DK_ROOT, and FIG_FORTH_SOURCE'; exit 2; }
	$(PYTHON) tools/external_software_audit.py --check \
		--cpm-ls-tree "$(CPM_LS_TREE)" --z88dk-root "$(Z88DK_ROOT)" \
		--fig-source "$(FIG_FORTH_SOURCE)" --zmac "$(abspath $(ZMAC))"

dev-utility-rebuild-check: $(ZXCC)
	$(PYTHON) tools/rebuild_cpm3_dev_utilities.py

distribution-check: distribution
	$(PYTHON) tests/distribution_test.py

distribution-cosim-check: all
	CPM_PLUS_JUKU_NETWORK_ROM=$(C6_ROM) \
	CPM_PLUS_JUKU_ROM_SYSTEM=$(EXTENDED_NATIVE_ROM_SYSTEM) \
	CPM_PLUS_JUKU_ROM_FASTBOOT=$(EXTENDED_NATIVE_ROM_FASTBOOT) \
	CPM_PLUS_JUKU_VOLUME=$(DEMO_VOLUME) \
	CPM_PLUS_JUKU_DRIVE_B=$(APPS_VOLUME) \
	CPM_PLUS_JUKU_S21_EXTRA=0x01 \
	CPM_PLUS_JUKU_EXPECT_PROFILE='A>DIR' \
	CPM_PLUS_JUKU_EXPECT_PROFILE_OUTPUT=DIAG \
	CPM_PLUS_JUKU_EXTRA_COMMAND=SETDEF \
	CPM_PLUS_JUKU_EXTRA_MARKER='Drive Search Path' \
	CPM_PLUS_JUKU_EXTRA_COMMAND2='DUMP PROFILE.SUB' \
	CPM_PLUS_JUKU_EXTRA_MARKER2=0000 \
	CPM_PLUS_JUKU_EXTRA_MARKERS2='44 49 52' \
	CPM_PLUS_JUKU_EXTRA_COMMAND3='HELP DUMP' \
	CPM_PLUS_JUKU_EXTRA_MARKER3='DUMP displays' \
	CPM_PLUS_JUKU_EXTRA_READY_MARKER3='HELP>' \
	CPM_PLUS_JUKU_EXTRA_INPUT_HEX3=0d \
	CPM_PLUS_JUKU_EXTRA_COMMAND4='PIP COPY.TXT=README.TXT' \
	CPM_PLUS_JUKU_EXTRA_COMMAND5='CRC COPY.TXT' \
	CPM_PLUS_JUKU_EXTRA_MARKER5='CRC16-CCITT: 4613  records: 0004' \
	CPM_PLUS_JUKU_EXTRA_COMMAND6='SHOW A:[SPACE]' \
	CPM_PLUS_JUKU_EXTRA_MARKER6='Space:' \
	CPM_PLUS_JUKU_EXTRA_COMMAND7='SET COPY.TXT [RO]' \
	CPM_PLUS_JUKU_EXTRA_MARKER7='Read Only' \
	CPM_PLUS_JUKU_EXTRA_COMMAND8='SET COPY.TXT [RW]' \
	CPM_PLUS_JUKU_EXTRA_MARKER8='Read Write' \
	CPM_PLUS_JUKU_EXTRA_COMMAND9='DATE BAD' \
	CPM_PLUS_JUKU_EXTRA_MARKER9='Illegal time/date specification' \
	CPM_PLUS_JUKU_EXTRA_COMMAND10='SUBMIT MISSING' \
	CPM_PLUS_JUKU_EXTRA_MARKER10="No 'SUB' File Found" \
	CPM_PLUS_JUKU_EXTRA_COMMAND11='CRC README.TXT' \
	CPM_PLUS_JUKU_EXTRA_MARKER11='CRC16-CCITT: 4613  records: 0004' \
	CPM_PLUS_JUKU_EXTRA_COMMAND12='CMP CRC.COM CRC.COM' \
	CPM_PLUS_JUKU_EXTRA_MARKER12='files are identical' \
	CPM_PLUS_JUKU_EXTRA_COMMAND13='CMP CRC.COM README.TXT' \
	CPM_PLUS_JUKU_EXTRA_MARKER13='difference at record 0000 offset 00' \
	CPM_PLUS_JUKU_EXTRA_COMMAND14='MEM 0100 10' \
	CPM_PLUS_JUKU_EXTRA_MARKER14='0100: 11 82 02 CD 5A 02 3A 80 00 47 21 81 00 CD FE 01' \
	CPM_PLUS_JUKU_EXTRA_COMMAND15='WC README.TXT' \
	CPM_PLUS_JUKU_EXTRA_MARKER15='WC (hex): lines 000014  words 00003B  bytes 0001FA' \
	CPM_PLUS_JUKU_EXTRA_COMMAND16='FIND README.TXT Juku' \
	CPM_PLUS_JUKU_EXTRA_MARKER16='FIND: 04' \
	CPM_PLUS_JUKU_EXTRA_MARKERS16='host-backed NetDisk-v3|Shared non-destructive Juku diagnostics|Project: https://github.com/ddanila/cpm-plus-juku' \
	CPM_PLUS_JUKU_EXTRA_COMMAND17='STRINGS README.TXT' \
	CPM_PLUS_JUKU_EXTRA_MARKER17='host-backed NetDisk-v3' \
	CPM_PLUS_JUKU_EXTRA_COMMAND18='DEVICE NAMES' \
	CPM_PLUS_JUKU_EXTRA_MARKER18='Physical Devices:' \
	CPM_PLUS_JUKU_EXTRA_MARKERS18='JUKU|IO' \
	CPM_PLUS_JUKU_EXTRA_COMMAND19='PIP COPY2.TXT=README.TXT' \
	CPM_PLUS_JUKU_EXTRA_COMMAND20='CRC COPY2.TXT' \
	CPM_PLUS_JUKU_EXTRA_MARKER20='CRC16-CCITT: 4613  records: 0004' \
	CPM_PLUS_JUKU_CAPTURE_EXTRA_STACK=1 \
	CPM_PLUS_JUKU_CAPTURE_EXTRA_STACK_METRICS='extra,extra2,extra3,extra4,extra6,extra7,extra9,extra10,extra18' \
	CPM_PLUS_JUKU_METRICS_OUTPUT=$(DRI_FULL_RUNTIME_METRICS) \
	CPM_PLUS_JUKU_EXPECT_STRICT_TPA_OPCODES=1 \
	CPM_PLUS_JUKU_EXPECT_PER_DRIVE_CACHE=1 \
	CPM_PLUS_JUKU_READ_AHEAD_RECORDS=8 \
	CPM_PLUS_JUKU_EXPECT_BOOT_STAGE=0x50 \
	CPM_PLUS_JUKU_EXPECT_BOOT_PROTOCOL=16 \
	CPM_PLUS_JUKU_EXPECT_BOOT_ABI_MINOR=2 \
	CPM_PLUS_JUKU_EXPECT_CAPABILITY_QUERIES=1 \
	CPM_PLUS_JUKU_EXPECT_DIAG_REPORTS=3 \
	CPM_PLUS_JUKU_BOOT_PATH=network-smoke $(PYTHON) tests/cosim_check.py
	$(PYTHON) tools/audit_cpm3_runtime.py --check --profile full \
		--metrics $(DRI_FULL_RUNTIME_METRICS) --volume-report $(DEMO_REPORT)

development-cosim-check: all
	CPM_PLUS_JUKU_NETWORK_ROM=$(C6_ROM) \
	CPM_PLUS_JUKU_ROM_SYSTEM=$(EXTENDED_NATIVE_ROM_SYSTEM) \
	CPM_PLUS_JUKU_ROM_FASTBOOT=$(EXTENDED_NATIVE_ROM_FASTBOOT) \
	CPM_PLUS_JUKU_VOLUME=$(DEV_VOLUME) \
	CPM_PLUS_JUKU_S21_EXTRA=0x01 \
	CPM_PLUS_JUKU_EXTRA_COMMAND='HEXCOM HELLO' \
	CPM_PLUS_JUKU_EXTRA_COMMAND2=HELLO \
	CPM_PLUS_JUKU_EXTRA_MARKER2='Juku dev profile' \
	CPM_PLUS_JUKU_EXTRA_COMMAND3='SID HELLO.COM' \
	CPM_PLUS_JUKU_EXTRA_READY_MARKER3='#' \
	CPM_PLUS_JUKU_EXTRA_INPUT_HEX3='51 0d' \
	CPM_PLUS_JUKU_EXTRA_MARKER3='#' \
	CPM_PLUS_JUKU_EXTRA_COMMAND4='PATCH SID' \
	CPM_PLUS_JUKU_EXTRA_MARKER4='Current patches for' \
	CPM_PLUS_JUKU_EXTRA_COMMAND5='ED EDTEST.TXT' \
	CPM_PLUS_JUKU_EXTRA_INPUT_SCRIPT5='[{"wait":": *","hex":"49456469746564206f6e204a756b752043502f4d20506c757320332e311a0d","delay":1},{"wait":"\r\n*","hex":"450d","delay":1}]' \
	CPM_PLUS_JUKU_EXTRA_MARKER5='NEW FILE' \
	CPM_PLUS_JUKU_EXTRA_COMMAND6='TYPE EDTEST.TXT' \
	CPM_PLUS_JUKU_EXTRA_MARKER6='EDITED ON JUKU CP/M PLUS 3.1' \
	CPM_PLUS_JUKU_CAPTURE_EXTRA_STACK=1 \
	CPM_PLUS_JUKU_CAPTURE_EXTRA_STACK_METRICS='extra,extra3,extra4,extra5' \
	CPM_PLUS_JUKU_METRICS_OUTPUT=$(DRI_DEV_RUNTIME_METRICS) \
	CPM_PLUS_JUKU_EXPECT_STRICT_TPA_OPCODES=1 \
	CPM_PLUS_JUKU_READ_AHEAD_RECORDS=8 \
	CPM_PLUS_JUKU_EXPECT_BOOT_STAGE=0x50 \
	CPM_PLUS_JUKU_EXPECT_BOOT_PROTOCOL=16 \
	CPM_PLUS_JUKU_EXPECT_BOOT_ABI_MINOR=2 \
	CPM_PLUS_JUKU_EXPECT_CAPABILITY_QUERIES=1 \
	CPM_PLUS_JUKU_EXPECT_DIAG_REPORTS=1 \
	CPM_PLUS_JUKU_BOOT_PATH=network-smoke $(PYTHON) tests/cosim_check.py
	$(PYTHON) tools/audit_cpm3_runtime.py --check --profile dev \
		--metrics $(DRI_DEV_RUNTIME_METRICS) --volume-report $(DEV_REPORT)

manifest-check: $(BOOT_MANIFEST)
	$(PYTHON) tests/boot_manifest_test.py

c5-manifest-check: $(C5_BOOT_MANIFEST)
	$(PYTHON) tests/c5_boot_manifest_test.py

c6-manifest-check: $(C6_BOOT_MANIFEST)
	$(PYTHON) tests/c6_boot_manifest_test.py

release-candidate: check
	$(PYTHON) tools/package_release_candidate.py --output $(C5_RELEASE)

release-candidate-check: $(C5_BOOT_MANIFEST)
	$(PYTHON) tests/release_candidate_test.py

c6-release-candidate:
	$(PYTHON) ../8080-cosim/spinoffs/jukuravi/network-rom/build_network_rom.py
	../8080-cosim/sync/network_first_rom_abi_check.sh
	../8080-cosim/sync/network_first_rom_hdl_check.sh
	$(MAKE) c6-manifest-check
	$(MAKE) network-rom-extended-cosim-check
	$(MAKE) network-rom-long-soak-check
	$(PYTHON) tools/package_release_candidate.py --variant c6 --output $(C6_RELEASE)
	$(PYTHON) tests/c6_release_candidate_test.py

c6-release-candidate-check: $(C6_BOOT_MANIFEST)
	$(PYTHON) tests/c6_release_candidate_test.py

network-rom-cosim-check: all
	CPM_PLUS_JUKU_BOOT_PATH=network $(PYTHON) tests/cosim_check.py

network-rom-locale-cosim-check: all
	CPM_PLUS_JUKU_BOOT_PATH=network-smoke CPM_PLUS_JUKU_NETWORK_ROM=\
	../8080-cosim/spinoffs/jukuravi/network-rom/juku-network-rom-abi1.1-c5.bin \
	CPM_PLUS_JUKU_ROM_SYSTEM=$(LOCALE_NATIVE_ROM_SYSTEM) \
	CPM_PLUS_JUKU_ROM_FASTBOOT=$(LOCALE_NATIVE_ROM_FASTBOOT) \
	CPM_PLUS_JUKU_VOLUME=$(NATIVE_RECOVERY_VOLUME) \
	CPM_PLUS_JUKU_DRIVE_B=$(APPS_VOLUME) \
	CPM_PLUS_JUKU_S21_EXTRA=0x09 CPM_PLUS_JUKU_EXTRA_COMMAND=STATUS \
	CPM_PLUS_JUKU_EXTRA_MARKER='Locale: Estonian' \
	CPM_PLUS_JUKU_EXPECT_PER_DRIVE_CACHE=1 \
	CPM_PLUS_JUKU_READ_AHEAD_RECORDS=8 \
	CPM_PLUS_JUKU_EXPECT_BOOT_READS=10 \
	CPM_PLUS_JUKU_EXPECT_DIR_READS=0 \
	CPM_PLUS_JUKU_EXPECT_TYPE_READS=1 \
	CPM_PLUS_JUKU_EXPECT_STATUS_REPORTS=1 \
	CPM_PLUS_JUKU_EXPECT_BOOT_REPORTS=1 \
	CPM_PLUS_JUKU_EXPECT_BOOT_STAGE=0x50 \
	CPM_PLUS_JUKU_EXPECT_BOOT_PROTOCOL=15 \
	CPM_PLUS_JUKU_EXPECT_BOOT_ABI_MINOR=1 \
	CPM_PLUS_JUKU_EXPECT_DIAG_REPORTS=3 \
	CPM_PLUS_JUKU_EXPECT_CAPABILITY_QUERIES=2 \
	$(PYTHON) tests/cosim_check.py

network-rom-extended-local-cosim-check: all
	CPM_PLUS_JUKU_BOOT_PATH=network-smoke CPM_PLUS_JUKU_NETWORK_ROM=\
	../8080-cosim/spinoffs/jukuravi/network-rom/juku-network-rom-abi1.2-c6.bin \
	CPM_PLUS_JUKU_BOOT_HOST_DELAY=2 \
	CPM_PLUS_JUKU_DISCARD_BOOT_READY=1 \
	CPM_PLUS_JUKU_EXPECT_AUTO_READY_SEEN=0 \
	CPM_PLUS_JUKU_ROM_SYSTEM=$(EXTENDED_NATIVE_ROM_SYSTEM) \
	CPM_PLUS_JUKU_ROM_FASTBOOT=$(EXTENDED_NATIVE_ROM_FASTBOOT) \
	CPM_PLUS_JUKU_VOLUME=$(C6_RECOVERY_VOLUME) \
	CPM_PLUS_JUKU_DRIVE_B=$(APPS_VOLUME) \
	CPM_PLUS_JUKU_S21_EXTRA=0x09 CPM_PLUS_JUKU_EXTRA_COMMAND=STATUS \
	CPM_PLUS_JUKU_EXTRA_MARKER='Locale: Estonian' \
	CPM_PLUS_JUKU_EXTRA_COMMAND2='DIR KEYRAW.COM' \
	CPM_PLUS_JUKU_EXTRA_MARKER2='KEYRAW.COM' \
	CPM_PLUS_JUKU_EXPECT_PER_DRIVE_CACHE=1 \
	CPM_PLUS_JUKU_READ_AHEAD_RECORDS=8 \
	CPM_PLUS_JUKU_EXPECT_BOOT_READS=10 \
	CPM_PLUS_JUKU_EXPECT_DIR_READS=0 \
	CPM_PLUS_JUKU_EXPECT_TYPE_READS=1 \
	CPM_PLUS_JUKU_EXPECT_STATUS_REPORTS=1 \
	CPM_PLUS_JUKU_EXPECT_BOOT_REPORTS=1 \
	CPM_PLUS_JUKU_EXPECT_BOOT_STAGE=0x50 \
	CPM_PLUS_JUKU_EXPECT_BOOT_PROTOCOL=16 \
	CPM_PLUS_JUKU_EXPECT_BOOT_ABI_MINOR=2 \
	CPM_PLUS_JUKU_EXPECT_DIAG_REPORTS=3 \
	CPM_PLUS_JUKU_EXPECT_CAPABILITY_QUERIES=2 \
	$(PYTHON) tests/cosim_check.py

network-rom-extended-cosim-check: network-rom-extended-local-cosim-check
	CPM_PLUS_JUKU_BOOT_PATH=network-remote CPM_PLUS_JUKU_NETWORK_ROM=\
	../8080-cosim/spinoffs/jukuravi/network-rom/juku-network-rom-abi1.2-c6.bin \
	CPM_PLUS_JUKU_ROM_SYSTEM=$(EXTENDED_NATIVE_ROM_SYSTEM) \
	CPM_PLUS_JUKU_ROM_FASTBOOT=$(EXTENDED_NATIVE_ROM_FASTBOOT) \
	CPM_PLUS_JUKU_VOLUME=$(C6_RECOVERY_VOLUME) \
	CPM_PLUS_JUKU_DRIVE_B=$(APPS_VOLUME) \
	CPM_PLUS_JUKU_S21_EXTRA=0x09 CPM_PLUS_JUKU_EXTRA_COMMAND=STATUS \
	CPM_PLUS_JUKU_EXTRA_MARKER='Locale: Estonian' \
	CPM_PLUS_JUKU_EXTRA_COMMAND2='DIR KEYRAW.COM' \
	CPM_PLUS_JUKU_EXTRA_MARKER2='KEYRAW.COM' \
	CPM_PLUS_JUKU_EXTRA_COMMAND3=N4BULK \
	CPM_PLUS_JUKU_EXTRA_MARKER3='N4 BULK PASS' \
	CPM_PLUS_JUKU_EXPECT_CONSOLE_BULK=1 \
	CPM_PLUS_JUKU_EXPECT_PER_DRIVE_CACHE=1 \
	CPM_PLUS_JUKU_READ_AHEAD_RECORDS=8 \
	CPM_PLUS_JUKU_EXPECT_BOOT_READS=10 \
	CPM_PLUS_JUKU_EXPECT_DIR_READS=0 \
	CPM_PLUS_JUKU_EXPECT_TYPE_READS=1 \
	CPM_PLUS_JUKU_EXPECT_STATUS_REPORTS=1 \
	CPM_PLUS_JUKU_EXPECT_BOOT_REPORTS=1 \
	CPM_PLUS_JUKU_EXPECT_BOOT_STAGE=0x50 \
	CPM_PLUS_JUKU_EXPECT_BOOT_PROTOCOL=16 \
	CPM_PLUS_JUKU_EXPECT_BOOT_ABI_MINOR=2 \
	CPM_PLUS_JUKU_EXPECT_DIAG_REPORTS=3 \
	CPM_PLUS_JUKU_EXPECT_CAPABILITY_QUERIES=2 \
	$(PYTHON) tests/cosim_check.py

bootstrap-observability-check: all
	CPM_PLUS_JUKU_BOOT_PATH=network-smoke CPM_PLUS_JUKU_NETWORK_ROM=\
	../8080-cosim/spinoffs/jukuravi/network-rom/juku-network-rom-abi1.1-c5.bin \
	CPM_PLUS_JUKU_ROM_SYSTEM=$(LOCALE_NATIVE_ROM_SYSTEM) \
	CPM_PLUS_JUKU_ROM_FASTBOOT=$(LOCALE_NATIVE_ROM_FASTBOOT) \
	CPM_PLUS_JUKU_VOLUME=$(NATIVE_RECOVERY_VOLUME) \
	CPM_PLUS_JUKU_DRIVE_B=$(APPS_VOLUME) \
	CPM_PLUS_JUKU_S21_EXTRA=0x09 CPM_PLUS_JUKU_EXTRA_COMMAND=STATUS \
	CPM_PLUS_JUKU_EXTRA_MARKER='Bootstrap stage: 50' \
	CPM_PLUS_JUKU_EXPECT_PER_DRIVE_CACHE=1 \
	CPM_PLUS_JUKU_READ_AHEAD_RECORDS=8 \
	CPM_PLUS_JUKU_EXPECT_BOOT_READS=10 \
	CPM_PLUS_JUKU_EXPECT_DIR_READS=0 \
	CPM_PLUS_JUKU_EXPECT_TYPE_READS=1 \
	CPM_PLUS_JUKU_EXPECT_STATUS_REPORTS=1 \
	CPM_PLUS_JUKU_EXPECT_BOOT_REPORTS=1 \
	CPM_PLUS_JUKU_EXPECT_BOOT_STAGE=0x50 \
	CPM_PLUS_JUKU_EXPECT_BOOT_RETRIES=1 \
	CPM_PLUS_JUKU_EXPECT_BOOT_PROTOCOL=15 \
	CPM_PLUS_JUKU_EXPECT_BOOT_ABI_MINOR=1 \
	CPM_PLUS_JUKU_EXPECT_DIAG_REPORTS=3 \
	CPM_PLUS_JUKU_EXPECT_CAPABILITY_QUERIES=2 \
	CPM_PLUS_JUKU_CORRUPT_FASTBOOT_ONCE=1 \
	$(PYTHON) tests/cosim_check.py

network-rom-soak-check: all
	CPM_PLUS_JUKU_BOOT_PATH=network \
	CPM_PLUS_JUKU_SOAK_CYCLES=16 CPM_PLUS_JUKU_REALTIME_HZ=20000000 \
	$(PYTHON) tests/cosim_check.py

network-rom-long-soak-check: all $(C6_RECOVERY_VOLUME)
	CPM_PLUS_JUKU_BOOT_PATH=network-soak \
	CPM_PLUS_JUKU_NETWORK_ROM=$(C6_ROM) \
	CPM_PLUS_JUKU_ROM_SYSTEM=$(EXTENDED_NATIVE_ROM_SYSTEM) \
	CPM_PLUS_JUKU_ROM_FASTBOOT=$(EXTENDED_NATIVE_ROM_FASTBOOT) \
	CPM_PLUS_JUKU_VOLUME=$(C6_RECOVERY_VOLUME) \
	CPM_PLUS_JUKU_DRIVE_B=$(APPS_VOLUME) \
	CPM_PLUS_JUKU_S21_EXTRA=0x01 \
	CPM_PLUS_JUKU_READ_AHEAD_RECORDS=8 \
	CPM_PLUS_JUKU_SOAK_CYCLES=64 CPM_PLUS_JUKU_SOAK_WRITES=1 \
	CPM_PLUS_JUKU_EXPECT_DIAG_REPORTS=66 \
	CPM_PLUS_JUKU_EXPECT_CAPABILITY_QUERIES=1 \
	CPM_PLUS_JUKU_REALTIME_HZ=20000000 \
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
		$(COMMON)/platform/creep-console-font.asm \
		$(COMMON)/platform/locale-console-fonts.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 \
		-I$(COMMON)/platform -o $@ $<

$(BUILD)/platform-adapter-romabi.rel: src/platform-adapter.asm \
		$(COMMON)/platform/rom-abi.inc $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -DROMABI \
		-I$(COMMON)/platform -o $@ $<

$(BUILD)/platform-adapter-romabi-native.rel: src/platform-adapter.asm \
		$(COMMON)/platform/rom-abi.inc $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -DROMABI -DNATIVE_SERVICES \
		-DNATIVE_SERVICES_EXTRNS -DNATIVE_SERVICES_VECTORS \
		-DNATIVE_SERVICES_BOOT -DNATIVE_SERVICES_DISK \
		-I$(COMMON)/platform -o $@ $<

$(BUILD)/platform-adapter-romabi-locale-native.rel: src/platform-adapter.asm \
		$(COMMON)/platform/rom-abi.inc $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -DROMABI -DROM_ABI_LOCALE \
		-DNATIVE_SERVICES -DNATIVE_SERVICES_EXTRNS \
		-DNATIVE_SERVICES_VECTORS -DNATIVE_SERVICES_BOOT \
		-DNATIVE_SERVICES_DISK -I$(COMMON)/platform -o $@ $<

$(BUILD)/platform-adapter-romabi-extended-native.rel: src/platform-adapter.asm \
		$(COMMON)/platform/rom-abi.inc $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -DROMABI -DROM_ABI_LOCALE \
		-DROM_ABI_EXTENDED -DNATIVE_SERVICES -DNATIVE_SERVICES_EXTRNS \
		-DNATIVE_SERVICES_VECTORS -DNATIVE_SERVICES_BOOT \
		-DNATIVE_SERVICES_DISK -I$(COMMON)/platform -o $@ $<

$(BUILD)/cpm3-native-services.rel: src/cpm3-native-services.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -o $@ $<

$(BUILD)/cpm3-native-services-locale.rel: src/cpm3-native-services.asm \
		$(COMMON)/platform/rom-abi.inc $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -DROM_ABI_LOCALE \
		-I$(COMMON)/platform -o $@ $<

$(BUILD)/cpm3-native-services-extended.rel: src/cpm3-native-services.asm \
		$(COMMON)/platform/rom-abi.inc $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -DROM_ABI_LOCALE \
		-DROM_ABI_EXTENDED -I$(COMMON)/platform -o $@ $<

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

$(BUILD)/netconsole-romabi-extended-native.rel: \
		$(COMMON)/platform/netconsole.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -DNETCONSOLE_EAGER_POLL \
		-DNATIVE_SERVICES -DNETCONSOLE_BULK -o $@ $<

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
		-P0xc2a0 $(BUILD)/netconsole-romabi-native.rel \
		-P0xca00 $(BUILD)/cpm3-native-services.rel

$(BUILD)/adapter-romabi-native.bin: $(BUILD)/adapter-romabi-native.all
	tail -c+49153 $< >$@
	test $$(stat -c %s $@) -le 4096

$(BUILD)/adapter-romabi-locale-native.all: \
		$(BUILD)/platform-adapter-romabi-locale-native.rel \
		$(BUILD)/netconsole-romabi-native.rel \
		$(BUILD)/cpm3-native-services-locale.rel $(LD80)
	$(LD80) -m -O bin -o $@ -s /dev/null \
		-P0xc000 $(BUILD)/platform-adapter-romabi-locale-native.rel \
		-P0xc2a0 $(BUILD)/netconsole-romabi-native.rel \
		-P0xca00 $(BUILD)/cpm3-native-services-locale.rel

$(BUILD)/adapter-romabi-locale-native.bin: \
		$(BUILD)/adapter-romabi-locale-native.all
	tail -c+49153 $< >$@
	test $$(stat -c %s $@) -le 4096

$(BUILD)/adapter-romabi-extended-native.all: \
		$(BUILD)/platform-adapter-romabi-extended-native.rel \
		$(BUILD)/netconsole-romabi-extended-native.rel \
		$(BUILD)/cpm3-native-services-extended.rel $(LD80)
	$(LD80) -m -O bin -o $@ -s /dev/null \
		-P0xc000 $(BUILD)/platform-adapter-romabi-extended-native.rel \
		-P0xc2a0 $(BUILD)/netconsole-romabi-extended-native.rel \
		-P0xca00 $(BUILD)/cpm3-native-services-extended.rel

$(BUILD)/adapter-romabi-extended-native.bin: \
		$(BUILD)/adapter-romabi-extended-native.all
	tail -c+49153 $< >$@
	test $$(stat -c %s $@) -le 4096

# The stock-ROM/RAM-BIOS C4 baseline is immutable. Its exact source boundary
# is cpm-plus-juku 6ce52d8 plus juku-common aeee23d; later common font and
# keyboard growth must not silently relink that physical recovery artifact.
$(SYSTEM): prebuilt/cpm-plus-juku-system.bin | $(OUT)
	cp $< $@

$(ROM_SYSTEM): prebuilt/cpm-plus-juku-network-rom-system.bin | $(OUT)
	cp $< $@

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

# C5 is also a physically qualified immutable pair. Rebuild experiments use a
# new artifact name; the C5 manifest always consumes these pinned bytes.
$(LOCALE_NATIVE_ROM_SYSTEM): prebuilt/cpm-plus-juku-c5-system.bin | $(OUT)
	cp $< $@

$(EXTENDED_NATIVE_ROM_SYSTEM): $(BUILD)/adapter-romabi-extended-native.bin \
		$(NATIVE_ROM_SYS) tools/mksystem3.py | $(OUT)
	$(PYTHON) tools/mksystem3.py $(BUILD)/adapter-romabi-extended-native.bin \
		$(NATIVE_ROM_SYS) $@ --load-address 0x9000 \
		--adapter-address 0xc000 --entry-address 0xbc00 \
		--end-address 0xd600

FASTBOOT_CORE_DEFS := FASTBOOT_8N1 FASTBOOT_ZX0 FASTBOOT_STREAM \
	FASTBOOT_V15 FASTBOOT_EXACT FASTBOOT_EXT_ACK FASTBOOT_PROBE_SYNC
FASTBOOT_EXTENSION_DEFS := FASTBOOT_8N1 FASTBOOT_ZX0 FASTBOOT_TIGHT \
	FASTBOOT_V15 FASTBOOT_STREAM_ACK FASTBOOT_CPM3
FASTBOOT_CORE_V16_DEFS := FASTBOOT_8N1 FASTBOOT_ZX0 FASTBOOT_STREAM \
	FASTBOOT_V16 FASTBOOT_EXACT FASTBOOT_EXT_ACK FASTBOOT_PROBE_SYNC \
	FASTBOOT_ROM_EXTENSION
FASTBOOT_EXTENSION_V16_DEFS := FASTBOOT_8N1 FASTBOOT_ZX0 FASTBOOT_STREAM \
	FASTBOOT_V16 FASTBOOT_STREAM_ACK FASTBOOT_CPM3 FASTBOOT_CPM3_ROM \
	FASTBOOT_BOOT_RECORD

$(BUILD)/fastboot-core.cim: $(COMMON)/transport/fastboot-core.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 \
		$(addprefix -D,$(FASTBOOT_CORE_DEFS)) -o $@ $<

$(BUILD)/fastboot-core-v16.cim: \
		$(COMMON)/transport/fastboot-core.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 \
		$(addprefix -D,$(FASTBOOT_CORE_V16_DEFS)) -o $@ $<

$(BUILD)/fastboot-extension.cim: \
		$(COMMON)/transport/fastboot-extension.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 \
		$(addprefix -D,$(FASTBOOT_EXTENSION_DEFS)) -o $@ $<

$(BUILD)/fastboot-extension-rom.cim: \
		$(COMMON)/transport/fastboot-extension.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 \
		$(addprefix -D,$(FASTBOOT_EXTENSION_DEFS) FASTBOOT_CPM3_ROM) \
		-o $@ $<

$(BUILD)/fastboot-extension-rom-locale.cim: \
		$(COMMON)/transport/fastboot-extension.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 \
		$(addprefix -D,$(FASTBOOT_EXTENSION_DEFS) FASTBOOT_CPM3_ROM \
		FASTBOOT_BOOT_RECORD) -o $@ $<

$(BUILD)/fastboot-extension-rom-v16.cim: \
		$(COMMON)/transport/fastboot-extension.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 \
		$(addprefix -D,$(FASTBOOT_EXTENSION_V16_DEFS)) -o $@ $<

$(FASTBOOT): prebuilt/cpm-plus-juku-fastboot-v15.bin | $(OUT)
	cp $< $@

$(ROM_FASTBOOT): prebuilt/cpm-plus-juku-network-rom-fastboot-v15.bin | $(OUT)
	cp $< $@

$(NATIVE_ROM_FASTBOOT): $(BUILD)/fastboot-core.cim \
		$(BUILD)/fastboot-extension-rom.cim $(NATIVE_ROM_SYSTEM) $(ZX0) \
		tools/build_fastboot.py | $(OUT)
	$(PYTHON) tools/build_fastboot.py $(BUILD)/fastboot-core.cim \
		$(BUILD)/fastboot-extension-rom.cim $(NATIVE_ROM_SYSTEM) $(ZX0) $@

$(LOCALE_NATIVE_ROM_FASTBOOT): \
		prebuilt/cpm-plus-juku-c5-fastboot-v15.bin | $(OUT)
	cp $< $@

$(EXTENDED_NATIVE_ROM_FASTBOOT): $(BUILD)/fastboot-core-v16.cim \
		$(BUILD)/fastboot-extension-rom-v16.cim \
		$(EXTENDED_NATIVE_ROM_SYSTEM) $(ZX0) \
		tools/build_fastboot.py | $(OUT)
	$(PYTHON) tools/build_fastboot.py $(BUILD)/fastboot-core-v16.cim \
		$(BUILD)/fastboot-extension-rom-v16.cim \
		$(EXTENDED_NATIVE_ROM_SYSTEM) $(ZX0) $@

$(BUILD)/diag.cim: src/diag.asm $(wildcard $(COMMON)/diag/*.asm) $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -I$(COMMON)/diag -o $@ $<

$(C4_DIAG): prebuilt/cpm-plus-juku.img diskdefs | $(BUILD)
	DISKDEFS=$(abspath diskdefs) cpmcp -f juku386 $< 0:DIAG.COM $@
	test "$$(sha256sum $@ | cut -d' ' -f1)" = \
		7603115ef94bf7b6792f80cb87cc71916970af08c34227cfe2368c8e88331110

$(BUILD)/wboot.cim: src/wboot.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/wboot-user.cim: src/wboot-user.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/nativecheck.cim: src/nativecheck.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/status.cim: src/status.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/crc.cim: src/crc.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/cmp.cim: src/cmp.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/mem.cim: src/mem.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/wc.cim: src/wc.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/find.cim: src/find.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/strings.cim: src/strings.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/keytest.cim: src/keytest.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/vidtest.cim: src/vidtest.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/keyraw.cim: src/keyraw.asm $(COMMON)/platform/rom-abi.inc \
		$(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -DROM_ABI_LOCALE -DROM_ABI_EXTENDED \
		-I$(COMMON)/platform -o $@ $<

$(BUILD)/disksoak.cim: src/disksoak.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(BUILD)/n4bulk.cim: src/n4bulk.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -o $@ $<

$(NATIVE_TEST_VOLUME): third_party/cpm3/ccp.com $(BUILD)/diag.cim \
		$(BUILD)/wboot-user.cim $(BUILD)/status.cim $(BUILD)/keytest.cim \
		$(BUILD)/nativecheck.cim \
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

$(BUILD)/HELLO.hex: volume/HELLO.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -8 --od $(BUILD) --oo hex $<
	test -f $@

$(RECOVERY_VOLUME) $(RECOVERY_REPORT) &: third_party/cpm3/ccp.com \
		$(C4_DIAG) $(BUILD)/wboot.cim volume/README.txt \
		volume/profiles/recovery.json tools/build_volume.py diskdefs | $(OUT)
	$(PYTHON) tools/build_volume.py --profile volume/profiles/recovery.json \
		--output $(RECOVERY_VOLUME) --report $(RECOVERY_REPORT)

$(VOLUME): $(RECOVERY_VOLUME) | $(OUT)
	cp $(RECOVERY_VOLUME) $@

$(NATIVE_RECOVERY_VOLUME) $(NATIVE_RECOVERY_REPORT) &: \
		third_party/cpm3/ccp.com $(BUILD)/diag.cim $(BUILD)/wboot-user.cim \
		$(BUILD)/status.cim $(BUILD)/keytest.cim volume/README.txt \
		volume/profiles/recovery.json volume/profiles/native-recovery.json \
		tools/build_volume.py diskdefs | $(OUT)
	$(PYTHON) tools/build_volume.py \
		--profile volume/profiles/native-recovery.json \
		--output $(NATIVE_RECOVERY_VOLUME) \
		--report $(NATIVE_RECOVERY_REPORT)

$(C6_RECOVERY_VOLUME) $(C6_RECOVERY_REPORT) &: \
		third_party/cpm3/ccp.com $(BUILD)/diag.cim $(BUILD)/wboot-user.cim \
		$(BUILD)/status.cim $(BUILD)/keytest.cim $(BUILD)/keyraw.cim \
		$(BUILD)/disksoak.cim $(BUILD)/n4bulk.cim \
		volume/README.txt volume/profiles/recovery.json \
		volume/profiles/native-recovery.json volume/profiles/c6-recovery.json \
		tools/build_volume.py diskdefs | $(OUT)
	$(PYTHON) tools/build_volume.py \
		--profile volume/profiles/c6-recovery.json \
		--output $(C6_RECOVERY_VOLUME) --report $(C6_RECOVERY_REPORT)

$(FULL_VOLUME) $(FULL_REPORT) &: third_party/cpm3/ccp.com \
		$(BUILD)/diag.cim $(BUILD)/wboot-user.cim $(BUILD)/status.cim \
		$(BUILD)/keytest.cim $(BUILD)/vidtest.cim \
		$(BUILD)/crc.cim $(BUILD)/cmp.cim \
		$(BUILD)/mem.cim $(BUILD)/wc.cim $(BUILD)/find.cim \
		$(BUILD)/strings.cim volume/README.txt volume/TOOLS.txt \
		$(BUILD)/cpm3-utilities/manifest.json volume/profiles/full.json \
		tools/build_volume.py diskdefs | $(OUT)
	$(PYTHON) tools/build_volume.py --profile volume/profiles/full.json \
		--output $(FULL_VOLUME) --report $(FULL_REPORT)

$(DEV_VOLUME) $(DEV_REPORT) &: $(FULL_VOLUME) \
		$(BUILD)/cpm3-utilities/manifest.json $(BUILD)/HELLO.hex \
		volume/HELLO.asm volume/profiles/full.json volume/profiles/dev.json \
		tools/build_volume.py diskdefs | $(OUT)
	$(PYTHON) tools/build_volume.py --profile volume/profiles/dev.json \
		--output $(DEV_VOLUME) --report $(DEV_REPORT)

$(APPS_VOLUME) $(APPS_REPORT) &: $(BUILD)/diag.cim volume/APPS.txt \
		volume/profiles/apps.json tools/build_volume.py diskdefs | $(OUT)
	$(PYTHON) tools/build_volume.py --profile volume/profiles/apps.json \
		--output $(APPS_VOLUME) --report $(APPS_REPORT)

$(DEMO_VOLUME) $(DEMO_REPORT) &: third_party/cpm3/ccp.com \
		$(BUILD)/diag.cim $(BUILD)/wboot-user.cim $(BUILD)/status.cim \
		$(BUILD)/keytest.cim $(BUILD)/vidtest.cim \
		$(BUILD)/crc.cim $(BUILD)/cmp.cim \
		$(BUILD)/mem.cim $(BUILD)/wc.cim $(BUILD)/find.cim \
		$(BUILD)/strings.cim volume/README.txt volume/TOOLS.txt \
		volume/PROFILE.sub $(BUILD)/cpm3-utilities/manifest.json \
		volume/profiles/full.json volume/profiles/demo.json \
		tools/build_volume.py diskdefs | $(OUT)
	$(PYTHON) tools/build_volume.py --profile volume/profiles/demo.json \
		--output $(DEMO_VOLUME) --report $(DEMO_REPORT)

$(BOOT_MANIFEST): $(NATIVE_ROM_SYSTEM) $(NATIVE_ROM_FASTBOOT) \
		$(ROM_SYSTEM) $(ROM_FASTBOOT) \
		$(NATIVE_RECOVERY_VOLUME) $(NATIVE_RECOVERY_REPORT) \
		$(FULL_VOLUME) $(FULL_REPORT) $(DEV_VOLUME) $(DEV_REPORT) \
		$(APPS_VOLUME) $(APPS_REPORT) \
		$(DEMO_VOLUME) $(DEMO_REPORT) tools/build_boot_manifest.py | $(OUT)
	$(PYTHON) tools/build_boot_manifest.py \
		--system $(NATIVE_ROM_SYSTEM) --fast-stage $(NATIVE_ROM_FASTBOOT) \
		--fallback-system $(ROM_SYSTEM) --fallback-fast-stage $(ROM_FASTBOOT) \
		--volume $(NATIVE_RECOVERY_VOLUME) $(NATIVE_RECOVERY_REPORT) \
		--volume $(FULL_VOLUME) $(FULL_REPORT) \
		--volume $(DEV_VOLUME) $(DEV_REPORT) \
		--volume $(APPS_VOLUME) $(APPS_REPORT) \
		--volume $(DEMO_VOLUME) $(DEMO_REPORT) --output $@

$(C5_BOOT_MANIFEST): $(LOCALE_NATIVE_ROM_SYSTEM) \
		$(LOCALE_NATIVE_ROM_FASTBOOT) $(ROM_SYSTEM) $(ROM_FASTBOOT) \
		$(C5_ROM) $(C5_ROM_METADATA) \
		$(NATIVE_RECOVERY_VOLUME) $(NATIVE_RECOVERY_REPORT) \
		$(FULL_VOLUME) $(FULL_REPORT) $(DEV_VOLUME) $(DEV_REPORT) \
		$(APPS_VOLUME) $(APPS_REPORT) \
		$(DEMO_VOLUME) $(DEMO_REPORT) tools/build_boot_manifest.py | $(OUT)
	$(PYTHON) tools/build_boot_manifest.py \
		--system $(LOCALE_NATIVE_ROM_SYSTEM) \
		--fast-stage $(LOCALE_NATIVE_ROM_FASTBOOT) \
		--fallback-system $(ROM_SYSTEM) --fallback-fast-stage $(ROM_FASTBOOT) \
		--rom $(C5_ROM) --rom-metadata $(C5_ROM_METADATA) \
		--rom-abi 1.1 --identity-prefix c5 \
		--primary-slot-name c5-native \
		--volume $(NATIVE_RECOVERY_VOLUME) $(NATIVE_RECOVERY_REPORT) \
		--volume $(FULL_VOLUME) $(FULL_REPORT) \
		--volume $(DEV_VOLUME) $(DEV_REPORT) \
		--volume $(APPS_VOLUME) $(APPS_REPORT) \
		--volume $(DEMO_VOLUME) $(DEMO_REPORT) --output $@

$(C6_BOOT_MANIFEST): $(EXTENDED_NATIVE_ROM_SYSTEM) \
		$(EXTENDED_NATIVE_ROM_FASTBOOT) $(ROM_SYSTEM) $(ROM_FASTBOOT) \
		$(C6_ROM) $(C6_ROM_METADATA) \
		$(C6_RECOVERY_VOLUME) $(C6_RECOVERY_REPORT) \
		$(FULL_VOLUME) $(FULL_REPORT) $(DEV_VOLUME) $(DEV_REPORT) \
		$(APPS_VOLUME) $(APPS_REPORT) \
		$(DEMO_VOLUME) $(DEMO_REPORT) tools/build_boot_manifest.py | $(OUT)
	$(PYTHON) tools/build_boot_manifest.py \
		--system $(EXTENDED_NATIVE_ROM_SYSTEM) \
		--fast-stage $(EXTENDED_NATIVE_ROM_FASTBOOT) \
		--fallback-system $(ROM_SYSTEM) --fallback-fast-stage $(ROM_FASTBOOT) \
		--rom $(C6_ROM) --rom-metadata $(C6_ROM_METADATA) \
		--rom-abi 1.2 --identity-prefix c6 \
		--primary-slot-name c6-native \
		--volume $(C6_RECOVERY_VOLUME) $(C6_RECOVERY_REPORT) \
		--volume $(FULL_VOLUME) $(FULL_REPORT) \
		--volume $(DEV_VOLUME) $(DEV_REPORT) \
		--volume $(APPS_VOLUME) $(APPS_REPORT) \
		--volume $(DEMO_VOLUME) $(DEMO_REPORT) --output $@

cpm3-toolchain: $(ZXCC)

cpm3-system-check: $(ZXCC)
	$(PYTHON) tools/regenerate_cpm3.py --check
	$(PYTHON) tools/regenerate_cpm3.py --check \
		--adapter-address 0xc000 --top-page 0xbf \
		--metadata-policy gencpm \
		--output third_party/cpm3/cpm3-network-rom.sys

native-services-check: $(NATIVE_ROM_SYSTEM) $(NATIVE_ROM_FASTBOOT) \
		$(NATIVE_TEST_VOLUME) $(FULL_VOLUME)
	$(PYTHON) tests/native_services_test.py
	CPM_PLUS_JUKU_ROM_SYSTEM=$(NATIVE_ROM_SYSTEM) \
	CPM_PLUS_JUKU_ROM_FASTBOOT=$(NATIVE_ROM_FASTBOOT) \
	CPM_PLUS_JUKU_VOLUME=$(NATIVE_TEST_VOLUME) \
	CPM_PLUS_JUKU_EXTRA_COMMAND=NATIVE \
	CPM_PLUS_JUKU_EXTRA_MARKER='NATIVE: PASS' \
	CPM_PLUS_JUKU_EXTRA_COMMAND2='KEYTEST B' \
	CPM_PLUS_JUKU_EXTRA_READY_MARKER2='Juku Keytest 1.1 READY' \
	CPM_PLUS_JUKU_EXTRA_INPUT_HEX2='41 20 31 0d 1b' \
	CPM_PLUS_JUKU_EXTRA_MARKER2='Juku Keytest 1.1 DONE' \
	CPM_PLUS_JUKU_EXTRA_MARKERS2="BATCH 04|KEY 41 'A'|KEY 20 ' '|KEY 31 '1'|KEY 0D|BATCH 01|KEY 1B" \
	CPM_PLUS_JUKU_EXPECT_BOOT_READS=22 \
	CPM_PLUS_JUKU_EXPECT_DIR_READS=0 \
	CPM_PLUS_JUKU_EXPECT_TYPE_READS=2 \
	CPM_PLUS_JUKU_EXPECT_CAPABILITY_QUERIES=1 \
	CPM_PLUS_JUKU_EXPECT_DIAG_REPORTS=1 \
	CPM_PLUS_JUKU_EXPECT_NATIVE_BOOT_RECORD=1 \
	CPM_PLUS_JUKU_BOOT_PATH=network-smoke $(PYTHON) tests/cosim_check.py
	CPM_PLUS_JUKU_ROM_SYSTEM=$(NATIVE_ROM_SYSTEM) \
	CPM_PLUS_JUKU_ROM_FASTBOOT=$(NATIVE_ROM_FASTBOOT) \
	CPM_PLUS_JUKU_VOLUME=$(FULL_VOLUME) \
	CPM_PLUS_JUKU_EXTRA_COMMAND=STATUS \
	CPM_PLUS_JUKU_EXTRA_MARKER='Juku Status 1.3' \
	CPM_PLUS_JUKU_EXTRA_MARKERS='ROM: Juku ABI 01.00 network-first|S21 raw: 06  video: 03 (80x24)|Boot marker (00 cold/01 warm): 01  POST: 00  ROM ABI: 00|Bootstrap stage: 00  CRC retries: 00  protocol: 00|Host caps: NetDisk v03  read-ahead: 03  features: 2E  drives: 01' \
	CPM_PLUS_JUKU_EXTRA_COMMAND2='DIAG IO' \
	CPM_PLUS_JUKU_EXTRA_MARKER2='Keyboard/S21: PASS' \
	CPM_PLUS_JUKU_EXTRA_COMMAND3='DEVICE NAMES' \
	CPM_PLUS_JUKU_EXTRA_MARKER3='Physical Devices:' \
	CPM_PLUS_JUKU_EXTRA_MARKERS3='JUKU|IO' \
	CPM_PLUS_JUKU_EXPECT_STRICT_TPA_OPCODES=1 \
	CPM_PLUS_JUKU_EXPECT_BOOT_READS=24 \
	CPM_PLUS_JUKU_EXPECT_DIR_READS=3 \
	CPM_PLUS_JUKU_EXPECT_TYPE_READS=3 \
	CPM_PLUS_JUKU_EXPECT_STATUS_REPORTS=1 \
	CPM_PLUS_JUKU_EXPECT_BOOT_REPORTS=1 \
	CPM_PLUS_JUKU_EXPECT_CAPABILITY_QUERIES=2 \
	CPM_PLUS_JUKU_EXPECT_DIAG_REPORTS=2 \
	CPM_PLUS_JUKU_EXPECT_IO_DIAG=1 \
	CPM_PLUS_JUKU_EXPECT_NATIVE_BOOT_RECORD=1 \
	CPM_PLUS_JUKU_BOOT_PATH=network-smoke $(PYTHON) tests/cosim_check.py

regenerate-cpm3: $(ZXCC)
	$(PYTHON) tools/regenerate_cpm3.py

regenerate-cpm3-rom: $(ZXCC)
	$(PYTHON) tools/regenerate_cpm3.py --adapter-address 0xc000 \
		--top-page 0xbf --metadata-policy gencpm \
		--output third_party/cpm3/cpm3-network-rom.sys
