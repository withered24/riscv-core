# Bug catalog

One entry per bug: symptom, what exposed it, root cause, fix. Each one is an
interview story. Testbench bugs count too, because a wrong checker is as
dangerous as a wrong design.

| # | Where | Symptom | What exposed it | Root cause | Fix |
|---|-------|---------|-----------------|------------|-----|
| 1 | Testbench | `test_branches` and `test_jumps` failed at `addi s1, s1, 1`: core wrote `0xFFFFFFFF`, model wrote `1`. | Lockstep compare, first run of the full suite. Only failed when run *after* `test_alu_immediate_ops`. | Reset doesn't clear the register file (correct: the ISA leaves registers undefined after reset). The previous test left `s1 = 0xFFFFFFFE`; the golden model starts every test at zero. | Harness zeroes `regs[1..31]` before each program, matching the model's initial state. |
| 2 | **RTL** (`core.sv`, now `core_single.sv`) | `test_bubble_sort`: core fetched `0x00000000` at pc `0x18` instead of the program's instruction. | Added a read-back check after program load: word 6 was zero *after* loading, before the core ran a single instruction. | Store byte-enables weren't gated by reset. While `rst` is held, `pc` still points where the *previous* program stopped, so the core decodes whatever new instruction sits there. That was `sw t1, 24(t0)` with `t0 = 0`, so the core wrote 0 over word 6 **during reset**. Register writes were gated by `!rst`; stores weren't. | `if (mem_write && !rst)` in the store path. |
| 3 | Test coverage | Planted bug "LH sign-extends from bit 7 instead of bit 15" passed every test. | Mutation testing (deliberately breaking the RTL to check the tests notice). | Both halfwords in `test_loads_and_stores` (`0xAABB`, `0x8899`) had bit 15 = bit 7 = 1, so the wrong bit gave the right answer. | Added `0x807F7F80`: halves where bit 15 ≠ bit 7, plus matching LB cases. |
| 4 | Testbench (`cosim.py`) | riscv-tests on the single-cycle core, after moving it onto the new shared harness: "final memory [0x80001000]: core 0x00000000, model 0x00000001" on every test. | The new end-of-run check that compares every stored word against the model. | The check ran in the same cycle the last instruction retired. On the single-cycle core that instruction is the `tohost` store, which writes memory at the *next* rising edge, so the checker read memory one edge too early. The pipeline passed only because its stores land in EX, before retirement. | Let the final cycle commit (one more rising edge) before comparing, and skip words that a younger, not-yet-retired store has just written. A checker that's right for one timing and wrong for another is exactly the kind of bug that hides until the second core shows up. |
| 5 | Testbench (`test_pipeline.py` / `cosim.py`) | `test_wrong_path_is_discarded`: "a wrong-path instruction trapped" (1 trap, expected 0); `test_traps_are_precise`: 9 traps counted, 8 expected. | The per-cycle event counters in the hazard tests. A debug print of `m_pc`/`m_instr` on every `trap_m` showed the extra pulse was always at the address right after the program's final store, with `m_instr = 0x00000000`. | The word after a program is zero memory = an illegal instruction. In the last sampled cycle it has reached MEM and raises `trap_m`, but it's younger than the program's last instruction and never retires. The counters sampled every cycle, including that one. Not a core bug: trapping on an illegal word is correct; the *counter* was looking past the end of the program. | The harness stops sampling internal events on the final cycle (everything in IF..MEM is younger than the end of the program). |
| 6 | Test coverage (generator + coverage model) | Planted bug "store not cancelled by an older MRET" passed **every** simulation suite, including 200 random programs. | Mutation testing of the pipeline (`tb/mutate.py`). | The random generator's only MRET template always put an ALU instruction after the MRET, never a store. The coverage model *should* have flagged this, but its one bin counted "store killed by a trap **or** an MRET", and traps alone filled it. | Split the bin (`store_killed_by_trap` / `store_killed_by_mret`), and the MRET template now puts a store in the skipped slot 30% of the time; random catches the mutant now. The formal property `dmem_wstrb != 0 → !mret_m` catches it independently. |
| 7 | Test coverage (`test_pipeline.py`) | Planted bug "CSR-immediate forms mark rs1 as read" passed every suite. | Mutation testing. | The bug only adds stalls (a `csrrwi` whose uimm happens to equal a pending load's rd stalls for nothing). Results stay right, so lockstep can't see it, and no test counted stalls for a case that *shouldn't* stall. | `test_load_use_patterns` now includes two false dependencies (CSR uimm, and LUI immediate bits that sit where rs1 would be) and its exact stall count catches the mutant. Performance bugs need cycle-level checks; correctness checks are blind to them. |

A wrong hypothesis, on the record: bug 2 first looked like the cocotb/Icarus VPI
layer aliasing the `regs[6]` and `mem[6]` handles. A 20-line probe test
disproved that (separate handles, independent writes), which pointed back to
the design.

Near miss (tooling, not counted above): concurrent `assert property
(@(posedge clk) ...)` compiled without error under this yosys-slang build
but produced **no assert cells**: a formal check that would have passed
because it checked nothing. Caught by counting assert cells in the design
before trusting a PASS; the properties use immediate assertions in clocked
blocks instead. See verification.md §7.

## Count

7 bugs: 1 in the RTL, 3 in the testbench, 3 coverage holes. The course
target for Milestone 3 is "10+ bugs documented". This catalog stays at
the honest number rather than padding it. The pipelined core passed
lockstep, riscv-tests and the hazard tests on its first run, and the
random/coverage/formal layers found holes in the *tests*, not bugs in the
design. Mutation testing (verification.md §8) is the evidence that those
layers would have caught design bugs: 28/28 planted pipeline bugs caught.
