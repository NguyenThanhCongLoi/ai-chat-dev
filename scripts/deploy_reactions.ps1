# Keep all local temporary/download caches on D; GPU/model installation is remote.
$ErrorActionPreference = "Stop"
$reactionCache = "D:\ai_chat_char\.reaction-cache"
New-Item -ItemType Directory -Force -Path $reactionCache | Out-Null
$env:TEMP = $reactionCache
$env:TMP = $reactionCache
$env:PIP_CACHE_DIR = Join-Path $reactionCache "pip"
$env:HF_HOME = Join-Path $reactionCache "huggingface"
$env:TORCH_HOME = Join-Path $reactionCache "torch"
$env:XDG_CACHE_HOME = Join-Path $reactionCache "xdg"
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    python -m modal deploy modal_reactions.py
    if ($LASTEXITCODE -ne 0) { throw "Reaction worker deployment failed" }
} finally { Pop-Location }
