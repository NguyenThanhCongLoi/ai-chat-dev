$ErrorActionPreference = "Stop"

Write-Host "1. Thu hoi key da lo va tao OpenAI API key moi."
Write-Host "2. Copy day du key moi (sk-...) vao clipboard."
Read-Host "Sau khi copy, nhan Enter de tiep tuc" | Out-Null

$temporaryEnv = Join-Path ([System.IO.Path]::GetTempPath()) ("character-chat-moderation-" + [guid]::NewGuid().ToString("N") + ".env")

try {
    $plainKey = (Get-Clipboard -Raw).Trim()
    if ($plainKey -notmatch '^sk-[A-Za-z0-9_-]{20,}$') {
        throw "OpenAI API key khong hop le. Key phai la chuoi day du bat dau bang sk-."
    }
    [System.IO.File]::WriteAllText($temporaryEnv, "OPENAI_MODERATION_API_KEY=$plainKey", [System.Text.Encoding]::ASCII)
    & modal secret create character-chat-moderation --from-dotenv $temporaryEnv --force
    if ($LASTEXITCODE -ne 0) { throw "Khong tao duoc Modal moderation secret." }
    & modal deploy modal_app.py
    if ($LASTEXITCODE -ne 0) { throw "Deploy Modal that bai." }
    Write-Host "Da kich hoat omni-moderation-latest va deploy character-chat thanh cong."
}
finally {
    Set-Clipboard -Value " "
    $plainKey = $null
    if (Test-Path -LiteralPath $temporaryEnv) {
        Remove-Item -LiteralPath $temporaryEnv -Force
    }
}
