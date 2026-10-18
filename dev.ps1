param([int]$Port = 1313)
& (Join-Path $PSScriptRoot 'scripts\hugo.ps1') server --bind 127.0.0.1 --port $Port --disableFastRender
