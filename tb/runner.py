"""Shared cocotb runner: build an RTL top-level with Icarus and run a test module.

Every tb/test_*.py ends with a small pytest function that calls run(), so
`pytest tb/` from the repo root runs the whole regression.
"""

from pathlib import Path

from cocotb_tools.runner import get_runner

REPO = Path(__file__).resolve().parent.parent


def run(toplevel: str, sources: list[str], test_module: str, waves: bool = True,
        parameters: dict | None = None, build_name: str | None = None):
    """sources are paths relative to the repo root, in compile order
    (packages first). build_name keeps differently-parameterized builds of
    the same top level apart."""
    build_dir = REPO / "sim_build" / (build_name or toplevel)
    runner = get_runner("icarus")
    runner.build(
        sources=[REPO / s for s in sources],
        hdl_toplevel=toplevel,
        build_dir=build_dir,
        timescale=("1ns", "1ps"),
        parameters=parameters or {},
        waves=waves,
        always=True,
    )
    runner.test(
        hdl_toplevel=toplevel,
        test_module=test_module,
        test_dir=Path(__file__).resolve().parent,
        build_dir=build_dir,
        waves=waves,
    )
