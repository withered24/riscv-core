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
