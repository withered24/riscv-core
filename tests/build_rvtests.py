"""Build the official rv32ui-p-* riscv-tests into flat binaries the testbench loads.

Replaces riscv-tests' Makefile (no `make` on this machine) with the same
compiler flags. For each test in isa/rv32ui/Makefrag it produces, in
tests/build/:

    rv32ui-p-<name>.elf    the linked program (base address 0x8000_0000)
    rv32ui-p-<name>.bin    flat image from 0x8000_0000, loaded into sim memory
    rv32ui-p-<name>.dump   disassembly: open this when a test fails
    manifest.json          {name: {"bin": path, "tohost": address}}

Usage:  python tests/build_rvtests.py      (needs env.sh / env.ps1 sourced)
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "riscv-tests"
OUT = HERE / "build"
PREFIX = "riscv-none-elf-"

# From riscv-tests isa/Makefile, with the ISA string spelled out for modern
# GCC: since GCC 12, CSR instructions (Zicsr) and FENCE.I (Zifencei) are
# separate extensions and must be named explicitly.
CFLAGS = [
    "-march=rv32i_zicsr_zifencei", "-mabi=ilp32",
    "-static", "-mcmodel=medany", "-fvisibility=hidden", "-nostdlib", "-nostartfiles",
    f"-I{SRC / 'env' / 'p'}", f"-I{SRC / 'isa' / 'macros' / 'scalar'}",
    f"-T{SRC / 'env' / 'p' / 'link.ld'}",
]


def test_names() -> list[str]:
    frag = (SRC / "isa" / "rv32ui" / "Makefrag").read_text()
    body = re.search(r"rv32ui_sc_tests\s*=\s*\\\n(.*?)\n\s*\n", frag, re.S).group(1)
    return body.replace("\\", " ").split()


def tool(name: str) -> str:
    path = shutil.which(PREFIX + name)
    if not path:
        sys.exit(f"{PREFIX}{name} not found: source env.sh (or . .\\env.ps1) first")
    return path


def build() -> dict:
    if not (SRC / "env" / "p" / "riscv_test.h").exists():
        sys.exit("riscv-tests missing: git submodule update --init --recursive")
    OUT.mkdir(exist_ok=True)
    gcc, objcopy, objdump, nm = (tool(t) for t in ("gcc", "objcopy", "objdump", "nm"))
    manifest = {}
    for name in test_names():
        full = f"rv32ui-p-{name}"
        elf, binf, dump = (OUT / f"{full}{ext}" for ext in (".elf", ".bin", ".dump"))
        subprocess.run([gcc, *CFLAGS, str(SRC / "isa" / "rv32ui" / f"{name}.S"), "-o", str(elf)],
                       check=True)
        subprocess.run([objcopy, "-O", "binary", str(elf), str(binf)], check=True)
        dump.write_text(subprocess.run([objdump, "-d", "-M", "no-aliases", str(elf)],
                                       check=True, capture_output=True, text=True).stdout)
        syms = subprocess.run([nm, str(elf)], check=True, capture_output=True, text=True).stdout
        tohost = int(re.search(r"^([0-9a-f]+) \w tohost$", syms, re.M).group(1), 16)
        manifest[full] = {"bin": str(binf), "tohost": tohost}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    m = build()
    print(f"built {len(m)} tests into {OUT}")
