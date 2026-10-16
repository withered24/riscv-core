# Verification

## Method (so far)

**Golden-model lockstep co-simulation.** `tb/iss.py` is an RV32I
instruction-set simulator written straight from the ISA manual as a plain
interpreter, deliberately *not* structured like the RTL, so the two can't
share a misunderstanding by construction. Every test program runs on both.
Each clock cycle the testbench compares the core's `trace_*` outputs (pc,
instruction, register write, store address/byte-enables/data) against what
the model did for the same instruction. The first disagreement fails the
test and prints the last eight instructions.

**Known answers on top.** Each test also checks hand-computed results read
straight out of the core's register file and memory, which catches a mistake
the RTL and the model might both make.

**Test programs** are written in assembly and built by `tb/asm.py`, a small
assembler (stopgap until the RISC-V GCC toolchain is installed). Its
encodings were checked against known instruction words, and its branch/jump
offsets round-tripped through the model 2,000 times each.

## Official riscv-tests: `tb/test_riscv_tests.py`

The 42 `rv32ui-p-*` tests from riscv-tests, built by `tests/build_rvtests.py`
with `riscv-none-elf-gcc -march=rv32i_zicsr_zifencei -mabi=ilp32` and linked
at `0x8000_0000` (the core's `RESET_PC` is set to match). Each test checks
itself and reports through a store to `tohost` (1 = pass, `(n<<1)|1` = check
*n* failed). On top of that, **every instruction runs in lockstep with the
golden model**, so a failure names the exact instruction instead of just
"check 7".

**Result: 41/41 applicable tests pass.** `ma_data` needs hardware misaligned
access; this core traps instead (allowed by the ISA), and `test_ma_data_traps`
checks that the first data trap is a misaligned-load trap on an `lh`.

What the tests needed from the core (Milestone 2's "CSR gotcha"):
- **Zicsr**: CSRRW/S/C and the immediate forms; mstatus (MIE/MPIE),
  misa, mtvec, mscratch, mepc, mcause, mtval, mie/mip (zero), ID registers.
- **Traps**: ECALL (the test's pass/fail report), EBREAK, illegal
  instruction (including unimplemented CSRs: the startup code probes `satp`,
  `pmpaddr0`, `medeleg`... and is written to survive the trap), misaligned
  load/store/jump target. **MRET** returns to mepc.

Mutation check of this harness (planted bug → tests that fail):

| Planted bug | Failing tests |
|-------------|---------------|
| BLTU compares signed | `bltu` |
| LH sign-extends from bit 7 | `lh`, `sh`, `fence_i` (which uses `lh`) |
| CSR write to mepc off by 4 | all 41 + `test_ma_data_traps` (every test's startup goes through MRET) |

## Directed tests: `tb/test_core.py`

| Test | Covers |
|------|--------|
| `test_first_five` | add, addi, lw, sw, beq taken / not taken |
| `test_alu_register_ops` | all 10 R-type ops, signed/unsigned split, shift uses only `b[4:0]` |
| `test_alu_immediate_ops` | all OP-IMM ops; `addi -1024` must not decode as SUB (instr[30] trap) |
| `test_upper_immediates` | LUI, AUIPC (incl. negative upper immediate) |
| `test_branches` | all 6 branches taken and not taken at the -1 vs 1 boundary; backward loop |
| `test_jumps` | JAL link, JALR link and target with bit 0 cleared, call/return |
| `test_loads_and_stores` | every load width at every offset, sign vs zero extension, partial-store merging, negative offset |
| `test_x0_stays_zero` | writes to x0 by every instruction class; FENCE as no-op |
| `test_fibonacci` | a real loop program, results checked in memory |
| `test_bubble_sort` | nested loops, signed compares, 16-element sort |

## Mutation testing

Bugs planted in the RTL one at a time, to check that the suite notices:

| Planted bug | Caught? |
|-------------|---------|
| BLTU compares signed | ✅ |
| SRA does a logical shift | ✅ |
| LH sign-extends from bit 7 | ✅ (after fixing coverage hole, bugs.md #3) |
| LBU sign-extends | ✅ |
| SH ignores the address offset | ✅ |
| JALR keeps bit 0 | ✅ |
| `instr[30]` turns every ADDI into SUB | ✅ |
| B-immediate bit 0 taken from the instruction | ✅ |
| Branches always taken | ✅ |
| x0 read-side check removed | ⚪ equivalent: `regs[0]` is never written, so simulation can't tell |
| Register writes allowed during reset | ⚪ equivalent: registers are undefined after reset by the ISA |

## Synthesis sanity

`yosys synth -top core`: synthesizes cleanly, no inferred latches
(~8.5k generic cells with CSRs; ~4.5k without).

## Still to do (yours)

- Unit-test YOUR TURN stubs: `test_regfile.py`, `test_alu.py`, `test_immgen.py`
- Constrained-random program generator + functional coverage (Milestone 4)
- SVA assertions (x0 never written, no write during reset)
