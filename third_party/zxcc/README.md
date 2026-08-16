# ZXCC build input

`releases/zxcc-0.5.7.tar.gz` is the unmodified ZXCC 0.5.7 source release from
<https://www.seasip.info/Unix/Zxcc/>. Its SHA-256 is:

```text
6095119a31a610de84ff8f049d17421dd912c6fd2df18373e5f0a3bc796eb4bf
```

ZXCC is Copyright (C) John Elliott and is distributed under the GNU General
Public License; the bundled CPMIO and CPMREDIR libraries are distributed under
the GNU Lesser General Public License. The license texts and upstream README
files are included unchanged in the source archive.

The project builds it with `-std=gnu17` because GCC 15 defaults to C23, which
no longer accepts some of this deliberately portable older C source. Run
`make cpm3-toolchain`; no system-installed CP/M cross tools are required.
