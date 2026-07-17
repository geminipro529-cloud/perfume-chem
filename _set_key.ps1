$userKey = [Environment]::GetEnvironmentVariable(
    "DEEPSEEK_API_KEY",
    [EnvironmentVariableTarget]::User
)

if (-not [string]::IsNullOrWhiteSpace($userKey)) {
    $env:DEEPSEEK_API_KEY = $userKey
}

if ([string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)) {
    Write-Error "DEEPSEEK_API_KEY is unavailable. Configure it in the Windows user environment or a secret manager."
    exit 1
}

Write-Output "DEEPSEEK_API_KEY was loaded into this process without reading a credential from source control."
