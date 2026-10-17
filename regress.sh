#!/usr/bin/env bash
# Full regression in one command (Git Bash):  ./regress.sh
#
# Sets up the tool PATH, fetches riscv-tests if this is a fresh clone, builds
# the rv32ui tests, and runs every testbench: unit tests, directed lockstep
# programs, pipeline hazard tests, the official riscv-tests, and 200
# constrained-random programs, all on both cores; then the formal proof of the
# pipeline's SVA properties. Exit code 0 = everything green.
# Extra arguments go to pytest, e.g.  ./regress.sh -k rv32ui  or  ./regress.sh -x
set -euo pipefail
cd "$(dirname "$0")"
source ./env.sh

if [ ! -f tests/riscv-tests/isa/rv64ui/add.S ]; then
    echo "== fetching riscv-tests (first run) =="
    git submodule update --init --recursive
fi

echo "== running regression =="
python -m pytest tb/ -v "$@"

echo "== formal: k-induction proof + cover (formal/core.sby) =="
(cd formal && sby -f core.sby)
