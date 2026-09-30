$ErrorActionPreference = "Stop"

$username = Read-Host "Ten dang nhap API docs"
$securePassword = Read-Host "Mat khau API docs" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
$temporaryEnv = Join-Path ([System.IO.Path]::GetTempPath()) ("character-chat-docs-" + [guid]::NewGuid().ToString("N") + ".env")

try {
    $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    if ($username -notmatch '^[A-Za-z0-9_.-]{3,50}$') { throw "Ten dang nhap can 3-50 ky tu." }
    if ($password.Length -lt 12) { throw "Mat khau can it nhat 12 ky tu." }
    # ASCII prevents Windows PowerShell 5.1 from prefixing the first key with
    # a UTF-8 BOM (U+FEFF), which Modal rejects as part of the variable name.
    [System.IO.File]::WriteAllLines($temporaryEnv,@("DOCS_USERNAME=$username","DOCS_PASSWORD=$password"),[System.Text.Encoding]::ASCII)
    & modal secret create character-chat-docs --from-dotenv $temporaryEnv --force
    if ($LASTEXITCODE -ne 0) { throw "Khong tao duoc Modal docs secret." }
    & modal deploy modal_app.py
    if ($LASTEXITCODE -ne 0) { throw "Deploy Modal that bai." }
    Write-Host "Da bao ve /docs va /openapi.json bang mat khau."
}
finally {
    if ($pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
    $password=$null
    if (Test-Path -LiteralPath $temporaryEnv) { Remove-Item -LiteralPath $temporaryEnv -Force }
}
