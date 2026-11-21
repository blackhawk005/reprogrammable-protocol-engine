# Flow notes

Physical-flow results for the Phase 0 design (hardwired UART TX, not the final engine).
Everything here was measured; limits of each claim are stated.

## Setup

| Item | Value |
|---|---|
| Template | `ttihp-verilog-template` `main`, commit `4b1204a` |
| Support tools | `tt-support-tools` `9d13ff3` |
| PDK / LibreLane | `ihp-sg13cmos5l` / `3.1.0.dev4` |
| Tiles | 8x4 (die area 1,225,260 um^2) |
| Constrained clock | 20 ns (50 MHz) in the first run; **16.6 ns (~60 MHz)** from the second run on (`CLOCK_PERIOD` in `src/config.json`) |
| Runs | CI `gds`/`precheck` on commit `a312962` (20 ns); local hardening at 16.6 ns |

`info.yaml` says `clock_hz: 60000000`, but that field is datasheet metadata only; the flow constraint is `CLOCK_PERIOD` in `src/config.json` (template default 20 ns). It was changed to 16.6 ns for the 60 MHz run below.

## Results (commit a312962, 8x4)

| Check | Result |
|---|---|
| Magic DRC | 0 errors |
| LVS | 0 errors |
| Antenna violating nets | 0 |
| Power grid violations | 0 |
| Setup / hold violations | 0 / 0 in all 3 corners |
| Tiny Tapeout precheck | All 10 checks passed (incl. KLayout SG13CMOS5L DRC) |
| Gate-level simulation | Passed (same 5 cocotb tests as RTL) |

KLayout DRC is disabled inside the hardening flow (`RUN_KLAYOUT_DRC: 0`); it is run by the precheck instead.

## Timing (flow's nominal PVT corners)

| Corner | Setup slack @ 20 ns | Setup slack @ 16.6 ns | Hold slack (both) |
|---|---:|---:|---:|
| slow 1.08 V, 125 C | +13.01 ns | +10.29 ns | +0.67 ns |
| typical 1.20 V, 25 C | +14.03 ns | +11.31 ns | +0.33 ns |
| fast 1.32 V, -40 C | +14.61 ns | +11.89 ns | **+0.13 ns** |

- The 16.6 ns run (local hardening, same RTL, same cell count) has 0 setup and 0 hold violations. A 16.6 ns CI run is pending.
- Hold slack is identical in both runs: hold does not depend on the clock period. It is the thin margin (+0.13 ns, fast corner).
- Worst clock skew (setup): 0.26 ns.
- Pre-silicon, post-route flow results. They do not characterise external pad timing.

## Area and cells

| Item | Value |
|---|---|
| Synthesis chip area (Yosys) | 2,959 um^2 |
| Standard cells after place-and-route | 266, 4,155 um^2 |
| Flip-flops | 26 (state 2, shift 8, bit index 3, cycle counter 10, synchroniser 3) |
| Timing-repair buffers inserted | 67 |
| Utilization of die | 0.34% |
| Total power (flow estimate) | 0.22 mW |

The design uses a tiny fraction of an 8x4 die. Utilization says little about congestion or timing for a larger design.

## Run time

- Local hardening, stock template: 24 min (about 11 min of that in Magic DRC).
- GitHub Actions: `gds` 55 min, `precheck` 26 min, `gl_test` 1 min.

## Not yet done

- CI (GDS + precheck) at the 16.6 ns constraint; the CI numbers above are from the 20 ns run.
- Hold-buffer cause: the 67 repair buffers were not analysed.
- GitHub Pages preview is not enabled (repo is private).
