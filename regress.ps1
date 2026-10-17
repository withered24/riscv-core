# Full regression in one command (PowerShell):  .\regress.ps1
#
# Sets up the tool PATH, fetches riscv-tests if this is a fresh clone, builds
# the rv32ui tests, and runs every testbench: unit tests, directed lockstep
# programs, pipeline hazard tests, the official riscv-tests, and 200
# constrained-random programs, all on both cores; then the formal proof of the
# pipeline's SVA properties. Exit code 0 = everything green.
# Extra arguments go to pytest, e.g.  .\regress.ps1 -k rv32ui  or  .\regress.ps1 -x
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    . .\env.ps1

    if (-not (Test-Path tests\riscv-tests\isa\rv64ui\add.S)) {
        Write-Host "== fetching riscv-tests (first run) =="
        git submodule update --init --recursive
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    Write-Host "== running regression =="
    python -m pytest tb/ -v @args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "== formal: k-induction proof + cover (formal/core.sby) =="
    Push-Location formal
    try { sby -f core.sby } finally { Pop-Location }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
