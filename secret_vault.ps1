param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("save", "view", "restore")]
    [string]$Action
)

$ErrorActionPreference = "Stop"
$vaultPath = Join-Path $PSScriptRoot "secrets.vault.json"

function Read-PlainSecret([string]$Prompt) {
    $secure = Read-Host $Prompt -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

function Read-ClipboardValue([string]$Prompt) {
    Write-Host $Prompt
    Read-Host "Copy gia tri vao clipboard roi nhan Enter; de trong neu khong muon luu" | Out-Null
    $clipboard=Get-Clipboard -Raw
    $value=if ($null -eq $clipboard) { "" } else { $clipboard.Trim() }
    Set-Clipboard -Value " "
    if ([string]::IsNullOrWhiteSpace($value)) { Write-Host "Bo qua, khong luu gia tri nay." }
    else { Write-Host "Da nhan gia tri co do dai $($value.Length) ky tu." }
    return $value
}

function Derive-Key([string]$Password, [byte[]]$Salt) {
    $derive = New-Object Security.Cryptography.Rfc2898DeriveBytes($Password, $Salt, 200000, [Security.Cryptography.HashAlgorithmName]::SHA256)
    try { return $derive.GetBytes(32) }
    finally { $derive.Dispose() }
}

function Encrypt-Text([string]$Text, [string]$Password) {
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    $salt = New-Object byte[] 16
    $rng.GetBytes($salt)
    $rng.Dispose()
    $key = Derive-Key $Password $salt
    try {
        $secure = ConvertTo-SecureString $Text -AsPlainText -Force
        $cipher = ConvertFrom-SecureString $secure -Key $key
        return @{ version=1; salt=[Convert]::ToBase64String($salt); ciphertext=$cipher }
    }
    finally { [Array]::Clear($key, 0, $key.Length) }
}

function Decrypt-Text($Vault, [string]$Password) {
    $salt = [Convert]::FromBase64String($Vault.salt)
    $key = Derive-Key $Password $salt
    try {
        $secure = ConvertTo-SecureString $Vault.ciphertext -Key $key
        $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
        finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
    }
    finally { [Array]::Clear($key, 0, $key.Length) }
}

if ($Action -eq "save") {
    Write-Host "Nhap lai cac secret hien tai. Gia tri se chi duoc luu duoi dang ma hoa."
    $master1 = Read-PlainSecret "Mat khau chinh cho vault (toi thieu 8 ky tu)"
    $master2 = Read-PlainSecret "Nhap lai mat khau chinh"
    if ($master1.Length -lt 8) { throw "Mat khau vault can it nhat 8 ky tu." }
    if ($master1 -cne $master2) { throw "Hai mat khau vault khong khop." }

    $data = [ordered]@{
        AIMP_API_KEY = Read-ClipboardValue "Copy AVIBI/AIMP API key"
        OPENAI_MODERATION_API_KEY = Read-ClipboardValue "Copy OpenAI Moderation API key"
        DOCS_USERNAME = Read-Host "API docs username"
        DOCS_PASSWORD = Read-PlainSecret "API docs password"
    }
    $encrypted = Encrypt-Text ($data | ConvertTo-Json -Compress) $master1
    $encrypted | ConvertTo-Json | Set-Content -LiteralPath $vaultPath -Encoding ASCII
    Write-Host "Da tao vault ma hoa: $vaultPath"
    $master1=$null; $master2=$null; $data=$null
    exit 0
}

if (-not (Test-Path -LiteralPath $vaultPath)) { throw "Khong tim thay $vaultPath" }
$master = Read-PlainSecret "Mat khau chinh cua vault"
try {
    $vault = Get-Content -LiteralPath $vaultPath -Raw | ConvertFrom-Json
    $plain = Decrypt-Text $vault $master
    $data = $plain | ConvertFrom-Json
} catch { throw "Khong mo duoc vault. Mat khau sai hoac file bi hong." }

if ($Action -eq "view") {
    Write-Host "`n===== CHARACTER CHAT SECRET VAULT ====="
    Write-Host "AIMP_API_KEY=$(if($data.AIMP_API_KEY){$data.AIMP_API_KEY}else{'(khong luu)'})"
    Write-Host "OPENAI_MODERATION_API_KEY=$(if($data.OPENAI_MODERATION_API_KEY){$data.OPENAI_MODERATION_API_KEY}else{'(khong luu)'})"
    Write-Host "DOCS_USERNAME=$(if($data.DOCS_USERNAME){$data.DOCS_USERNAME}else{'(khong luu)'})"
    Write-Host "DOCS_PASSWORD=$(if($data.DOCS_PASSWORD){$data.DOCS_PASSWORD}else{'(khong luu)'})"
    Write-Host "=======================================`n"
    Write-Warning "Cac gia tri dang hien ro tren man hinh. Dong terminal sau khi xem xong."
    $plain=$null; $data=$null; $master=$null
    exit 0
}

$tempDir = Join-Path ([IO.Path]::GetTempPath()) ("character-chat-vault-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir | Out-Null
try {
    if (-not [string]::IsNullOrWhiteSpace($data.AIMP_API_KEY)) {
        [IO.File]::WriteAllText((Join-Path $tempDir "llm.env"), "AIMP_API_KEY=$($data.AIMP_API_KEY)", [Text.Encoding]::ASCII)
        & modal secret create character-chat-llm --from-dotenv (Join-Path $tempDir "llm.env") --force
        if ($LASTEXITCODE -ne 0) { throw "Khong khoi phuc duoc LLM secret." }
    }
    if (-not [string]::IsNullOrWhiteSpace($data.OPENAI_MODERATION_API_KEY)) {
        [IO.File]::WriteAllText((Join-Path $tempDir "moderation.env"), "OPENAI_MODERATION_API_KEY=$($data.OPENAI_MODERATION_API_KEY)", [Text.Encoding]::ASCII)
        & modal secret create character-chat-moderation --from-dotenv (Join-Path $tempDir "moderation.env") --force
        if ($LASTEXITCODE -ne 0) { throw "Khong khoi phuc duoc moderation secret." }
    }
    if (-not [string]::IsNullOrWhiteSpace($data.DOCS_USERNAME) -and -not [string]::IsNullOrWhiteSpace($data.DOCS_PASSWORD)) {
        [IO.File]::WriteAllLines((Join-Path $tempDir "docs.env"), @("DOCS_USERNAME=$($data.DOCS_USERNAME)", "DOCS_PASSWORD=$($data.DOCS_PASSWORD)"), [Text.Encoding]::ASCII)
        & modal secret create character-chat-docs --from-dotenv (Join-Path $tempDir "docs.env") --force
        if ($LASTEXITCODE -ne 0) { throw "Khong khoi phuc duoc docs secret." }
    }
    & modal deploy modal_app.py
    if ($LASTEXITCODE -ne 0) { throw "Khoi phuc xong secret nhung deploy that bai." }
    Write-Host "Da khoi phuc tat ca Modal Secret va deploy app."
}
finally {
    $plain=$null; $data=$null; $master=$null
    if (Test-Path -LiteralPath $tempDir) { Remove-Item -LiteralPath $tempDir -Recurse -Force }
}
