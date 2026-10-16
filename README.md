# riscv-core

An RV32I processor, single-cycle first and then a 5-stage pipeline, verified
with cocotb against a Python golden model and the official riscv-tests suite.

## Status
- ✅ Single-cycle RV32I core: all 37 base instructions + Zicsr + machine-mode traps
- ✅ **Official riscv-tests: 41/41 applicable rv32ui-p tests pass**, every instruction
  in lockstep with the golden model
- ✅ Lockstep co-simulation against a Python golden model, 10 directed programs
- ✅ Mutation-tested testbench: see [docs/verification.md](docs/verification.md)
- ✅ One-command regression: `./regress.sh` (about 45 seconds)
- ⬜ 5-stage pipeline (Milestone 3)

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
  harness (`cosim.py`), a mini assembler (`asm.py`)
- `tests/`: official riscv-tests (git submodule) and `build_rvtests.py`
- `fpga/`: Arty A7 top level and constraints
- `docs/`: worklog, bug catalog, verification write-up

## Running the tests
One command runs the full regression: unit tests, directed lockstep
programs, and the official riscv-tests (built fresh each run). It also fetches
the riscv-tests submodule on a fresh clone. Exit code 0 means everything passed.
```bash
./regress.sh                # Git Bash
```
```powershell
powershell -ExecutionPolicy Bypass -File .\regress.ps1   # PowerShell
```
Extra arguments go to pytest, e.g. `./regress.sh -x` stops at the first
failing testbench. To run pieces by hand, `source env.sh` (or `. .\env.ps1`)
then `pytest tb/test_core.py -v`.

Waveforms land in `sim_build/<build>/`. Open them with `gtkwave`. When a
riscv-test fails, its disassembly is in `tests/build/rv32ui-p-<name>.dump`.

Toolchain: Icarus Verilog + Yosys (OSS CAD Suite), cocotb 2.1, xPack
`riscv-none-elf-gcc` 15.2.
