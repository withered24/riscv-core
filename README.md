# riscv-core

An RV32I processor, single-cycle first and then a 5-stage pipeline, verified
with cocotb against a Python golden model and the official riscv-tests suite.

## Status
- ✅ Single-cycle RV32I core (`rtl/core_single.sv`): all 37 base instructions + Zicsr + machine-mode traps
- ✅ **5-stage pipeline** (`rtl/core.sv`): full forwarding (EX/MEM, MEM/WB, WB→ID bypass),
  one-cycle load-use/CSR-use stall, predict-not-taken with branches resolved in EX
  (2-cycle penalty), precise traps taken in MEM, FENCE.I for self-modifying code,
  synchronous (block-RAM style) memories. CPI 1.13–2.2 on the directed programs,
  1.52 on random code
- ✅ **Official riscv-tests: 41/41 applicable rv32ui-p tests pass on both cores**, every
  instruction in lockstep with the golden model
- ✅ **Constrained-random verification**: 200 generated programs per core in every
  regression, soaked at 5,000 programs (1.3M instructions); **126/126 functional
  coverage bins** closed
- ✅ **Formal**: 23 SVA properties on the pipeline proven by k-induction (SymbiYosys),
  every instruction stream, no depth bound
- ✅ **Mutation-tested**: 28/28 planted pipeline bugs caught (no single layer catches all
  of them; see the table in [docs/verification.md](docs/verification.md))
- ✅ One-command regression: `./regress.sh` (under a minute)
- ⬜ FPGA bring-up on the Arty A7 (Milestone 5)

Methodology and numbers: [docs/verification.md](docs/verification.md). Bugs found
along the way: [docs/bugs.md](docs/bugs.md).

## riscv-tests (rv32ui-p)

| | | | | | | |
|---|---|---|---|---|---|---|
| ✅ simple | ✅ add | ✅ addi | ✅ and | ✅ andi | ✅ auipc | ✅ beq |
| ✅ bge | ✅ bgeu | ✅ blt | ✅ bltu | ✅ bne | ✅ fence_i | ✅ jal |
| ✅ jalr | ✅ lb | ✅ lbu | ✅ lh | ✅ lhu | ✅ lw | ✅ ld_st |
| ✅ lui | ✅ or | ✅ ori | ✅ sb | ✅ sh | ✅ sw | ✅ st_ld |
| ✅ sll | ✅ slli | ✅ slt | ✅ slti | ✅ sltiu | ✅ sltu | ✅ sra |
| ✅ srai | ✅ srl | ✅ srli | ✅ sub | ✅ xor | ✅ xori | ⚪ ma_data¹ |

¹ `ma_data` requires hardware support for misaligned loads/stores. This core
traps on them instead, which the ISA allows; `test_ma_data_traps` checks
that it takes the correct misaligned-load trap.

## Layout
- `rtl/`: the processor (SystemVerilog)
- `tb/`: cocotb testbenches, the Python golden model (`iss.py`), the lockstep
  harness (`cosim.py`), a mini assembler (`asm.py`), the random program
  generator (`rand_prog.py`), functional coverage (`coverage.py`), mutation
  testing (`mutate.py`)
- `formal/`: SymbiYosys proof of the pipeline's SVA properties (`core.sby`)
- `tests/`: official riscv-tests (git submodule) and `build_rvtests.py`
- `fpga/`: Arty A7 top level and constraints
- `docs/`: worklog, bug catalog, verification write-up

## Running the tests
One command runs the full regression on both cores: unit tests, directed
lockstep programs, pipeline hazard tests, the official riscv-tests (built
fresh each run), 200 constrained-random programs with coverage, then the
formal proof. It also fetches the riscv-tests submodule on a fresh clone.
Exit code 0 means everything passed.
```bash
./regress.sh                # Git Bash
```
```powershell
powershell -ExecutionPolicy Bypass -File .\regress.ps1   # PowerShell
```
Extra arguments go to pytest, e.g. `./regress.sh -x` stops at the first
failing testbench. To run pieces by hand, `source env.sh` (or `. .\env.ps1`)
then `pytest tb/test_core.py -v`.

`REGRESS_CORES=pipeline` (or `single`) limits a run to one core. A longer random
soak: `RAND_PROGRAMS=5000 RAND_SEED=100000 pytest tb/test_random.py`. Mutation
testing (about 5 minutes on 6 workers): `python tb/mutate.py -j 6`.

Waveforms land in `sim_build/<build>/`. Open them with `gtkwave`. When a
riscv-test fails, its disassembly is in `tests/build/rv32ui-p-<name>.dump`.

Toolchain: Icarus Verilog, Yosys + yosys-slang, SymbiYosys + bitwuzla (OSS CAD Suite), cocotb 2.1, xPack
`riscv-none-elf-gcc` 15.2.
