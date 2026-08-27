param(
    [switch]$SetUser,
    [switch]$Status
)

function Get-Last4 {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ""
    }

    return $Value.Substring([Math]::Max(0, $Value.Length - 4))
}

if ($SetUser) {
    $secureKey = Read-Host "Paste the intended DeepSeek API key" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

    try {
        $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        if ([string]::IsNullOrWhiteSpace($plainKey)) {
            Write-Error "No key was entered. The Windows user environment was not changed."
            exit 1
        }
        if ($plainKey.EndsWith("a4b1")) {
            Write-Error "Refusing to store the revoked DeepSeek key ending a4b1."
            exit 1
        }

        [Environment]::SetEnvironmentVariable(
            "DEEPSEEK_API_KEY",
            $plainKey,
            [EnvironmentVariableTarget]::User
        )
        Remove-Item Env:\DEEPSEEK_API_KEY -ErrorAction SilentlyContinue
        Remove-Item Env:\DEEPSEEK_KEY -ErrorAction SilentlyContinue
        $env:PERFUME_DEEPSEEK_API_KEY = $plainKey
        Write-Output "DEEPSEEK_API_KEY was updated in the Windows user environment. Last4: $(Get-Last4 $plainKey)"
    }
    finally {
        if ($bstr -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
    }

    exit 0
}

$userKey = [Environment]::GetEnvironmentVariable(
    "DEEPSEEK_API_KEY",
    [EnvironmentVariableTarget]::User
)

if (-not [string]::IsNullOrWhiteSpace($userKey)) {
    $env:PERFUME_DEEPSEEK_API_KEY = $userKey
}
elseif ($env:DEEPSEEK_API_KEY -and $env:DEEPSEEK_API_KEY.EndsWith("a4b1")) {
    Remove-Item Env:\DEEPSEEK_API_KEY -ErrorAction SilentlyContinue
}

if ($Status) {
    $processKey = [Environment]::GetEnvironmentVariable("DEEPSEEK_API_KEY", [EnvironmentVariableTarget]::Process)
    $projectKey = [Environment]::GetEnvironmentVariable("PERFUME_DEEPSEEK_API_KEY", [EnvironmentVariableTarget]::Process)
    Write-Output "Process DEEPSEEK_API_KEY present: $(-not [string]::IsNullOrWhiteSpace($processKey)); Last4: $(Get-Last4 $processKey)"
    Write-Output "Process PERFUME_DEEPSEEK_API_KEY present: $(-not [string]::IsNullOrWhiteSpace($projectKey)); Last4: $(Get-Last4 $projectKey)"
    Write-Output "User DEEPSEEK_API_KEY present: $(-not [string]::IsNullOrWhiteSpace($userKey)); Last4: $(Get-Last4 $userKey)"
    exit 0
}

if ([string]::IsNullOrWhiteSpace($env:PERFUME_DEEPSEEK_API_KEY)) {
    Write-Error "DEEPSEEK_API_KEY is unavailable. Configure it in the Windows user environment or a secret manager."
    exit 1
}

Write-Output "DeepSeek key was loaded into the project runtime env without reading a credential from source control."
