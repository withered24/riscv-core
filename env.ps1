# Dot-source this in PowerShell before running tests:  . .\env.ps1
$OSS_CAD = "C:\Users\rayan\tools\oss-cad-suite"
$RISCV_GCC = "C:\Users\rayan\tools\xpack-riscv-none-elf-gcc-15.2.0-1"
$env:PATH = "$OSS_CAD\bin;$OSS_CAD\lib;$RISCV_GCC\bin;$env:PATH"
