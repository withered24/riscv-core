"""Lockstep co-simulation: run a program on the RTL core and the golden model.

Each cycle, the core's trace_* outputs (pc, instruction, register write,
memory write, trap) are compared against what the model did for the same
instruction. The first disagreement fails with the last few instructions.

Used by test_core.py (hand-written programs) and test_riscv_tests.py
(the official suite).
"""

from collections.abc import Callable

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge

from iss import ISS, MASK, Retire

MEM_WORDS = 16384                # must match sim_mem.sv's WORDS (64 KiB)

CORE_SOURCES = [
    "rtl/rv32i_pkg.sv",
    "rtl/regfile.sv",
    "rtl/immgen.sv",
    "rtl/alu.sv",
    "rtl/branch_unit.sv",
    "rtl/decoder.sv",
    "rtl/csr.sv",
    "rtl/core.sv",
    "tb/sim_mem.sv",
    "tb/tb_top.sv",
]

# Word indices written by earlier tests in this simulation; cleared before the
# next program loads, so every test starts from all-zero memory like the model.
_dirty: set[int] = set()


def u(handle) -> int:
    return int(handle.value)


def dut_reg(dut, r: int) -> int:
    return 0 if r == 0 else u(dut.u_core.u_rf.regs[r])


def dut_word(dut, addr: int) -> int:
    return u(dut.u_mem.mem[(addr >> 2) % MEM_WORDS])


def byte_mask(strb: int) -> int:
    return sum(0xFF << (8 * i) for i in range(4) if strb >> i & 1)


def words_from_bytes(data: bytes) -> list[int]:
    data += b"\0" * (-len(data) % 4)
    return [int.from_bytes(data[i:i + 4], "little") for i in range(0, len(data), 4)]


async def load_and_reset(dut, words: list[int], base: int = 0) -> None:
    """Start the clock, hold reset, load `words` at address `base`, release reset."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1

    # Reset doesn't clear the register file (the ISA leaves registers
    # undefined after reset), but the model starts at zero, so match it.
    for r in range(1, 32):
        dut.u_core.u_rf.regs[r].value = 0

    first = (base >> 2) % MEM_WORDS
    indices = [(first + i) % MEM_WORDS for i in range(len(words))]
    for i in _dirty - set(indices):        # words this program won't overwrite
        dut.u_mem.mem[i].value = 0
    _dirty.clear()
    for i, w in zip(indices, words):
        dut.u_mem.mem[i].value = w
        _dirty.add(i)

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0

    bad = [(i, w, u(dut.u_mem.mem[i])) for i, w in zip(indices, words) if u(dut.u_mem.mem[i]) != w]
    assert not bad, "program load failed (index, wanted, got): " + \
        ", ".join(f"({i}, {w:#010x}, {g:#010x})" for i, w, g in bad[:8])


async def lockstep(dut, iss: ISS, stop: Callable[[Retire], bool],
                   max_steps: int = 100_000,
                   on_trap: Callable[[Retire], None] | None = None) -> int:
    """Step core and model together until stop(retire) is true. Returns the
    number of instructions executed. on_trap, if given, sees every trap."""
    history: list[str] = []
    for step in range(max_steps):
        # Mid-cycle: the instruction at pc has settled through the datapath
        # and is about to commit at the next rising edge.
        await FallingEdge(dut.clk)
        hw_pc, hw_instr = u(dut.trace_pc), u(dut.trace_instr)
        exp = iss.step()
        history.append(f"  pc={exp.pc:#010x} instr={exp.instr:#010x}"
                       + (f"  TRAP cause={exp.cause}" if exp.trap else ""))

        def fail(what: str):
            recent = "\n".join(history[-8:])
            raise AssertionError(
                f"step {step}: {what}\n  (last instructions, newest last)\n{recent}")

        if hw_pc != exp.pc:
            fail(f"PC mismatch: core {hw_pc:#010x}, model {exp.pc:#010x}")
        if hw_instr != exp.instr:
            fail(f"instruction mismatch: core {hw_instr:#010x}, model {exp.instr:#010x}")

        hw_trap = u(dut.trace_trap)
        if hw_trap != exp.trap:
            fail(f"trap: core {hw_trap}, model {int(exp.trap)} (model cause {exp.cause})")
        if hw_trap and u(dut.trace_cause) != exp.cause:
            fail(f"trap cause: core {u(dut.trace_cause)}, model {exp.cause}")
        if exp.trap and on_trap:
            on_trap(exp)

        hw_we = u(dut.trace_rd_we)
        if hw_we != (exp.rd is not None):
            fail(f"register write-enable: core {hw_we}, model {exp.rd is not None}")
        if hw_we:
            hw_rd, hw_val = u(dut.trace_rd), u(dut.trace_rd_wdata)
            if (hw_rd, hw_val) != (exp.rd, exp.rd_val):
                fail(f"register write: core x{hw_rd}={hw_val:#010x}, "
                     f"model x{exp.rd}={exp.rd_val:#010x}")

        hw_strb = u(dut.dmem_wstrb)
        if hw_strb != exp.store_strb:
            fail(f"store byte-enables: core {hw_strb:04b}, model {exp.store_strb:04b}")
        if hw_strb:
            hw_addr = u(dut.dmem_addr) & ~3 & MASK
            m = byte_mask(hw_strb)
            hw_data = u(dut.dmem_wdata) & m
            if (hw_addr, hw_data) != (exp.store_addr & MASK, exp.store_data & m):
                fail(f"store: core [{hw_addr:#010x}]={hw_data:#010x}, "
                     f"model [{exp.store_addr:#010x}]={exp.store_data & m:#010x}")
            _dirty.add((hw_addr >> 2) % MEM_WORDS)

        if stop(exp):
            await RisingEdge(dut.clk)   # let the final cycle commit
            return step + 1

    raise AssertionError(f"program did not finish within {max_steps} instructions")
