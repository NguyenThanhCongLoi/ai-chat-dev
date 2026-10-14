param([switch]$Push)
$ErrorActionPreference = "Stop"
$releaseRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $releaseRoot
try {
    $branch = git branch --show-current
    if ($LASTEXITCODE -ne 0 -or $branch -ne "selfhost/dev") {
        throw "Switch to selfhost/dev before publishing."
    }
    # Explicit release paths exclude private backups, secrets and unrelated local reports.
    $releasePaths = @(
        ".gitignore", ".dockerignore", "Dockerfile", "compose.yaml", "pyproject.toml", "README.md",
        ".github/workflows/selfhost.yml",
        "deploy/service.env.example", "deploy/nginx.conf.example",
        "scripts/service_entrypoint.py", "scripts/publish_selfhost.ps1",
        "character_chat", "frontend/src",
        "docs/ASSISTANT_DIVINATION.md", "docs/SELF_HOSTED_DEPLOYMENT.md",
        "docs/BE_SERVICE_HANDOFF.md", "docs/AI_COMPANION_SYSTEM_REPORT.md",
        "tests/test_selfhost.py", "tests/test_divination.py", "tests/test_api_contract.py", "tests/test_app.py",
        "image/tarot_tuvi/tarot.jpg", "image/tarot_tuvi/tu_vi.jpg", "image/tarot_tuvi/cards"
    )
    # Refuse a commit containing files staged for another task.
    $alreadyStaged = @(git diff --cached --name-only)
    if ($LASTEXITCODE -ne 0) { throw "Cannot inspect staged files." }
    foreach ($file in $alreadyStaged) {
        $allowed = $false
        foreach ($path in $releasePaths) {
            if ($file -eq $path -or $file.StartsWith($path + "/")) { $allowed = $true; break }
        }
        if (-not $allowed) { throw "Unrelated staged file: $file. Review the index before publishing." }
    }
    git add -- $releasePaths
    if ($LASTEXITCODE -ne 0) { throw "Staging failed." }
    git diff --cached --check
    if ($LASTEXITCODE -ne 0) { throw "Staged diff validation failed." }
    git diff --cached --stat
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 1) {
        git commit -m "Prepare standalone CPU service with Tarot and CMS updates; preserve GPU workers"
        if ($LASTEXITCODE -ne 0) { throw "Commit failed." }
    } elseif ($LASTEXITCODE -ne 0) {
        throw "Cannot inspect staged changes."
    }
    if ($Push) {
        git push -u origin selfhost/dev
        if ($LASTEXITCODE -ne 0) { throw "Push failed. The local commit is preserved." }
    } else {
        Write-Host "Local commit ready. Run git push -u origin selfhost/dev when ready."
    }
} finally {
    Pop-Location
}
