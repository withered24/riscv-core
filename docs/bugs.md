# Bug catalog

One entry per bug: symptom, what exposed it, root cause, fix. Each one is an
interview story. Testbench bugs count too, because a wrong checker is as
dangerous as a wrong design.

| # | Where | Symptom | What exposed it | Root cause | Fix |
|---|-------|---------|-----------------|------------|-----|
| 1 | Testbench | `test_branches` and `test_jumps` failed at `addi s1, s1, 1`: core wrote `0xFFFFFFFF`, model wrote `1`. | Lockstep compare, first run of the full suite. Only failed when run *after* `test_alu_immediate_ops`. | Reset doesn't clear the register file (correct: the ISA leaves registers undefined after reset). The previous test left `s1 = 0xFFFFFFFE`; the golden model starts every test at zero. | Harness zeroes `regs[1..31]` before each program, matching the model's initial state. |
| 2 | **RTL** (`core.sv`) | `test_bubble_sort`: core fetched `0x00000000` at pc `0x18` instead of the program's instruction. | Added a read-back check after program load: word 6 was zero *after* loading, before the core ran a single instruction. | Store byte-enables weren't gated by reset. While `rst` is held, `pc` still points where the *previous* program stopped, so the core decodes whatever new instruction sits there. That was `sw t1, 24(t0)` with `t0 = 0`, so the core wrote 0 over word 6 **during reset**. Register writes were gated by `!rst`; stores weren't. | `if (mem_write && !rst)` in the store path. |
| 3 | Test coverage | Planted bug "LH sign-extends from bit 7 instead of bit 15" passed every test. | Mutation testing (deliberately breaking the RTL to check the tests notice). | Both halfwords in `test_loads_and_stores` (`0xAABB`, `0x8899`) had bit 15 = bit 7 = 1, so the wrong bit gave the right answer. | Added `0x807F7F80`: halves where bit 15 ≠ bit 7, plus matching LB cases. |

A wrong hypothesis, on the record: bug 2 first looked like the cocotb/Icarus VPI
layer aliasing the `regs[6]` and `mem[6]` handles. A 20-line probe test
disproved that (separate handles, independent writes), which pointed back to
the design.
