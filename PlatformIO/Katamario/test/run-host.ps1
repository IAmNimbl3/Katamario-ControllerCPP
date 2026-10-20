param([string]$Compiler = "$env:USERPROFILE\.platformio\packages\toolchain-gccmingw32\bin\g++.exe")
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path $PSScriptRoot -Parent
$testOutput = Join-Path $projectPath '.pio\host-tests'
New-Item -ItemType Directory -Force -Path $testOutput | Out-Null
$originalPath = $env:PATH
try {
  $env:PATH = (Split-Path $Compiler -Parent) + ';' + $originalPath
  & $Compiler -std=c++11 -Wall -Wextra -pedantic '-I' (Join-Path $projectPath 'include') (Join-Path $PSScriptRoot 'motion_host.cpp') -static -o (Join-Path $testOutput 'motion-tests.exe')
  if ($LASTEXITCODE -ne 0) { throw "Host test compilation failed: $LASTEXITCODE" }
  & (Join-Path $testOutput 'motion-tests.exe')
  if ($LASTEXITCODE -ne 0) { throw 'Motion regression failed' }
} finally {
  $env:PATH = $originalPath
}
