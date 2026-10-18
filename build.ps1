param([string]$BaseURL = '')
if ($BaseURL) { & (Join-Path $PSScriptRoot 'scripts\hugo.ps1') --gc --minify --cleanDestinationDir --baseURL $BaseURL }
else { & (Join-Path $PSScriptRoot 'scripts\hugo.ps1') --gc --minify --cleanDestinationDir }
