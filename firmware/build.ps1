[CmdletBinding()]
param(
    [ValidateSet('tx', 'rx', 'all')]
    [string]$Target = 'all'
)

$ErrorActionPreference = 'Stop'
$asciiProject = 'F:\DormRadar'
if (-not (Test-Path -LiteralPath $asciiProject)) {
    $targetProject = Split-Path -Parent $PSScriptRoot
    New-Item -ItemType Junction -Path $asciiProject -Target $targetProject | Out-Null
}
$root = Join-Path $asciiProject 'firmware'
$fqbn = 'esp32:esp32:esp32c3'

$cliCandidates = @(
    'D:\Program Files\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe',
    (Join-Path $env:LOCALAPPDATA 'Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe'),
    (Join-Path $env:ProgramFiles 'Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe')
)

$arduinoCli = $cliCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $arduinoCli) {
    $command = Get-Command arduino-cli -ErrorAction SilentlyContinue
    if ($command) {
        $arduinoCli = $command.Source
    }
}

if (-not $arduinoCli) {
    throw '未找到 arduino-cli。请安装 Arduino IDE 或把 arduino-cli 加入 PATH。'
}

$targets = if ($Target -eq 'all') { @('tx', 'rx') } else { @($Target) }

foreach ($name in $targets) {
    $sketchDir = Join-Path $root "arduino\$name"
    $buildDir = Join-Path $root ".build\$name"

    Write-Host "Compiling $name ..." -ForegroundColor Cyan
    & $arduinoCli compile `
        --fqbn $fqbn `
        --build-path $buildDir `
        --warnings all `
        $sketchDir

    if ($LASTEXITCODE -ne 0) {
        throw "编译失败：$name"
    }
}

Write-Host '编译完成。' -ForegroundColor Green




