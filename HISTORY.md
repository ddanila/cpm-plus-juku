# Project history

The first simulator-proven Juku CP/M Plus baseline was developed temporarily
on CP/Mish's public `juku` branch. Its complete original patch remains
available in `ddanila/cpmish` as commit
`59b8528e6c73ee1ea704b9f6bddcfcf96fc82eca` (subject: “Add simulator-proven
Juku CP/M Plus”, 2026-08-15).

Once the experiment proved that a genuine Digital Research CP/M 3 system could
boot on the Juku model, it was separated here rather than presented as a new
CP/Mish version. CP/Mish commit
`40451f3fe14c0030dd26c80eb796db9a25f258c2` (subject: “Separate CP/M Plus into
its own project”, 2026-08-15) removes the duplicate implementation while
deliberately retaining the prototype in that repository's published history.

The standalone tree begins with commit `4267d00`. During extraction, reusable
Juku platform and direct-fastboot modules moved to `ddanila/juku-common` commit
`aa1b4bfa2cc623c946e5d31ae6003d9b341dc4ce`. CP/Mish and this project consume
the same pinned shared sources but retain independent BIOS policy, memory map,
system generation, artifacts, tests, and release plans.
