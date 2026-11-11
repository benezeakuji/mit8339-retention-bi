<#
  push_to_github.ps1 - publish this project folder to a new GitHub repository.

  Usage (from inside the unzipped project folder, in PowerShell):
      powershell -ExecutionPolicy Bypass -File .\push_to_github.ps1
      powershell -ExecutionPolicy Bypass -File .\push_to_github.ps1 -RepoName mit8339-retention-bi -Visibility public

  Needs Git for Windows. GitHub CLI (gh) is optional: with it the repo is created for you,
  without it you create an empty repo on github.com and paste its URL when asked.
#>
param(
    [string]$RepoName = "mit8339-retention-bi",
    [ValidateSet("private", "public")]
    [string]$Visibility = "private"
)

$ErrorActionPreference = "Continue"   # git and gh print progress on stderr; check exit codes instead
Set-Location -LiteralPath $PSScriptRoot

function Test-Command($name) { [bool](Get-Command $name -ErrorAction SilentlyContinue) }

# 1. Git installed?
if (-not (Test-Command git)) {
    Write-Host "Git is not installed. Install it with:  winget install --id Git.Git -e" -ForegroundColor Yellow
    Write-Host "Then close and reopen PowerShell and run this script again."
    exit 1
}

# 2. Git identity (used only for commit authorship)
if (-not (git config --global user.name))  { git config --global user.name  (Read-Host "Your name for Git commits") }
if (-not (git config --global user.email)) { git config --global user.email (Read-Host "Your GitHub email (or GitHub noreply address)") }

# 3. Local repository and first commit
if (-not (Test-Path -LiteralPath ".git")) { git init -b main | Out-Null }
git add -A
$pending = git status --porcelain
if ($pending) {
    git commit -m "MIT 8339 BI/DSS virtual lab: data pipeline, analysis, dashboard and report" | Out-Null
    Write-Host "Committed project files." -ForegroundColor Green
} else {
    Write-Host "Nothing new to commit."
}
git branch -M main

# 4. Create the GitHub repo and push
$hasRemote = (git remote) -contains "origin"
if ($hasRemote) {
    git push -u origin main
}
elseif (Test-Command gh) {
    gh auth status *> $null
    if ($LASTEXITCODE -ne 0) { gh auth login --web }
    gh repo create $RepoName "--$Visibility" --source . --remote origin --push `
        --description "MIT 8339 BI/DSS virtual lab - customer retention intelligence (BankChurners)"
}
else {
    Write-Host ""
    Write-Host "GitHub CLI not found. Do this once in your browser:" -ForegroundColor Yellow
    Write-Host "  1. Open https://github.com/new"
    Write-Host "  2. Repository name: $RepoName  ($Visibility). Do NOT add a README, .gitignore or licence."
    Write-Host "  3. Click Create repository and copy the HTTPS URL."
    $url = Read-Host "Paste the repository URL (e.g. https://github.com/you/$RepoName.git)"
    git remote add origin $url
    git push -u origin main    # a browser sign-in window opens the first time
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Push failed - read the message above (wrong URL, repo name taken, or sign-in cancelled) and run the script again." -ForegroundColor Red
    exit 1
}
$remote = git remote get-url origin
Write-Host ""
Write-Host "Done. Repository: $($remote -replace '\.git$','')" -ForegroundColor Green
Write-Host "Put this URL on the report cover (Code repository) and in Appendices A and C."
