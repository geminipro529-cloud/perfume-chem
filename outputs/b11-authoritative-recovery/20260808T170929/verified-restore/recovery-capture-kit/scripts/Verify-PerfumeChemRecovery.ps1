[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$CaptureRoot
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function Get-FullPathSafe {
    param([string]$Path)
    return [System.IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($Path))
}

$CaptureRoot = Get-FullPathSafe $CaptureRoot
$manifestPath = Join-Path $CaptureRoot '04_MANIFESTS\FULL_FILE_MANIFEST.csv'
$sealPath = Join-Path $CaptureRoot '04_MANIFESTS\CAPTURE_SHA256SUMS.csv'
$reportPath = Join-Path $CaptureRoot '04_MANIFESTS\VERIFICATION_REPORT.json'

if (-not (Test-Path -LiteralPath $manifestPath)) { throw "Missing manifest: $manifestPath" }

$missing = New-Object System.Collections.Generic.List[object]
$mismatches = New-Object System.Collections.Generic.List[object]
$verified = 0
foreach ($row in (Import-Csv -LiteralPath $manifestPath)) {
    $path = Join-Path $CaptureRoot $row.StoredRelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $missing.Add([pscustomobject]@{ StoredRelativePath=$row.StoredRelativePath; ExpectedSHA256=$row.SHA256 })
        continue
    }
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $row.SHA256.ToLowerInvariant()) {
        $mismatches.Add([pscustomobject]@{ StoredRelativePath=$row.StoredRelativePath; ExpectedSHA256=$row.SHA256; ActualSHA256=$actual })
    }
    else { $verified++ }
}

$sealMissing = New-Object System.Collections.Generic.List[object]
$sealMismatches = New-Object System.Collections.Generic.List[object]
$sealVerified = 0
if (Test-Path -LiteralPath $sealPath) {
    foreach ($row in (Import-Csv -LiteralPath $sealPath)) {
        $path = Join-Path $CaptureRoot $row.RelativePath
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            $sealMissing.Add([pscustomobject]@{ RelativePath=$row.RelativePath; ExpectedSHA256=$row.SHA256 })
            continue
        }
        $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $row.SHA256.ToLowerInvariant()) {
            $sealMismatches.Add([pscustomobject]@{ RelativePath=$row.RelativePath; ExpectedSHA256=$row.SHA256; ActualSHA256=$actual })
        }
        else { $sealVerified++ }
    }
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zipResults = New-Object System.Collections.Generic.List[object]
$chunksRoot = Join-Path $CaptureRoot '07_UPLOAD_CHUNKS'
if (Test-Path -LiteralPath $chunksRoot) {
    foreach ($zip in (Get-ChildItem -LiteralPath $chunksRoot -Filter '*.zip' -File)) {
        $state = 'PASS'
        $errorText = ''
        $entries = 0
        try {
            $archive = [System.IO.Compression.ZipFile]::OpenRead($zip.FullName)
            try {
                $buffer = New-Object byte[] 1048576
                foreach ($entry in $archive.Entries) {
                    $entries++
                    $stream = $entry.Open()
                    try { while ($stream.Read($buffer, 0, $buffer.Length) -gt 0) { } }
                    finally { $stream.Dispose() }
                }
            }
            finally { $archive.Dispose() }
        }
        catch {
            $state = 'FAIL'
            $errorText = $_.Exception.Message
        }
        $zipResults.Add([pscustomobject]@{
            Zip = $zip.Name
            Entries = $entries
            CRCReadState = $state
            Error = $errorText
            SHA256 = (Get-FileHash -LiteralPath $zip.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        })
    }
}

$report = [ordered]@{
    verified_utc = [DateTime]::UtcNow.ToString('o')
    capture_root = $CaptureRoot
    source_manifest_verified = $verified
    source_manifest_missing = $missing.Count
    source_manifest_mismatches = $mismatches.Count
    sealed_metadata_verified = $sealVerified
    sealed_metadata_missing = $sealMissing.Count
    sealed_metadata_mismatches = $sealMismatches.Count
    upload_zip_count = $zipResults.Count
    upload_zip_crc_failures = @($zipResults | Where-Object { $_.CRCReadState -ne 'PASS' }).Count
    overall_state = if ($missing.Count -eq 0 -and $mismatches.Count -eq 0 -and $sealMissing.Count -eq 0 -and $sealMismatches.Count -eq 0 -and @($zipResults | Where-Object { $_.CRCReadState -ne 'PASS' }).Count -eq 0) { 'PASS' } else { 'FAIL' }
    source_missing_records = $missing
    source_mismatch_records = $mismatches
    sealed_missing_records = $sealMissing
    sealed_mismatch_records = $sealMismatches
    zip_results = $zipResults
}
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "Verification state: $($report.overall_state)"
Write-Host "Report: $reportPath"
if ($report.overall_state -ne 'PASS') { exit 1 }
