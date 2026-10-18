param([Parameter(ValueFromRemainingArguments=$true)][string[]]$HugoArguments)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskHugo = Join-Path $taskRoot '.tools\hugo\hugo.exe'
if (-not (Test-Path -LiteralPath $taskHugo)) {
    $taskInstalled = Get-Command hugo -ErrorAction SilentlyContinue
    if ($taskInstalled) { $taskHugo = $taskInstalled.Source }
    else {
        $taskVersion = '0.145.0'
        $taskToolDir = Join-Path $taskRoot '.tools\hugo'
        New-Item -ItemType Directory -Force -Path $taskToolDir | Out-Null
        $taskArchive = Join-Path $taskRoot '.tools\hugo-install.zip'
        Write-Host "Downloading Hugo $taskVersion from the official GitHub release..."
        Invoke-WebRequest -Uri "https://github.com/gohugoio/hugo/releases/download/v$taskVersion/hugo_${taskVersion}_windows-amd64.zip" -OutFile $taskArchive
        Expand-Archive -LiteralPath $taskArchive -DestinationPath $taskToolDir -Force
    }
}
Push-Location $taskRoot
try { & $taskHugo @HugoArguments; if ($LASTEXITCODE -ne 0) { throw "Hugo failed with exit code $LASTEXITCODE" } }
finally { Pop-Location }
