param(
    [string]$Message = "WIP update",
    [string]$Branch = "master"
)

$ErrorActionPreference = "Stop"

function Step($text) {
    Write-Host "==> $text" -ForegroundColor Cyan
}

function Fail($text) {
    Write-Host "ERROR: $text" -ForegroundColor Red
    exit 1
}

try {
    Step "Checking repository"
    $insideRepo = (git rev-parse --is-inside-work-tree 2>$null)
    if ($insideRepo -ne "true") {
        Fail "Current folder is not a git repository."
    }

    Step "Checking current branch"
    $currentBranch = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($currentBranch -ne $Branch) {
        Write-Host "Note: current branch is '$currentBranch' (script target '$Branch')." -ForegroundColor Yellow
        $Branch = $currentBranch
    }

    Step "Staging changes"
    git add .

    $staged = git diff --cached --name-only
    if (-not $staged) {
        Write-Host "No staged changes. Pulling latest and exiting cleanly..." -ForegroundColor Yellow
        git pull --rebase origin $Branch
        git status -sb
        exit 0
    }

    Step "Creating commit"
    git commit -m "$Message"

    Step "Pulling latest with rebase"
    git pull --rebase origin $Branch

    Step "Pushing to origin/$Branch"
    git push origin $Branch

    Step "Done"
    git status -sb
}
catch {
    Fail $_.Exception.Message
}
