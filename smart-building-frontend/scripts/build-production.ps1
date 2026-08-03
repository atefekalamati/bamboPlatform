param(
  [string]$Source = (Resolve-Path "$PSScriptRoot\.."),
  [string]$Output = "$PSScriptRoot\..\dist",
  [string]$Release = $(if ($env:BAMBO_RELEASE) { $env:BAMBO_RELEASE } else { "local" }),
  [string]$ApiBaseUrl = $(if ($env:BAMBO_API_BASE_URL) { $env:BAMBO_API_BASE_URL } else { "/backend" })
)

$ErrorActionPreference = "Stop"
$outputPath = [System.IO.Path]::GetFullPath($Output)
$sourcePath = [System.IO.Path]::GetFullPath($Source)
if ($outputPath -eq $sourcePath -or -not $outputPath.StartsWith([System.IO.Path]::GetDirectoryName($sourcePath))) {
  throw "Output must be a dedicated directory next to or inside the frontend workspace."
}
if (Test-Path -LiteralPath $outputPath) { Remove-Item -LiteralPath $outputPath -Recurse -Force }
New-Item -ItemType Directory -Path $outputPath | Out-Null
Copy-Item -LiteralPath "$sourcePath\index.html" -Destination $outputPath
Copy-Item -LiteralPath "$sourcePath\src" -Destination $outputPath -Recurse
Remove-Item -LiteralPath "$outputPath\src\documents" -Recurse -Force -ErrorAction SilentlyContinue
$config = @"
window.__APP_CONFIG__ = Object.freeze({
  apiBaseUrl: "$ApiBaseUrl",
  environment: "production",
  release: "$Release",
  requestTimeoutMs: 30000,
});
"@
[System.IO.File]::WriteAllText("$outputPath\runtime-config.js", $config, [System.Text.UTF8Encoding]::new($false))
$forbidden = Get-ChildItem $outputPath -Recurse -File | Select-String -Pattern 'useMockApi\s*:\s*true|127\.0\.0\.1|localhost|debug_code\s*:'
if ($forbidden) { $forbidden | ForEach-Object { Write-Error "Forbidden production value: $($_.Path):$($_.LineNumber)" }; exit 1 }
Write-Output "Production artifact created: $outputPath (release $Release)"
