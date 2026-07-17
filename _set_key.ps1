if ([string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)) {
    Write-Error "DEEPSEEK_API_KEY is not available in this process. Load it from a secret manager or user environment."
    exit 1
}

Write-Output "DEEPSEEK_API_KEY is available in this process; no credential was read from source control."
