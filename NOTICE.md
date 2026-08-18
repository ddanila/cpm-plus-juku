# Provenance and licensing

Project-owned Juku sources and build scripts are Copyright (c) 2026 Danila
Sukharev and are licensed under the repository's BSD 2-Clause `LICENSE`.
OpenAI GPT-5.6 Sol was used as a development assistant; it is not named as a
copyright holder.

The following components retain their own provenance and terms:

- `third_party/cpm3`: Digital Research CP/M Plus material distributed under
  the grant reproduced in `third_party/cpm3/LICENSE.md`;
- `third_party/juku-common`: the pinned shared Juku source repository and its
  per-component MIT/BSD notices, including the console font adapted from
  Romeo Van Snick's MIT-licensed Creep 0.31;
- `third_party/zmac`: the zmac assembler sources and notices from CP/Mish;
- `third_party/ld80`: the public-domain ld80 linker sources from CP/Mish;
- `third_party/zx0`: Einar Saukas's BSD-licensed ZX0 compressor;
- the ZX0 Intel 8080 decoder embedded in the shared fastboot extension is by
  Ivan Gorodetsky and based on Einar Saukas's decoder.

Audit-only patches under `experiments/external-software/` do not place their
targets in a generated CP/M image. `cpm-ls-z88dk.patch` modifies Kevin Boone's
GPLv3 `cpm-ls` and is GPLv3; its added console shim is Copyright (c) 2026 Danila
Sukharev under the same terms. `fig-forth-zmac.patch` records mechanical build
changes against the credited John Cassady/Kim Harris FIG-Forth 1.1 listing;
the source notice and the reason it is not packaged are preserved in
`docs/external-software-audit.md`.

The simulator is not copied here. Tests use a sibling `8080-cosim` checkout or
the path selected by `JUKU_COSIM_ROOT`.
