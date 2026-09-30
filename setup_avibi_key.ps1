$ErrorActionPreference = "Stop"

Write-Host "Hay copy day du AVIBI/AIMP API key (bat dau bang sk-) vao clipboard."
Read-Host "Sau khi copy, nhan Enter de tiep tuc" | Out-Null
$temporaryEnv = Join-Path ([System.IO.Path]::GetTempPath()) ("character-chat-" + [guid]::NewGuid().ToString("N") + ".env")

try {
    $plainKey = (Get-Clipboard -Raw).Trim()
    if ($plainKey -notmatch '^sk-[A-Za-z0-9_-]{10,}$') {
        throw "API key khong hop le. Key phai la chuoi day du bat dau bang sk-, khong phai ban bi che hoac mot ky tu *."
    }

    [System.IO.File]::WriteAllText($temporaryEnv, "AIMP_API_KEY=$plainKey", [System.Text.Encoding]::ASCII)
    & modal secret create character-chat-llm --from-dotenv $temporaryEnv --force
    if ($LASTEXITCODE -ne 0) { throw "Khong tao duoc Modal Secret." }

    & modal deploy modal_app.py
    if ($LASTEXITCODE -ne 0) { throw "Deploy Modal that bai." }

    Write-Host "Da luu key an toan va deploy character-chat thanh cong."
}
finally {
    Set-Clipboard -Value " "
    $plainKey = $null
    if (Test-Path -LiteralPath $temporaryEnv) {
        Remove-Item -LiteralPath $temporaryEnv -Force
    }
}
