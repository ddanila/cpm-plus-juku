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
COMMON := third_party/juku-common

SYSTEM := $(OUT)/cpm-plus-juku-system.bin
FASTBOOT := $(OUT)/cpm-plus-juku-fastboot-v15.bin
VOLUME := $(OUT)/cpm-plus-juku.img

.PHONY: all check clean tools verify-prebuilt regenerate-cpm3
all: $(SYSTEM) $(FASTBOOT) $(VOLUME)

tools: $(ZMAC) $(LD80) $(ZX0)

verify-prebuilt: all
	cmp $(SYSTEM) prebuilt/cpm-plus-juku-system.bin
	cmp $(FASTBOOT) prebuilt/cpm-plus-juku-fastboot-v15.bin
	cmp $(VOLUME) prebuilt/cpm-plus-juku.img

check: verify-prebuilt
	$(PYTHON) tests/cosim_check.py

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

$(BUILD)/platform-adapter.rel: src/platform-adapter.asm \
		$(COMMON)/platform/ram-console.asm \
		$(COMMON)/platform/ram-console-font.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 \
		-I$(COMMON)/platform -o $@ $<

$(BUILD)/ram-keyboard.rel: $(COMMON)/platform/ram-keyboard.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -o $@ $<

$(BUILD)/netdisk-v3.rel: $(COMMON)/platform/netdisk-v3.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -DCPM3ADAPTER -o $@ $<

$(BUILD)/netconsole.rel: $(COMMON)/platform/netconsole.asm $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m --rel7 -8 -o $@ $<

$(BUILD)/adapter.all: $(BUILD)/platform-adapter.rel \
		$(BUILD)/ram-keyboard.rel $(BUILD)/netdisk-v3.rel \
		$(BUILD)/netconsole.rel $(LD80)
	$(LD80) -m -O bin -o $@ -s /dev/null \
		-P0xa000 $(BUILD)/platform-adapter.rel \
		-P0xa900 $(BUILD)/ram-keyboard.rel \
		-P0xac10 $(BUILD)/netdisk-v3.rel \
		-P0xae80 $(BUILD)/netconsole.rel

$(BUILD)/adapter.bin: $(BUILD)/adapter.all
	tail -c+40961 $< >$@
	test $$(stat -c %s $@) -le 4096

$(SYSTEM): $(BUILD)/adapter.bin third_party/cpm3/cpm3.sys \
		tools/mksystem3.py | $(OUT)
	$(PYTHON) tools/mksystem3.py $(BUILD)/adapter.bin \
		third_party/cpm3/cpm3.sys $@

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

$(FASTBOOT): $(BUILD)/fastboot-core.cim \
		$(BUILD)/fastboot-extension.cim $(SYSTEM) $(ZX0) \
		tools/build_fastboot.py | $(OUT)
	$(PYTHON) tools/build_fastboot.py $(BUILD)/fastboot-core.cim \
		$(BUILD)/fastboot-extension.cim $(SYSTEM) $(ZX0) $@

$(BUILD)/diag.cim: src/diag.asm $(wildcard $(COMMON)/diag/*.asm) $(ZMAC) | $(BUILD)
	$(ZMAC) --nmnv --zmac -m -8 -I$(COMMON)/diag -o $@ $<

$(VOLUME): third_party/cpm3/ccp.com $(BUILD)/diag.cim volume/README.txt \
		tools/build_volume.py diskdefs | $(OUT)
	$(PYTHON) tools/build_volume.py $@ third_party/cpm3/ccp.com \
		$(BUILD)/diag.cim volume/README.txt

regenerate-cpm3:
	test -n "$(ZXCC)" -a -n "$(CPM3_TOOLS)"
	$(PYTHON) tools/regenerate_cpm3.py --zxcc "$(ZXCC)" \
		--tools "$(CPM3_TOOLS)"
