# Verification

Two cores, one regression: the single-cycle core (`rtl/core_single.sv`) and
the 5-stage pipeline (`rtl/core.sv`) run every simulation suite below.

| Layer | What | Result |
|-------|------|--------|
| Golden model | `tb/iss.py`, every instruction in lockstep | (the checker for everything below) |
| Directed | 10 hand-written programs, `tb/test_core.py` | ✅ both cores |
| Pipeline hazards | 9 tests that watch the pipeline's internals, `tb/test_pipeline.py` | ✅ |
| Official suite | 41/41 applicable riscv-tests rv32ui-p, `tb/test_riscv_tests.py` | ✅ both cores |
| Constrained random | 200 programs per core every regression (~52k instructions each); soaked at 5,000 programs | ✅ both cores |
| Functional coverage | 126 bins (103 ISA + 23 pipeline), `tb/coverage.py` | ✅ 126/126 pipeline, 103/103 single-cycle |
| Formal | 23 SVA assertions proven by k-induction (unbounded), 6 covers reached, `formal/core.sby` | ✅ |
| Mutation | 28 planted pipeline bugs, `tb/mutate.py` | ✅ 28/28 caught |

`./regress.sh` (Git Bash) or `regress.ps1` (PowerShell) runs all of it in
one command, in under a minute, and exits nonzero if anything fails.

---

## 1. The checker: golden-model lockstep

`tb/iss.py` is an RV32I + Zicsr instruction-set simulator written straight
from the ISA manuals as a plain interpreter, deliberately *not* structured
like the RTL, so the two can't share a misunderstanding by construction.

Every program runs on the RTL core and the model together (`tb/cosim.py`).
Each time the core retires an instruction (`trace_valid`), the testbench
compares its `trace_*` outputs (pc, instruction, register write, store
address/byte-enables/data, trap and cause) against what the model did for
that instruction. The first disagreement fails with the last eight
instructions. A retirement trace can miss two things, so the harness also
checks them directly:

- **The memory bus, every cycle.** On the pipeline a store writes memory in
  EX, two cycles before it retires, so a wrong-path store that leaked onto
  the bus would never appear in the trace. Every bus write must match the
  next store to retire, in order, and none may be left over at the end.
- **Final state.** After the last instruction commits, the whole register
  file and every word the model stored to are compared against the model.

Directed tests also check hand-computed answers, which catches a mistake the
RTL and the model might both make.

## 2. Directed tests: `tb/test_core.py`

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

Pipeline CPI on these programs: 1.13 to 2.2 (bubble sort 1.50). The
single-cycle core is 1.00 by construction.

## 3. Pipeline hazard tests: `tb/test_pipeline.py`

Lockstep proves the results are right; it can't prove the *mechanism*
(a core that stalled on every dependency would also be right). These tests
watch the pipeline's internal signals every cycle and check the mechanism
itself, the "done when" list from the course's pipelining guide:

| Test | Checks |
|------|--------|
| `test_forwarding_no_stalls` | ALU→ALU chains at distance 1, 2, 3 give right answers with **zero** stalls; all four forwarding paths and the WB→ID bypass were used |
| `test_forwarding_priority` | when EX/MEM and MEM/WB both hold the register, the newer (EX/MEM) wins |
| `test_x0_never_forwarded` | a write to x0 in flight is never forwarded; a load into x0 doesn't stall its reader |
| `test_load_use_patterns` | every load-use shape (ALU operand, store data, store address, load address, branch, JALR target, CSR read) stalls exactly one cycle; distance-2 doesn't stall; false dependencies (CSR uimm, LUI immediate bits that look like rs1) don't stall |
| `test_load_use_costs_one_cycle` | timing: a dependent load-use pair costs exactly 1 cycle more than an independent one |
| `test_wrong_path_is_discarded` | after every taken branch/JAL/JALR, the two fetched instructions (including an illegal one) have no effect and don't trap |
| `test_taken_branch_costs_two_cycles` | timing: each taken BEQ/JAL/JALR loses exactly 2 cycles; not-taken loses 0 |
| `test_fence_i_self_modifying_code` | a store over an instruction already in the pipeline, then FENCE.I: the new instruction runs |
| `test_traps_are_precise` | 8 traps of 4 kinds, each with older instructions completed and younger ones gone; a write to mtvec immediately followed by a trap |

## 4. Official riscv-tests: `tb/test_riscv_tests.py`

