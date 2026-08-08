[CmdletBinding()]
param(
    [string]$DownloadsPath = "",
    [string]$RepoPath = "",
    [string]$AdditionalPathsCsv = "",
    [string]$DestinationRoot = "",
    [int]$UploadChunkMB = 1500,
    [switch]$SkipDownloadsCopy,
    [switch]$SkipUploadChunks,
    [switch]$IncludeExecutableBinariesInUpload,
    [switch]$NonInteractive
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 78) -ForegroundColor DarkCyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host ("=" * 78) -ForegroundColor DarkCyan
}

function Get-FullPathSafe {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return "" }
    return [System.IO.Path]::GetFullPath((Expand-EnvironmentVariables $Path))
}

function Expand-EnvironmentVariables {
    param([string]$Path)
    return [Environment]::ExpandEnvironmentVariables($Path)
}

function Test-PathInside {
    param([string]$Candidate, [string]$Parent)
    $candidateFull = (Get-FullPathSafe $Candidate).TrimEnd('\') + '\'
    $parentFull = (Get-FullPathSafe $Parent).TrimEnd('\') + '\'
    return $candidateFull.StartsWith($parentFull, [System.StringComparison]::OrdinalIgnoreCase)
}

function Get-RelativePathCompat {
    param([string]$BasePath, [string]$FullPath)
    $base = (Get-FullPathSafe $BasePath).TrimEnd('\') + '\'
    $full = Get-FullPathSafe $FullPath
    if ($full.StartsWith($base, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $full.Substring($base.Length)
    }
    return [System.IO.Path]::GetFileName($full)
}

function Sanitize-Name {
    param([string]$Name)
    $invalid = [System.IO.Path]::GetInvalidFileNameChars()
    $result = $Name
    foreach ($char in $invalid) {
        $result = $result.Replace([string]$char, '_')
    }
    $result = $result -replace '\s+', '_'
    if ([string]::IsNullOrWhiteSpace($result)) { return "unnamed" }
    return $result
}

function Get-DirectoryStats {
    param([string]$Path)
    [long]$bytes = 0
    [long]$files = 0
    try {
        foreach ($item in (Get-ChildItem -LiteralPath $Path -File -Recurse -Force -ErrorAction SilentlyContinue)) {
            $files++
            $bytes += $item.Length
        }
    }
    catch { }
    return [pscustomobject]@{ Path=$Path; FileCount=$files; Bytes=$bytes }
}

function Invoke-RobocopySnapshot {
    param(
        [string]$Source,
        [string]$Destination,
        [string]$LogPath
    )
    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        throw "Source directory does not exist: $Source"
    }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $arguments = @(
        $Source,
        $Destination,
        '*',
        '/E',
        '/COPY:DAT',
        '/DCOPY:DAT',
        '/R:2',
        '/W:2',
        '/XJ',
        '/FFT',
        '/NP',
        '/TEE',
        "/LOG:$LogPath"
    )
    & robocopy @arguments
    $code = $LASTEXITCODE
    if ($code -ge 8) {
        throw "Robocopy failed with exit code $code. See $LogPath"
    }
    return $code
}

function Invoke-CommandCapture {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$OutputPath,
        [string]$WorkingDirectory = ""
    )
    $old = Get-Location
    try {
        if (-not [string]::IsNullOrWhiteSpace($WorkingDirectory)) {
            Set-Location -LiteralPath $WorkingDirectory
        }
        $all = & $FilePath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
        @(
            "COMMAND: $FilePath $($Arguments -join ' ')",
            "EXIT_CODE: $exitCode",
            "CAPTURED_UTC: $([DateTime]::UtcNow.ToString('o'))",
            "",
            ($all | Out-String)
        ) | Set-Content -LiteralPath $OutputPath -Encoding UTF8
        return $exitCode
    }
    catch {
        @(
            "COMMAND: $FilePath $($Arguments -join ' ')",
            "CAPTURED_UTC: $([DateTime]::UtcNow.ToString('o'))",
            "ERROR: $($_.Exception.Message)"
        ) | Set-Content -LiteralPath $OutputPath -Encoding UTF8
        return 999
    }
    finally {
        Set-Location $old
    }
}

function Invoke-GitPatchCapture {
    param(
        [string]$Repo,
        [string[]]$DiffArguments,
        [string]$PatchPath,
        [string]$ReceiptPath
    )
    try {
        $lines = & git -C $Repo @DiffArguments 2>&1
        $exitCode = $LASTEXITCODE
        $text = ($lines | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
        if (-not [string]::IsNullOrEmpty($text)) { $text += [Environment]::NewLine }
        [System.IO.File]::WriteAllText($PatchPath, $text, (New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $false))
        @(
            "COMMAND: git -C $Repo $($DiffArguments -join ' ')",
            "EXIT_CODE: $exitCode",
            "CAPTURED_UTC: $([DateTime]::UtcNow.ToString('o'))",
            "PATCH_SHA256: $((Get-FileHash -LiteralPath $PatchPath -Algorithm SHA256).Hash.ToLowerInvariant())"
        ) | Set-Content -LiteralPath $ReceiptPath -Encoding UTF8
        return $exitCode
    }
    catch {
        @(
            "COMMAND: git -C $Repo $($DiffArguments -join ' ')",
            "CAPTURED_UTC: $([DateTime]::UtcNow.ToString('o'))",
            "ERROR: $($_.Exception.Message)"
        ) | Set-Content -LiteralPath $ReceiptPath -Encoding UTF8
        return 999
    }
}

function Test-SecretPath {
    param([string]$Path)
    $name = [System.IO.Path]::GetFileName($Path)
    $normalized = $Path.Replace('/', '\')
    $patterns = @(
        '(?i)(^|[\\/])\.env($|\.)',
        '(?i)(api[-_. ]?key|openai[-_. ]?api|secret|client_secret|access[-_. ]?token|refresh[-_. ]?token|credential|password|passwd)',
        '(?i)(^|[\\/])id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$',
        '(?i)\.(pem|pfx|p12|key|kdbx)$',
        '(?i)(auth|credentials?|secrets?)\.json$',
        '(?i)(github|gitlab|azure|aws|gcp)[-_. ]?(token|key|credential)'
    )
    foreach ($pattern in $patterns) {
        if ($normalized -match $pattern -or $name -match $pattern) { return $true }
    }
    return $false
}

function Test-SecretContent {
    param([string]$Path)
    $textExtensions = @(
        '.txt','.md','.csv','.json','.jsonl','.yaml','.yml','.toml','.ini','.cfg','.conf',
        '.ps1','.psm1','.py','.js','.ts','.jsx','.tsx','.sh','.bat','.cmd','.env','.xml','.html','.htm'
    )
    $extension = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
    if ($textExtensions -notcontains $extension -and [System.IO.Path]::GetFileName($Path) -notmatch '(?i)^\.env') {
        return $false
    }
    try {
        $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        try {
            $maxBytes = 131072
            $buffer = New-Object byte[] $maxBytes
            $read = $stream.Read($buffer, 0, $buffer.Length)
            if ($read -le 0) { return $false }
            $text = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $read)
            $patterns = @(
                '(?i)\bsk-[A-Za-z0-9_-]{20,}\b',
                '(?i)\bgithub_pat_[A-Za-z0-9_]{20,}\b',
                '(?i)\bgh[pousr]_[A-Za-z0-9]{20,}\b',
                '\bAKIA[0-9A-Z]{16}\b',
                '\bAIza[0-9A-Za-z_-]{30,}\b',
                '-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
                '(?i)OPENAI_API_KEY\s*[:=]\s*["'']?[^\s"'']{16,}',
                '(?i)(api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*["'']?[^\s"'']{16,}'
            )
            foreach ($pattern in $patterns) {
                if ($text -match $pattern) { return $true }
            }
        }
        finally {
            $stream.Dispose()
        }
    }
    catch {
        return $false
    }
    return $false
}

function Test-ResearchCandidate {
    param([string]$Path)
    $extension = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
    $allowedExtensions = @(
        '.zip','.7z','.rar','.tar','.gz','.bz2','.xz',
        '.xlsx','.xls','.xlsm','.ods','.csv','.tsv',
        '.json','.jsonl','.ndjson','.schema','.yaml','.yml','.toml','.xml',
        '.md','.txt','.docx','.doc','.pdf','.rtf','.html','.htm',
        '.py','.ipynb','.ps1','.psm1','.sh','.bat','.cmd','.js','.ts','.sql',
        '.patch','.diff','.sha256','.log','.ini','.cfg','.conf','.lock',
        '.sqlite','.sqlite3','.db','.duckdb','.parquet','.feather','.pkl','.pickle',
        '.png','.jpg','.jpeg','.webp','.tif','.tiff','.svg',
        '.mzml','.mzxml','.cdf','.raw'
    )
    if ($allowedExtensions -contains $extension) { return $true }
    $keywords = '(?i)(perfume|perfumery|fragrance|accord|aroma|odor|olfact|prada|dior|amouage|chanel|ysl|violet|orris|iris|floral|woody|amber|musk|hedonic|complexity|crossbrand|program[_ -]?v3|pcv3|cp6|xhigh|inventory|formula|reconstruction|citrus|sandalwood|vetiver|jasmine|rose|tuberose|muguet|osmanthus|immortelle|lavender|counterbrand|layton|sauvage|l[_'' -]?homme|opus|batch|pilot|interaction|sensory|headspace|oav|truth|stock|lineage|microevent|flanker|reverif|verification)'
    return ($Path -match $keywords)
}

function Get-UploadExclusionReason {
    param(
        [string]$Path,
        [bool]$SuspectedSecret,
        [bool]$ResearchCandidate,
        [bool]$AllowExecutables
    )
    if ($SuspectedSecret) { return "SUSPECTED_SECRET__PRIVATE_ONLY" }
    if (-not $ResearchCandidate) { return "NOT_CLASSIFIED_AS_RESEARCH" }
    $normalized = $Path.Replace('/', '\')
    $excludedDirectories = '(?i)(^|[\\/])(node_modules|\.venv|venv|__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|\.cache|site-packages|\.git)([\\/]|$)'
    if ($normalized -match $excludedDirectories) { return "CACHE_OR_DEPENDENCY_TREE" }
    $extension = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
    $binaryExtensions = @('.exe','.msi','.msix','.appx','.appxbundle','.dll','.sys','.cab','.iso','.vhd','.vhdx','.dmg','.pkg','.gguf','.safetensors','.ckpt','.pt','.pth','.onnx')
    if ((-not $AllowExecutables) -and ($binaryExtensions -contains $extension)) {
        return "EXECUTABLE_OR_MODEL_BINARY__OFFLINE_ONLY"
    }
    return ""
}

function Move-SecretsToPrivateArea {
    param(
        [string]$SnapshotRoot,
        [string]$PrivateRoot,
        [string]$SourceClass
    )
    $records = New-Object System.Collections.Generic.List[object]
    if (-not (Test-Path -LiteralPath $SnapshotRoot)) { return $records }
    $files = Get-ChildItem -LiteralPath $SnapshotRoot -File -Recurse -Force -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        $pathFlag = Test-SecretPath $file.FullName
        $contentFlag = $false
        if (-not $pathFlag) { $contentFlag = Test-SecretContent $file.FullName }
        if ($pathFlag -or $contentFlag) {
            $relative = Get-RelativePathCompat $SnapshotRoot $file.FullName
            $destination = Join-Path (Join-Path $PrivateRoot $SourceClass) $relative
            $destinationDirectory = Split-Path -Parent $destination
            New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null
            $sha = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            Move-Item -LiteralPath $file.FullName -Destination $destination -Force
            $records.Add([pscustomobject]@{
                SourceClass = $SourceClass
                OriginalRelativePath = $relative
                StoredPrivateRelativePath = Get-RelativePathCompat $PrivateRoot $destination
                Length = $file.Length
                LastWriteTimeUtc = $file.LastWriteTimeUtc.ToString('o')
                SHA256 = $sha
                Detection = if ($pathFlag -and $contentFlag) { "PATH_AND_CONTENT" } elseif ($pathFlag) { "PATH" } else { "CONTENT" }
                UploadAllowed = $false
            })
        }
    }
    return $records
}

function Get-RootFileRecords {
    param(
        [string]$CaptureRoot,
        [string]$StoredRoot,
        [string]$SourceClass,
        [string]$OriginalSource,
        [bool]$AllowExecutables
    )
    $records = New-Object System.Collections.Generic.List[object]
    if (-not (Test-Path -LiteralPath $StoredRoot)) { return $records }
    $files = Get-ChildItem -LiteralPath $StoredRoot -File -Recurse -Force -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        $relative = Get-RelativePathCompat $StoredRoot $file.FullName
        $storedRelative = Get-RelativePathCompat $CaptureRoot $file.FullName
        $secret = (Test-SecretPath $file.FullName) -or (Test-SecretContent $file.FullName)
        $research = Test-ResearchCandidate $file.FullName
        $reason = Get-UploadExclusionReason -Path $file.FullName -SuspectedSecret:$secret -ResearchCandidate:$research -AllowExecutables:$AllowExecutables
        $sha = ""
        $hashState = "OK"
        try {
            $sha = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
        catch {
            $hashState = "ERROR: $($_.Exception.Message)"
        }
        $records.Add([pscustomobject]@{
            StoredRelativePath = $storedRelative
            SourceClass = $SourceClass
            OriginalSourceRoot = $OriginalSource
            OriginalRelativePath = $relative
            FileName = $file.Name
            Extension = $file.Extension.ToLowerInvariant()
            Length = $file.Length
            CreationTimeUtc = $file.CreationTimeUtc.ToString('o')
            LastWriteTimeUtc = $file.LastWriteTimeUtc.ToString('o')
            SHA256 = $sha
            HashState = $hashState
            SuspectedSecret = $secret
            ResearchCandidate = $research
            UploadEligible = [string]::IsNullOrWhiteSpace($reason)
            UploadExclusionReason = $reason
        })
    }
    return $records
}

function Copy-EligibleToStaging {
    param(
        [object[]]$Records,
        [string]$CaptureRoot,
        [string]$StagingRoot
    )
    $copied = New-Object System.Collections.Generic.List[object]
    foreach ($record in $Records) {
        if (-not $record.UploadEligible) { continue }
        $source = Join-Path $CaptureRoot $record.StoredRelativePath
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { continue }
        $namespace = Sanitize-Name $record.SourceClass
        $destination = Join-Path (Join-Path $StagingRoot $namespace) $record.OriginalRelativePath
        $destinationDirectory = Split-Path -Parent $destination
        New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
        try {
            (Get-Item -LiteralPath $destination).CreationTimeUtc = [DateTime]::Parse($record.CreationTimeUtc).ToUniversalTime()
            (Get-Item -LiteralPath $destination).LastWriteTimeUtc = [DateTime]::Parse($record.LastWriteTimeUtc).ToUniversalTime()
        }
        catch { }
        $copied.Add([pscustomobject]@{
            StagingRelativePath = Get-RelativePathCompat $StagingRoot $destination
            SourceClass = $record.SourceClass
            OriginalRelativePath = $record.OriginalRelativePath
            Length = $record.Length
            SHA256 = $record.SHA256
        })
    }
    return $copied
}

function New-ZipChunks {
    param(
        [string]$StagingRoot,
        [string]$ChunksRoot,
        [long]$ChunkBytes
    )
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    New-Item -ItemType Directory -Force -Path $ChunksRoot | Out-Null
    $files = Get-ChildItem -LiteralPath $StagingRoot -File -Recurse -Force | Sort-Object FullName
    $groups = New-Object System.Collections.Generic.List[object]
    $current = New-Object System.Collections.Generic.List[object]
    [long]$currentSize = 0
    foreach ($file in $files) {
        if ($current.Count -gt 0 -and ($currentSize + $file.Length) -gt $ChunkBytes) {
            $groups.Add($current.ToArray())
            $current = New-Object System.Collections.Generic.List[object]
            $currentSize = 0
        }
        $current.Add($file)
        $currentSize += $file.Length
    }
    if ($current.Count -gt 0) { $groups.Add($current.ToArray()) }

    $memberRecords = New-Object System.Collections.Generic.List[object]
    $chunkRecords = New-Object System.Collections.Generic.List[object]
    $index = 0
    foreach ($group in $groups) {
        $index++
        $zipName = "PerfumeChem_Research_Recovery_{0:D3}.zip" -f $index
        $zipPath = Join-Path $ChunksRoot $zipName
        if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
        $archive = [System.IO.Compression.ZipFile]::Open($zipPath, [System.IO.Compression.ZipArchiveMode]::Create)
        try {
            foreach ($file in $group) {
                $relative = (Get-RelativePathCompat $StagingRoot $file.FullName).Replace('\','/')
                [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                    $archive,
                    $file.FullName,
                    $relative,
                    [System.IO.Compression.CompressionLevel]::Optimal
                ) | Out-Null
                $memberRecords.Add([pscustomobject]@{
                    Chunk = $zipName
                    RelativePath = $relative
                    Length = $file.Length
                    SHA256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
                })
            }
        }
        finally {
            $archive.Dispose()
        }

        $crcState = "PASS"
        $crcError = ""
        try {
            $check = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
            try {
                $buffer = New-Object byte[] 1048576
                foreach ($entry in $check.Entries) {
                    $stream = $entry.Open()
                    try {
                        while ($stream.Read($buffer, 0, $buffer.Length) -gt 0) { }
                    }
                    finally { $stream.Dispose() }
                }
            }
            finally { $check.Dispose() }
        }
        catch {
            $crcState = "FAIL"
            $crcError = $_.Exception.Message
        }
        $zipFile = Get-Item -LiteralPath $zipPath
        $chunkRecords.Add([pscustomobject]@{
            Chunk = $zipName
            FileCount = @($group).Count
            UncompressedBytes = (@($group) | Measure-Object Length -Sum).Sum
            ZipBytes = $zipFile.Length
            SHA256 = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
            CRCReadState = $crcState
            CRCError = $crcError
        })
    }
    return [pscustomobject]@{
        Members = $memberRecords
        Chunks = $chunkRecords
    }
}

function Match-RecoveryTargets {
    param(
        [object[]]$ManifestRecords,
        [string]$RegistersRoot
    )
    $results = New-Object System.Collections.Generic.List[object]

    $missingPath = Join-Path $RegistersRoot 'MISSING_EXACT_BYTES_REGISTER.csv'
    if (Test-Path -LiteralPath $missingPath) {
        foreach ($target in (Import-Csv -LiteralPath $missingPath)) {
            $expectedName = $target.filename
            $expectedHash = $target.known_sha256
            $matches = @($ManifestRecords | Where-Object { $_.FileName -ieq $expectedName })
            if ($matches.Count -eq 0) {
                $results.Add([pscustomobject]@{
                    TargetSource = 'MISSING_EXACT_BYTES_REGISTER'
                    TargetNameOrPattern = $expectedName
                    ExpectedSHA256 = $expectedHash
                    MatchState = 'NOT_FOUND'
                    FoundStoredRelativePath = ''
                    FoundSHA256 = ''
                })
            }
            else {
                foreach ($match in $matches) {
                    $state = if ([string]::IsNullOrWhiteSpace($expectedHash)) { 'NAME_FOUND_HASH_UNSPECIFIED' } elseif ($match.SHA256 -ieq $expectedHash) { 'EXACT_NAME_AND_HASH' } else { 'NAME_FOUND_HASH_MISMATCH' }
                    $results.Add([pscustomobject]@{
                        TargetSource = 'MISSING_EXACT_BYTES_REGISTER'
                        TargetNameOrPattern = $expectedName
                        ExpectedSHA256 = $expectedHash
                        MatchState = $state
                        FoundStoredRelativePath = $match.StoredRelativePath
                        FoundSHA256 = $match.SHA256
                    })
                }
            }
        }
    }

    $visiblePath = Join-Path $RegistersRoot 'VISIBLE_UNMOUNTED_BATCHES_REGISTER.csv'
    if (Test-Path -LiteralPath $visiblePath) {
        foreach ($target in (Import-Csv -LiteralPath $visiblePath)) {
            $pattern = $target.filename_or_pattern
            $matches = @($ManifestRecords | Where-Object { $_.FileName -like $pattern })
            if ($matches.Count -eq 0) {
                $results.Add([pscustomobject]@{
                    TargetSource = 'VISIBLE_UNMOUNTED_BATCHES_REGISTER'
                    TargetNameOrPattern = $pattern
                    ExpectedSHA256 = ''
                    MatchState = 'NOT_FOUND'
                    FoundStoredRelativePath = ''
                    FoundSHA256 = ''
                })
            }
            else {
                foreach ($match in $matches) {
                    $results.Add([pscustomobject]@{
                        TargetSource = 'VISIBLE_UNMOUNTED_BATCHES_REGISTER'
                        TargetNameOrPattern = $pattern
                        ExpectedSHA256 = ''
                        MatchState = 'NAME_OR_PATTERN_FOUND'
                        FoundStoredRelativePath = $match.StoredRelativePath
                        FoundSHA256 = $match.SHA256
                    })
                }
            }
        }
    }

    $queuePath = Join-Path $RegistersRoot 'FILE_LIBRARY_EXACT_PACKAGE_RECOVERY_QUEUE.csv'
    if (Test-Path -LiteralPath $queuePath) {
        foreach ($target in (Import-Csv -LiteralPath $queuePath)) {
            $expectedName = $target.filename
            $expectedHash = $target.sha256
            $matches = @($ManifestRecords | Where-Object { $_.FileName -ieq $expectedName })
            if ($matches.Count -eq 0) {
                $results.Add([pscustomobject]@{
                    TargetSource = 'FILE_LIBRARY_EXACT_PACKAGE_RECOVERY_QUEUE'
                    TargetNameOrPattern = $expectedName
                    ExpectedSHA256 = $expectedHash
                    MatchState = 'NOT_FOUND'
                    FoundStoredRelativePath = ''
                    FoundSHA256 = ''
                })
            }
            else {
                foreach ($match in $matches) {
                    $state = if ([string]::IsNullOrWhiteSpace($expectedHash)) { 'NAME_FOUND_HASH_UNSPECIFIED' } elseif ($match.SHA256 -ieq $expectedHash) { 'EXACT_NAME_AND_HASH' } else { 'NAME_FOUND_HASH_MISMATCH' }
                    $results.Add([pscustomobject]@{
                        TargetSource = 'FILE_LIBRARY_EXACT_PACKAGE_RECOVERY_QUEUE'
                        TargetNameOrPattern = $expectedName
                        ExpectedSHA256 = $expectedHash
                        MatchState = $state
                        FoundStoredRelativePath = $match.StoredRelativePath
                        FoundSHA256 = $match.SHA256
                    })
                }
            }
        }
    }
    return $results
}

Write-Section "Perfume-Chem lossless recovery capture"
Write-Host "This operation is non-destructive. It copies, hashes, indexes, and packages research files."
Write-Host "It does not modify the source Downloads folder or repository."
Write-Host "Suspected credentials are moved only inside the private recovery copy and are never staged for upload." -ForegroundColor Yellow

if ([string]::IsNullOrWhiteSpace($DownloadsPath)) {
    $DownloadsPath = Join-Path $env:USERPROFILE 'Downloads'
}
if ([string]::IsNullOrWhiteSpace($DestinationRoot) -and -not $NonInteractive) {
    $DestinationRoot = Read-Host "Destination directory on another drive or protected storage"
}
if ([string]::IsNullOrWhiteSpace($DestinationRoot)) {
    throw "DestinationRoot is required. Prefer an external drive with ample free space."
}
if ([string]::IsNullOrWhiteSpace($RepoPath) -and -not $NonInteractive) {
    $RepoPath = Read-Host "Path to the local perfume-chem repository, or press Enter to skip"
}
if ([string]::IsNullOrWhiteSpace($AdditionalPathsCsv) -and -not $NonInteractive) {
    $AdditionalPathsCsv = Read-Host "Additional project folders separated by semicolons, or press Enter"
}

$DownloadsPath = Get-FullPathSafe $DownloadsPath
$DestinationRoot = Get-FullPathSafe $DestinationRoot
if (-not [string]::IsNullOrWhiteSpace($RepoPath)) { $RepoPath = Get-FullPathSafe $RepoPath }
$additionalPaths = @()
if (-not [string]::IsNullOrWhiteSpace($AdditionalPathsCsv)) {
    $additionalPaths = @($AdditionalPathsCsv -split ';' | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { Get-FullPathSafe $_ })
}

if (-not $SkipDownloadsCopy -and -not (Test-Path -LiteralPath $DownloadsPath -PathType Container)) {
    throw "Downloads folder not found: $DownloadsPath"
}
if (-not [string]::IsNullOrWhiteSpace($RepoPath) -and -not (Test-Path -LiteralPath $RepoPath -PathType Container)) {
    throw "Repository folder not found: $RepoPath"
}
foreach ($path in $additionalPaths) {
    if (-not (Test-Path -LiteralPath $path -PathType Container)) { throw "Additional folder not found: $path" }
}

$sourceRoots = New-Object System.Collections.Generic.List[string]
if (-not $SkipDownloadsCopy) { $sourceRoots.Add($DownloadsPath) }
if (-not [string]::IsNullOrWhiteSpace($RepoPath)) { $sourceRoots.Add($RepoPath) }
foreach ($path in $additionalPaths) { $sourceRoots.Add($path) }
foreach ($source in $sourceRoots) {
    if (Test-PathInside -Candidate $DestinationRoot -Parent $source) {
        throw "Destination cannot be inside a source directory: $source"
    }
}
if ($DestinationRoot -match '(?i)(OneDrive|Dropbox|Google Drive|iCloud)') {
    Write-Warning "Destination appears cloud-synchronized. A private external drive is safer for the full forensic copy."
}

Write-Section "Preflight source size and destination capacity"
$sourceStats = New-Object System.Collections.Generic.List[object]
foreach ($source in $sourceRoots) {
    $stat = Get-DirectoryStats -Path $source
    $sourceStats.Add($stat)
    Write-Host ("{0}: {1:N0} files, {2:N2} GB" -f $source, $stat.FileCount, ($stat.Bytes / 1GB))
}
[long]$sourceBytes = ($sourceStats | Measure-Object Bytes -Sum).Sum
[long]$estimatedWorkingBytes = [Math]::Ceiling(($sourceBytes * 2.5) + 2GB)
$driveRoot = [System.IO.Path]::GetPathRoot($DestinationRoot)
$freeBytes = $null
if (-not [string]::IsNullOrWhiteSpace($driveRoot)) {
    try {
        $driveInfo = New-Object -TypeName System.IO.DriveInfo -ArgumentList $driveRoot
        if ($driveInfo.IsReady) { $freeBytes = [long]$driveInfo.AvailableFreeSpace }
    }
    catch { }
}
if ($freeBytes -ne $null) {
    Write-Host ("Available destination space: {0:N2} GB" -f ($freeBytes / 1GB))
    Write-Host ("Conservative working estimate: {0:N2} GB" -f ($estimatedWorkingBytes / 1GB))
    if ($freeBytes -lt $estimatedWorkingBytes) {
        $message = "Destination may not have enough space for the forensic copy, staging tree, and chunks."
        if ($NonInteractive) { throw $message }
        Write-Warning $message
        $answer = Read-Host "Type CONTINUE to proceed anyway, or anything else to stop"
        if ($answer -cne 'CONTINUE') { throw "Stopped before copying because destination capacity is insufficient." }
    }
}

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$captureRoot = Join-Path $DestinationRoot "PerfumeChem_Recovery_$timestamp"
$metadataRoot = Join-Path $captureRoot '00_METADATA'
$downloadsCopy = Join-Path $captureRoot '01_DOWNLOADS_FORENSIC_COPY'
$repoCopy = Join-Path $captureRoot '02_REPO_FORENSIC_COPY'
$additionalCopyRoot = Join-Path $captureRoot '02B_ADDITIONAL_FORENSIC_COPIES'
$gitRoot = Join-Path $captureRoot '03_GIT_FORENSICS'
$manifestRoot = Join-Path $captureRoot '04_MANIFESTS'
$stagingRoot = Join-Path $captureRoot '06_UPLOAD_STAGING'
$chunksRoot = Join-Path $captureRoot '07_UPLOAD_CHUNKS'
$privateRoot = Join-Path $captureRoot '99_PRIVATE_LOCAL_ONLY_DO_NOT_UPLOAD'
$logsRoot = Join-Path $metadataRoot 'logs'
$registersRoot = Join-Path $metadataRoot 'recovery_registers'

foreach ($directory in @($metadataRoot,$logsRoot,$manifestRoot,$stagingRoot,$privateRoot,$registersRoot)) {
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
}

Copy-Item -Path (Join-Path $PSScriptRoot '..\registers\*') -Destination $registersRoot -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Scan-PerfumeChemArchives.py') -Destination $metadataRoot -Force -ErrorAction SilentlyContinue

$systemMetadata = [ordered]@{
    capture_id = "PerfumeChem_Recovery_$timestamp"
    started_utc = [DateTime]::UtcNow.ToString('o')
    computer_name = $env:COMPUTERNAME
    user_name = $env:USERNAME
    powershell_version = $PSVersionTable.PSVersion.ToString()
    downloads_path = $DownloadsPath
    repo_path = $RepoPath
    additional_paths = $additionalPaths
    destination_root = $DestinationRoot
    capture_root = $captureRoot
    upload_chunk_mb = $UploadChunkMB
    preservation_policy = "LOSSLESS_COPY_HASH_INDEX__NO_SOURCE_MUTATION"
    secret_policy = "PRIVATE_LOCAL_QUARANTINE__NEVER_UPLOAD"
}
$systemMetadata | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $metadataRoot 'CAPTURE_CONTEXT.json') -Encoding UTF8
$sourceStats | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $metadataRoot 'SOURCE_PREFLIGHT_STATS.json') -Encoding UTF8

Write-Section "Copying source folders"
$copyRecords = New-Object System.Collections.Generic.List[object]
if (-not $SkipDownloadsCopy) {
    $code = Invoke-RobocopySnapshot -Source $DownloadsPath -Destination $downloadsCopy -LogPath (Join-Path $logsRoot 'robocopy_downloads.log')
    $copyRecords.Add([pscustomobject]@{ SourceClass='Downloads'; Source=$DownloadsPath; Destination=$downloadsCopy; RobocopyExitCode=$code })
}
if (-not [string]::IsNullOrWhiteSpace($RepoPath)) {
    $code = Invoke-RobocopySnapshot -Source $RepoPath -Destination $repoCopy -LogPath (Join-Path $logsRoot 'robocopy_repo.log')
    $copyRecords.Add([pscustomobject]@{ SourceClass='Repo'; Source=$RepoPath; Destination=$repoCopy; RobocopyExitCode=$code })
}
$additionalIndex = 0
$additionalMappings = New-Object System.Collections.Generic.List[object]
foreach ($path in $additionalPaths) {
    $additionalIndex++
    $leaf = Sanitize-Name ([System.IO.Path]::GetFileName($path.TrimEnd('\')))
    $class = "Additional_{0:D2}_{1}" -f $additionalIndex, $leaf
    $destination = Join-Path $additionalCopyRoot $class
    $code = Invoke-RobocopySnapshot -Source $path -Destination $destination -LogPath (Join-Path $logsRoot ("robocopy_{0}.log" -f $class))
    $copyRecords.Add([pscustomobject]@{ SourceClass=$class; Source=$path; Destination=$destination; RobocopyExitCode=$code })
    $additionalMappings.Add([pscustomobject]@{ SourceClass=$class; OriginalSource=$path; StoredRoot=$destination })
}
$copyRecords | Export-Csv -LiteralPath (Join-Path $metadataRoot 'COPY_OPERATIONS.csv') -NoTypeInformation -Encoding UTF8

Write-Section "Capturing Git state"
if (-not [string]::IsNullOrWhiteSpace($RepoPath)) {
    New-Item -ItemType Directory -Force -Path $gitRoot | Out-Null
    $gitCommands = @(
        @{ Name='rev_parse_toplevel'; Args=@('-C',$RepoPath,'rev-parse','--show-toplevel') },
        @{ Name='branch_current'; Args=@('-C',$RepoPath,'branch','--show-current') },
        @{ Name='head_sha'; Args=@('-C',$RepoPath,'rev-parse','HEAD') },
        @{ Name='remotes'; Args=@('-C',$RepoPath,'remote','-v') },
        @{ Name='status_porcelain_v2'; Args=@('-C',$RepoPath,'status','--porcelain=v2','-uall') },
        @{ Name='status_full'; Args=@('-C',$RepoPath,'status','--short','--branch') },
        @{ Name='branches'; Args=@('-C',$RepoPath,'branch','-a','-vv') },
        @{ Name='tags'; Args=@('-C',$RepoPath,'tag','--list') },
        @{ Name='stashes'; Args=@('-C',$RepoPath,'stash','list') },
        @{ Name='reflog_all'; Args=@('-C',$RepoPath,'reflog','--all','--date=iso') },
        @{ Name='worktrees'; Args=@('-C',$RepoPath,'worktree','list','--porcelain') },
        @{ Name='untracked'; Args=@('-C',$RepoPath,'ls-files','--others','--exclude-standard') },
        @{ Name='ignored'; Args=@('-C',$RepoPath,'ls-files','--others','-i','--exclude-standard') },
        @{ Name='log_all_graph'; Args=@('-C',$RepoPath,'log','--all','--decorate','--oneline','--graph','-n','5000') },
        @{ Name='fsck_unreachable'; Args=@('-C',$RepoPath,'fsck','--full','--unreachable','--no-reflogs') }
    )
    foreach ($command in $gitCommands) {
        Invoke-CommandCapture -FilePath 'git' -Arguments $command.Args -OutputPath (Join-Path $gitRoot ($command.Name + '.txt')) | Out-Null
    }
    Invoke-GitPatchCapture -Repo $RepoPath -DiffArguments @('diff','--binary') -PatchPath (Join-Path $gitRoot 'worktree_binary.patch') -ReceiptPath (Join-Path $gitRoot 'worktree_binary_patch_receipt.txt') | Out-Null
    Invoke-GitPatchCapture -Repo $RepoPath -DiffArguments @('diff','--cached','--binary') -PatchPath (Join-Path $gitRoot 'index_binary.patch') -ReceiptPath (Join-Path $gitRoot 'index_binary_patch_receipt.txt') | Out-Null
    Invoke-CommandCapture -FilePath 'git' -Arguments @('-C',$RepoPath,'bundle','create',(Join-Path $gitRoot 'repository_all_refs.bundle'),'--all') -OutputPath (Join-Path $gitRoot 'bundle_create_receipt.txt') | Out-Null
    Invoke-CommandCapture -FilePath 'git' -Arguments @('-C',$RepoPath,'archive','--format=zip','--output',(Join-Path $gitRoot 'HEAD_tracked_tree.zip'),'HEAD') -OutputPath (Join-Path $gitRoot 'git_archive_receipt.txt') | Out-Null
}
else {
    "Repository path not supplied. Git forensic capture skipped." | Set-Content -LiteralPath (Join-Path $metadataRoot 'GIT_CAPTURE_SKIPPED.txt') -Encoding UTF8
}

Write-Section "Quarantining credentials inside the private local copy"
$secretRecords = New-Object System.Collections.Generic.List[object]
if (-not $SkipDownloadsCopy) {
    foreach ($record in (Move-SecretsToPrivateArea -SnapshotRoot $downloadsCopy -PrivateRoot $privateRoot -SourceClass 'Downloads')) { $secretRecords.Add($record) }
}
if (-not [string]::IsNullOrWhiteSpace($RepoPath)) {
    foreach ($record in (Move-SecretsToPrivateArea -SnapshotRoot $repoCopy -PrivateRoot $privateRoot -SourceClass 'Repo')) { $secretRecords.Add($record) }
}
foreach ($mapping in $additionalMappings) {
    foreach ($record in (Move-SecretsToPrivateArea -SnapshotRoot $mapping.StoredRoot -PrivateRoot $privateRoot -SourceClass $mapping.SourceClass)) { $secretRecords.Add($record) }
}
$secretRecords | Export-Csv -LiteralPath (Join-Path $manifestRoot 'SECRET_QUARANTINE_INDEX_PRIVATE.csv') -NoTypeInformation -Encoding UTF8
@(
    "PRIVATE LOCAL AREA. DO NOT UPLOAD.",
    "Credentials and suspected credentials were separated from the research copy.",
    "Rotate any exposed API key before continuing.",
    "Files in this directory are excluded from upload staging and chunks."
) | Set-Content -LiteralPath (Join-Path $privateRoot 'DO_NOT_UPLOAD.txt') -Encoding UTF8

Write-Section "Hashing and indexing all copied files"
$manifestRecords = New-Object System.Collections.Generic.List[object]
if (-not $SkipDownloadsCopy) {
    foreach ($record in (Get-RootFileRecords -CaptureRoot $captureRoot -StoredRoot $downloadsCopy -SourceClass 'Downloads' -OriginalSource $DownloadsPath -AllowExecutables:$IncludeExecutableBinariesInUpload)) { $manifestRecords.Add($record) }
}
if (-not [string]::IsNullOrWhiteSpace($RepoPath)) {
    foreach ($record in (Get-RootFileRecords -CaptureRoot $captureRoot -StoredRoot $repoCopy -SourceClass 'Repo' -OriginalSource $RepoPath -AllowExecutables:$IncludeExecutableBinariesInUpload)) { $manifestRecords.Add($record) }
    foreach ($record in (Get-RootFileRecords -CaptureRoot $captureRoot -StoredRoot $gitRoot -SourceClass 'GitForensics' -OriginalSource $RepoPath -AllowExecutables:$IncludeExecutableBinariesInUpload)) { $manifestRecords.Add($record) }
}
foreach ($mapping in $additionalMappings) {
    foreach ($record in (Get-RootFileRecords -CaptureRoot $captureRoot -StoredRoot $mapping.StoredRoot -SourceClass $mapping.SourceClass -OriginalSource $mapping.OriginalSource -AllowExecutables:$IncludeExecutableBinariesInUpload)) { $manifestRecords.Add($record) }
}
foreach ($record in (Get-RootFileRecords -CaptureRoot $captureRoot -StoredRoot $privateRoot -SourceClass 'PRIVATE_LOCAL_ONLY' -OriginalSource 'Separated suspected credentials' -AllowExecutables:$false)) {
    $record.UploadEligible = $false
    $record.UploadExclusionReason = 'PRIVATE_LOCAL_ONLY_DO_NOT_UPLOAD'
    $manifestRecords.Add($record)
}

$manifestPath = Join-Path $manifestRoot 'FULL_FILE_MANIFEST.csv'
$manifestRecords | Sort-Object StoredRelativePath | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding UTF8

$publicManifestPath = Join-Path $manifestRoot 'PUBLIC_RESEARCH_MANIFEST.csv'
$publicManifestRecords = @($manifestRecords | Where-Object { $_.UploadEligible } | Select-Object SourceClass,OriginalRelativePath,FileName,Extension,Length,CreationTimeUtc,LastWriteTimeUtc,SHA256,HashState,ResearchCandidate,UploadEligible)
$publicManifestRecords | Sort-Object SourceClass,OriginalRelativePath | Export-Csv -LiteralPath $publicManifestPath -NoTypeInformation -Encoding UTF8

$excludedSummary = @($manifestRecords | Where-Object { -not $_.UploadEligible } | Group-Object UploadExclusionReason | ForEach-Object {
    [pscustomobject]@{
        ExclusionReason = $_.Name
        FileCount = $_.Count
        TotalBytes = ($_.Group | Measure-Object Length -Sum).Sum
    }
})
$excludedSummary | Export-Csv -LiteralPath (Join-Path $manifestRoot 'EXCLUDED_FILE_COUNTS.csv') -NoTypeInformation -Encoding UTF8

$duplicateRecords = New-Object System.Collections.Generic.List[object]
$groups = $manifestRecords | Where-Object { -not [string]::IsNullOrWhiteSpace($_.SHA256) } | Group-Object SHA256 | Where-Object { $_.Count -gt 1 }
foreach ($group in $groups) {
    foreach ($item in $group.Group) {
        $duplicateRecords.Add([pscustomobject]@{
            SHA256 = $group.Name
            AliasCount = $group.Count
            SourceClass = $item.SourceClass
            StoredRelativePath = $item.StoredRelativePath
            OriginalRelativePath = $item.OriginalRelativePath
            Length = $item.Length
        })
    }
}
$duplicateRecords | Export-Csv -LiteralPath (Join-Path $manifestRoot 'DUPLICATE_ALIASES_BY_SHA256.csv') -NoTypeInformation -Encoding UTF8

$publicDuplicateRecords = New-Object System.Collections.Generic.List[object]
$publicGroups = $manifestRecords | Where-Object { $_.UploadEligible -and -not [string]::IsNullOrWhiteSpace($_.SHA256) } | Group-Object SHA256 | Where-Object { $_.Count -gt 1 }
foreach ($group in $publicGroups) {
    foreach ($item in $group.Group) {
        $publicDuplicateRecords.Add([pscustomobject]@{
            SHA256 = $group.Name
            AliasCount = $group.Count
            SourceClass = $item.SourceClass
            OriginalRelativePath = $item.OriginalRelativePath
            Length = $item.Length
        })
    }
}
$publicDuplicateRecords | Export-Csv -LiteralPath (Join-Path $manifestRoot 'PUBLIC_DUPLICATE_ALIASES_BY_SHA256.csv') -NoTypeInformation -Encoding UTF8

$targetMatches = Match-RecoveryTargets -ManifestRecords $manifestRecords -RegistersRoot $registersRoot
$targetMatches | Export-Csv -LiteralPath (Join-Path $manifestRoot 'RECOVERY_TARGET_MATCHES.csv') -NoTypeInformation -Encoding UTF8

$summary = [ordered]@{
    capture_id = "PerfumeChem_Recovery_$timestamp"
    total_files = $manifestRecords.Count
    total_bytes = ($manifestRecords | Measure-Object Length -Sum).Sum
    unique_sha256 = @($manifestRecords | Where-Object { $_.SHA256 } | Select-Object -ExpandProperty SHA256 -Unique).Count
    duplicate_hash_groups = @($groups).Count
    secret_files_private_only = $secretRecords.Count
    research_candidates = @($manifestRecords | Where-Object { $_.ResearchCandidate }).Count
    upload_eligible = @($manifestRecords | Where-Object { $_.UploadEligible }).Count
    upload_excluded = @($manifestRecords | Where-Object { -not $_.UploadEligible }).Count
    target_exact_hash_matches = @($targetMatches | Where-Object { $_.MatchState -eq 'EXACT_NAME_AND_HASH' }).Count
    target_name_matches = @($targetMatches | Where-Object { $_.MatchState -match 'FOUND' }).Count
    targets_not_found = @($targetMatches | Where-Object { $_.MatchState -eq 'NOT_FOUND' }).Count
    source_mutations = 0
}
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $manifestRoot 'CAPTURE_SUMMARY.json') -Encoding UTF8

Write-Section "Building upload staging"
$staged = Copy-EligibleToStaging -Records $manifestRecords -CaptureRoot $captureRoot -StagingRoot $stagingRoot
$staged | Export-Csv -LiteralPath (Join-Path $manifestRoot 'UPLOAD_STAGING_MANIFEST.csv') -NoTypeInformation -Encoding UTF8

$controlRoot = Join-Path $stagingRoot '_RECOVERY_CONTROL'
New-Item -ItemType Directory -Force -Path $controlRoot | Out-Null
foreach ($file in @(
    'PUBLIC_RESEARCH_MANIFEST.csv',
    'PUBLIC_DUPLICATE_ALIASES_BY_SHA256.csv',
    'EXCLUDED_FILE_COUNTS.csv',
    'RECOVERY_TARGET_MATCHES.csv',
    'UPLOAD_STAGING_MANIFEST.csv',
    'CAPTURE_SUMMARY.json'
)) {
    Copy-Item -LiteralPath (Join-Path $manifestRoot $file) -Destination $controlRoot -Force
}
Copy-Item -LiteralPath $registersRoot -Destination (Join-Path $controlRoot 'recovery_registers') -Recurse -Force
@(
    "This upload staging tree excludes suspected credentials, dependency caches, and nonresearch binaries.",
    "The private local-only area is not included.",
    "Original relative paths are preserved under source-class namespaces.",
    "The private local FULL_FILE_MANIFEST.csv retains every copied file. Upload chunks contain only the sanitized public research manifest."
) | Set-Content -LiteralPath (Join-Path $controlRoot 'UPLOAD_SCOPE_README.txt') -Encoding UTF8

$stagingSecretFailures = New-Object System.Collections.Generic.List[string]
foreach ($file in (Get-ChildItem -LiteralPath $stagingRoot -File -Recurse -Force)) {
    if ((Test-SecretPath $file.FullName) -or (Test-SecretContent $file.FullName)) {
        $stagingSecretFailures.Add((Get-RelativePathCompat $stagingRoot $file.FullName))
    }
}
if ($stagingSecretFailures.Count -gt 0) {
    $stagingSecretFailures | Set-Content -LiteralPath (Join-Path $manifestRoot 'UPLOAD_STAGING_SECRET_FAILURES.txt') -Encoding UTF8
    throw "Fail-closed: suspected secret detected in upload staging. No chunks were created. Review UPLOAD_STAGING_SECRET_FAILURES.txt"
}

if (-not $SkipUploadChunks) {
    Write-Section "Creating upload ZIP chunks"
    $chunkResult = New-ZipChunks -StagingRoot $stagingRoot -ChunksRoot $chunksRoot -ChunkBytes ([long]$UploadChunkMB * 1MB)
    $chunkResult.Members | Export-Csv -LiteralPath (Join-Path $manifestRoot 'UPLOAD_CHUNK_MEMBERS.csv') -NoTypeInformation -Encoding UTF8
    $chunkResult.Chunks | Export-Csv -LiteralPath (Join-Path $manifestRoot 'UPLOAD_CHUNKS.csv') -NoTypeInformation -Encoding UTF8
}
else {
    "Upload chunk creation skipped by parameter." | Set-Content -LiteralPath (Join-Path $metadataRoot 'UPLOAD_CHUNKS_SKIPPED.txt') -Encoding UTF8
}

Write-Section "Running recursive archive scanner when Python is available"
$scannerPath = Join-Path $metadataRoot 'Scan-PerfumeChemArchives.py'
$pythonCommand = $null
foreach ($candidate in @('py','python','python3')) {
    try {
        & $candidate --version *> $null
        if ($LASTEXITCODE -eq 0) { $pythonCommand = $candidate; break }
    }
    catch { }
}
if ($pythonCommand -and (Test-Path -LiteralPath $scannerPath)) {
    $archiveOutput = Join-Path $manifestRoot 'ARCHIVE_SCAN'
    New-Item -ItemType Directory -Force -Path $archiveOutput | Out-Null
    $arguments = @($scannerPath,'--root',$captureRoot,'--output',$archiveOutput,'--registers',$registersRoot,'--max-depth','12')
    & $pythonCommand @arguments 2>&1 | Tee-Object -FilePath (Join-Path $logsRoot 'archive_scanner.log')
}
else {
    "Python not found. Run Scan-PerfumeChemArchives.py later against the capture root." | Set-Content -LiteralPath (Join-Path $metadataRoot 'ARCHIVE_SCAN_SKIPPED.txt') -Encoding UTF8
}

Write-Section "Sealing capture metadata"
$sealRecords = New-Object System.Collections.Generic.List[object]
$sealRoots = @($metadataRoot,$manifestRoot,$chunksRoot)
foreach ($root in $sealRoots) {
    if (-not (Test-Path -LiteralPath $root)) { continue }
    foreach ($file in (Get-ChildItem -LiteralPath $root -File -Recurse -Force | Sort-Object FullName)) {
        if ($file.Name -eq 'CAPTURE_SHA256SUMS.csv') { continue }
        $sealRecords.Add([pscustomobject]@{
            RelativePath = Get-RelativePathCompat $captureRoot $file.FullName
            Length = $file.Length
            SHA256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        })
    }
}
$sealRecords | Export-Csv -LiteralPath (Join-Path $manifestRoot 'CAPTURE_SHA256SUMS.csv') -NoTypeInformation -Encoding UTF8

$completion = [ordered]@{
    capture_id = "PerfumeChem_Recovery_$timestamp"
    completed_utc = [DateTime]::UtcNow.ToString('o')
    capture_root = $captureRoot
    full_manifest = (Join-Path $manifestRoot 'FULL_FILE_MANIFEST.csv')
    recovery_target_matches = (Join-Path $manifestRoot 'RECOVERY_TARGET_MATCHES.csv')
    secret_private_index = (Join-Path $manifestRoot 'SECRET_QUARANTINE_INDEX_PRIVATE.csv')
    upload_staging = $stagingRoot
    upload_chunks = if ($SkipUploadChunks) { $null } else { $chunksRoot }
    verify_command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\Verify-PerfumeChemRecovery.ps1`" -CaptureRoot `"$captureRoot`""
    source_mutations = 0
}
$completion | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $captureRoot 'RECOVERY_CAPTURE_COMPLETE.json') -Encoding UTF8

Write-Section "Capture complete"
Write-Host "Capture root: $captureRoot" -ForegroundColor Green
Write-Host "Upload only the ZIPs in: $chunksRoot" -ForegroundColor Green
Write-Host "Do not upload: $privateRoot" -ForegroundColor Yellow
Write-Host "Review target matches: $(Join-Path $manifestRoot 'RECOVERY_TARGET_MATCHES.csv')"
Write-Host "Review full manifest: $manifestPath"
Write-Host "The source Downloads folder and repository were not modified." -ForegroundColor Green
