# Run locally. Secure input is never echoed or passed as a command-line argument.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot '.env'
Push-Location $projectRoot
try {
    git check-ignore --quiet .env
    if ($LASTEXITCODE -ne 0) { throw 'The local .env must be ignored before storing a key.' }
    $secret = Read-Host 'Enter your Groq API key (hidden input)' -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
    try {
        $keyText = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        if ($keyText -notmatch '^gsk_[A-Za-z0-9_-]{20,}$') { throw 'Key format was not recognized. Nothing was saved.' }
        $lines = if (Test-Path -LiteralPath $envFile) { @(Get-Content -LiteralPath $envFile) } else { @() }
        $lines = @($lines | Where-Object { $_ -notmatch '^\s*GROQ_API_KEY\s*=' })
        $lines += 'GROQ_API_KEY=' + $keyText
        [IO.File]::WriteAllLines($envFile, $lines, [Text.UTF8Encoding]::new($false))
        Write-Output 'Groq key saved locally in ignored .env. No API request was made.'
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
        $keyText = $null
        $lines = $null
        $secret.Dispose()
    }
} finally { Pop-Location }