The 42 `rv32ui-p-*` tests from riscv-tests, built by `tests/build_rvtests.py`
with `riscv-none-elf-gcc -march=rv32i_zicsr_zifencei -mabi=ilp32` and linked
at `0x8000_0000`. Each test checks itself and reports through `tohost`; on
top of that **every instruction runs in lockstep with the golden model**, so
a failure names the exact instruction instead of just "check 7".

**Result: 41/41 applicable tests pass on both cores.** `ma_data` needs
hardware misaligned access; this core traps instead (allowed by the ISA),
and `test_ma_data_traps` checks that the first data trap is a
misaligned-load trap on an `lh`. The pipelined core passed all 41 on its
first run, which is less a boast than a sign that the earlier layers had
already done the work: the core was written against the hazard tests and
the lockstep harness from the start.

## 5. Constrained-random programs: `tb/rand_prog.py`, `tb/test_random.py`

Each seed generates one program (assembly text plus a data image), run in
lockstep against the model, so the generator never has to know the right
answers. It only has to make programs that finish and that hit the hard cases.

**Constraints (what keeps a random program runnable).** x28-x31 are
reserved (pointer-table base, data base, loop counter, trap-handler
scratch); random instructions write only x0-x27. Loads and stores go
through x29 or through a pointer loaded from a table, so every access lands
in the data region. Control flow only goes forward except counted loops
(1-4 iterations), so every program terminates. Traps are welcome: a small
handler skips the trapping instruction and carries on.

**Bias (what makes it find bugs).** Each program picks 5 "hot" registers for
75% of operands, so read-after-write at distance 1-3 (the forwarding and
stall cases) is the norm, not the exception. Constants come from an
edge-value list half the time (0, -1, 0x80000000, 0x7FFFFFFF...). Templates
target specific hazards: pointer chasing (load → address), `auipc` → `jalr`
(±1 and ±2 offsets: bit-0 clearing and misaligned-target traps), `csrw mepc`
→ `mret`, store → `fence.i` → run the stored instruction, plus every trap
cause including 10 known-illegal encodings.

**Numbers.**
- Regression: seeds 1-200 on each core, 51,713 instructions / 78,451 cycles
  on the pipeline (CPI 1.52), about 15 s.
- Soak: seeds 100000-104999 (5,000 programs) on each core: 1,315,676
  instructions on the pipeline (CPI 1.53) and 1,315,756 on the single-cycle
  core, all matching the model. (The single-cycle soak started after the
  MRET-store template was added, hence the slightly different count.)
- Bugs found in the RTL by random: **none.** By the time the generator
  existed, the directed, hazard and riscv-tests layers had already been
  green. The mutation table (§8) is the evidence that random would have
  found them: it catches 25 of the 28 planted bugs, including six that the
  directed tests and riscv-tests both miss.

Reproduce one program: `RAND_SEED=1234 RAND_PROGRAMS=1 pytest tb/test_random.py`,
or print it with `python tb/rand_prog.py 1234`. A failing program is saved
to `sim_build/rand_fail_<seed>.S`.

## 6. Functional coverage: `tb/coverage.py`

"200 random programs passed" means nothing unless they exercised the hard
cases. The coverage model says which cases count and whether they happened:

| Group | Bins | Sampled from |
|-------|------|--------------|
| `op` | 50: every RV32I + Zicsr mnemonic, ecall/ebreak/mret/wfi, illegal | each retired instruction |
| `branch` | 12: each branch type taken and not taken | retired instructions |
| `trap` | 6: every cause the core can raise | retired instructions |
| `raw` | 24: read-after-write at distance 1/2/3 × producer (ALU, load, CSR, jump link) × operand | retired instructions |
| `x0_write` | 4: each producer type writing x0 | retired instructions |
| `hazard` | 7 named shapes: load→branch, load→store data, load→address, CSR→use, auipc→jalr, csrw mepc→mret, store→fence.i | retired instructions |
| `pipe` | 23 (pipeline only): each forwarding path per operand, both at once, forwarding a load/CSR value from MEM/WB, WB→ID bypass per operand, stall per reason, redirect per kind, trap, MRET, trap and branch in the same cycle, MRET and branch in the same cycle, trap during a stall, store killed by a trap, store killed by an MRET, a younger exception squashed by an older one | pipeline internals, every cycle |

The regression **fails on any hole** with the default seeds. Holes found and
closed:

