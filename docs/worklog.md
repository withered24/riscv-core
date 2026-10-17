# Worklog

## 2026-10-16
- Repo scaffolded; OSS CAD Suite (Icarus 14, Yosys 0.70) + cocotb 2.1 installed.
- Single-cycle RV32I core written: `regfile`, `immgen`, `alu`, `branch_unit`,
  `decoder`, `core`, all in `rtl/`.
- Golden model (`tb/iss.py`), mini assembler (`tb/asm.py`), lockstep co-sim
  harness and 10 directed tests (`tb/test_core.py`). All green.
- Found and fixed 3 bugs (1 RTL, 1 testbench, 1 coverage hole), see bugs.md.
- Mutation-tested the suite: 9/9 real planted bugs caught, 2 equivalent
  mutants documented. Yosys synthesis clean, no latches.
- Next: your unit tests, then riscv-tests (M2).

## 2026-10-16 (later): Milestone 2
- Installed xPack riscv-none-elf-gcc 15.2 (checksum verified); riscv-tests
  added as a git submodule; `tests/build_rvtests.py` builds all 42 rv32ui-p
  tests (no `make` needed).
- Added `rtl/csr.sv` (Zicsr + machine-mode trap state) and trap/MRET logic
  in the core; tightened the decoder's illegal-instruction checks; golden
  model got the same features, written from the privileged spec.
- Factored the lockstep checker into `tb/cosim.py`; it now also compares
  trap/cause every cycle.
- **41/41 applicable rv32ui tests pass first run**, in lockstep. `ma_data`
  is N/A (core traps on misaligned access, allowed by the ISA) and has its
  own check. Mutation-tested the harness (see verification.md).
- No new bugs found this milestone. The single-cycle core is simple enough
  that the directed tests had already shaken out the datapath; expect the
  pipeline to be different.
- Added `regress.sh` / `regress.ps1`: the whole regression in one command
  (fetches the submodule on a fresh clone, builds riscv-tests, runs every
  testbench). Checked that a planted bug makes both exit 1. Milestone 2 done.

## 2026-10-17: Milestones 3 and 4
- **Pipeline (M3).** Single-cycle core kept as `rtl/core_single.sv`; the new
  `rtl/core.sv` is a 5-stage pipeline with forwarding, load-use/CSR-use
  stall, EX branch resolution, precise traps in MEM, FENCE.I. Memories became
  synchronous-read (block-RAM style) for the pipeline. Every suite now runs
  on both cores.
- Lockstep harness grew two checks a retirement trace can't make: the memory
  bus is watched every cycle (a wrong-path store would otherwise be
  invisible) and final registers + memory are compared. Fixing those checks
  turned up 2 testbench bugs (bugs.md #4, #5).
- `tb/test_pipeline.py`: 9 tests that check the hazard *mechanism* through
  internal signals (zero-stall forwarding, exact stall and flush costs,
  wrong-path discard, precise traps, self-modifying code).
- Pipelined core passed directed, hazard and all 41 riscv-tests on first
  run; CPI 1.13–2.2.
- **Random + coverage (M4).** `tb/rand_prog.py` generator, `tb/coverage.py`
  (126 bins), `tb/test_random.py` (200 programs per core per regression,
  fails on a coverage hole). Soak: 5,000 programs / 1.3M instructions clean.
  Closed 2 coverage holes (MRET + branch, MRET + store).
- **Formal.** 23 SVA properties + 6 covers in `core.sv`, proven by
  k-induction in `formal/core.sby` (needed stored-PC alignment invariants to
  become inductive). Concurrent `assert property` silently produced no
  checks with this tool build, so the properties use immediate assertions.
- **Mutation testing** of the pipeline (`tb/mutate.py`): 28 mutants × 5
  layers. First run 24/28; the survivors exposed 2 test holes (bugs.md #6,
  #7) and showed formal catches what simulation can't. Final: 28/28.
- Bug count: 7 total, honest (course target 10+); see bugs.md "Count".
- Yosys: pipeline 9,920 cells vs 7,166 single-cycle; no latches.
- Next: Milestone 5 (Arty A7 bring-up), and your YOUR TURN unit tests.