1. **`pipe.mret_beats_redirect`** (MRET in MEM with a taken jump in EX) was
   0 on the first 200-program run. The generator's MRET template always put
   an ALU instruction after the MRET. Fix: half the time it's now a jump.
2. **`pipe.store_killed_by_mret`** didn't exist at first: one bin counted
   "store killed by a trap *or* an MRET", and traps filled it. Mutation
   testing (§8) found a surviving bug, a store not cancelled by an older
   MRET, and showed the hole. The bin was split and the generator now puts a
   store after MRET 30% of the time. Lesson: a bin that lumps two cases
   together can hide that one of them never happens.

Least-hit bins after the regression run: `pipe.younger_exception_flushed`
(23), `raw.link.d3.rs1` (44), `raw.csr.d2.rs2` (45). Every bin is hit at
least 23 times.

**Known gap, documented rather than covered:** neither the decoder nor the
model checks `funct7` on OP/OP-IMM (e.g. a MUL encoding executes as ADD
instead of trapping). Both agree, so lockstep can't see it; it's a spec
deviation to fix with the M extension work, and the generator doesn't
produce those encodings.

## 7. Formal: SVA properties, `formal/core.sby`

`rtl/core.sv` ends with an `ifdef FORMAL` block: 23 assertions and 6 cover
statements. SymbiYosys (yosys-slang front end, bitwuzla) checks them with
`imem_rdata` and `dmem_rdata` as **free inputs**, so the properties hold for
every possible instruction stream and load value, not just the programs the
simulations run. The proof is **k-induction** (base case from reset, induction
depth 20), which means the assertions hold in every reachable state, with no
depth limit. It takes about 10 s.

Properties (grouped):
- **Bubbles are bubbles:** an invalid ID/EX or EX/MEM entry has all-zero controls.
- **x0:** never forwarded; reads as zero after forwarding.
- **Load-use safety:** EX/MEM never forwards a load's or CSR's result into an
  operand that is actually read (that value doesn't exist until MEM).
- **Stores:** a memory write only comes from a valid, non-faulting store in EX,
  never while an older instruction traps or MRETs; byte-enables are always a
  legal SB/SH/SW shape.
- **Stall:** lasts exactly one cycle; the stalled instruction stays put in ID.
- **Flushes:** a flush empties the stages it should, the next cycle.
- **Traps:** a trapping instruction doesn't write its register; the next fetch
  is mtvec (or mepc after MRET); trap and MRET never coincide.
- **Alignment:** pc and every stored PC (IF/ID, ID/EX, EX/MEM, mtvec, mepc)
  are word-aligned.
- **Reset:** empties every stage and sets pc to RESET_PC.

Covers (each reached within 5 cycles of reset, with a trace): a stall; both
operands forwarded from different stages; trap and branch in the same
cycle; MRET; a store killed by an older trap; a trap reaching WB.

**What it took.** The first k-induction attempt failed: the induction step
found an unreachable state with a misaligned `mtvec`, from which the pc
assertion breaks. Adding the stored-PC alignment invariants (true
properties in their own right) made it inductive. A tooling note:
concurrent `assert property (@(posedge clk) ...)` produced **no assert
cells at all** with this yosys-slang build. It compiled silently and checked
nothing, which was caught only by counting the assert cells. The properties
are therefore written as immediate assertions in clocked/combinational
blocks, using `$past`.

**What it is not:** these properties are about pipeline control (hazards,
flushes, stores, traps). They don't prove the core implements the ISA; that
is riscv-formal's job (Milestone 7). The ISA side is covered here by lockstep
simulation.

## 8. Mutation testing: `tb/mutate.py`

Does the regression notice bugs? Each mutant is one realistic pipeline bug,
planted in a copy of `rtl/`; every suite is run against it. ❌ = that suite
failed (caught the bug).

| Planted bug | directed | hazard | riscv-tests | random | formal |
|---|---|---|---|---|---|
| no EX/MEM forward (rs1) | ❌ | ❌ | ❌ | ❌ | · |
| no MEM/WB forward (rs2) | ❌ | ❌ | ❌ | ❌ | · |
| forward priority reversed (rs1) | ❌ | ❌ | ❌ | ❌ | · |
| x0 forwarded from EX/MEM (rs1) | · | ❌ | ❌ | ❌ | ❌ |
| no WB->ID bypass (rs2) | ❌ | ❌ | ❌ | ❌ | · |
| store data not forwarded (SW) | ❌ | ❌ | ❌ | ❌ | · |
| branch compares unforwarded rs1 | ❌ | ❌ | ❌ | ❌ | · |
| CSR write source not forwarded | · | ❌ | ❌ | ❌ | · |
| no load-use stall | ❌ | ❌ | ❌ | ❌ | ❌ |
| stall ignores CSR reads | · | ❌ | · | ❌ | ❌ |
| stall ignores rs2 | ❌ | ❌ | ❌ | ❌ | ❌ |
| stall inserts no bubble | ❌ | ❌ | ❌ | ❌ | ❌ |
| IF/ID not held on stall | ❌ | ❌ | ❌ | ❌ | ❌ |
| PC not held on stall | ❌ | ❌ | ❌ | ❌ | · |
| taken branch doesn't flush ID/EX | ❌ | ❌ | ❌ | ❌ | ❌ |
| taken branch doesn't flush IF/ID | ❌ | ❌ | ❌ | ❌ | · |
| branch beats trap in the PC mux | · | ❌ | · | ❌ | ❌ |
| store not cancelled by an older trap | · | ❌ | · | ❌ | ❌ |
| store not cancelled by an older MRET | · | · | · | ❌ | ❌ |
| faulting store still writes | · | ❌ | · | ❌ | ❌ |
| trap doesn't cancel the register write | · | ❌ | ❌ | ❌ | ❌ |
| MRET doesn't flush EX/MEM | · | ❌ | ❌ | ❌ | ❌ |
| FENCE.I doesn't refetch | · | ❌ | · | ❌ | · |
| stores don't mark rs1 as read | · | ❌ | ❌ | ❌ | · |
| branches don't mark rs2 as read | ❌ | · | · | ❌ | · |
| CSR-immediate forms mark rs1 as read | · | ❌ | · | · | · |
| faulting jump also redirects | · | · | · | · | ❌ |
| bubbles decode real controls | · | · | · | · | ❌ |

28/28 mutants killed.

What the table says:
- **No single layer catches everything.** Directed tests (written for the
  single-cycle datapath) miss 14 of 28. riscv-tests miss 10, including every
  trap-vs-store interaction, FENCE.I and the CSR-use stall. Random misses 3:
  two equivalent-looking ones, and an unnecessary stall (correct results,
  just slower).
- **Formal and simulation catch different things.** Formal misses bugs in
  the datapath values (a missing forward is still *safe* by the properties,
  just wrong), which lockstep catches. It is the only layer that catches
  "faulting jump also redirects" (the pc briefly holds a misaligned target
  that a trap then overrides: invisible to the ISA, a broken invariant
  inside) and "bubbles decode real controls" (a bubble carrying a live
  register-write control; harmless today because flushed slots hold a NOP,
  but one change away from a real bug).
- **A property is only as good as its inputs.** "Stores don't mark rs1 as
  read" survives formal: the load-use property uses the decoder's own
  `uses_rs1` signal, so a decoder bug blinds it. Simulation catches it.
- **Performance bugs need cycle checks.** "CSR-immediate forms mark rs1 as
  read" only adds a stall. It survived the first mutation run (results are
  still right) and is now caught by the false-dependency stall count added to
  `test_load_use_patterns`.

First mutation run: 24/28 caught. The four survivors led to the
false-dependency check, the MRET generator template and coverage bin
(§6), and adding formal as a column. Second run: 28/28.

Earlier, for the single-cycle core (Milestone 1): 9/9 real planted bugs
caught, plus 2 equivalent mutants (x0 read-side check removed; register
writes allowed during reset). The riscv-tests harness was checked the same way
in Milestone 2 (BLTU signed → `bltu` fails; LH sign bit → `lh`, `sh`,
`fence_i` fail; mepc off by 4 → every test fails).

## 9. Synthesis sanity

`yosys` (slang front end) `synth`, no inferred latches in either core:

| Core | Generic cells | Flip-flops |
|------|---------------|------------|
| `core_single` | 7,166 | 1,216 (1,024 of them the register file) |
| `core` (pipeline) | 9,920 | 1,902 (1,024 register file, ~880 pipeline registers + CSRs) |

## Still to do

- Unit-test YOUR TURN stubs (yours): `test_regfile.py`, `test_alu.py`, `test_immgen.py`
- `funct7` checking in the decoder and model (§6 known gap)
- riscv-formal (Milestone 7) for an ISA-level proof
