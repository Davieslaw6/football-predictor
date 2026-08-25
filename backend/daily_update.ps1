# daily_update.ps1
#
# Triggers a data refresh + model retrain on the running backend, via the
# /api/update endpoint. Designed to be run daily by Windows Task Scheduler.
#
# IMPORTANT: this script only works while the backend server is already
# running (uvicorn). It does NOT start the server itself. If you want
# fully unattended daily updates, either:
#   (a) keep the backend running continuously (e.g. as a Windows Service,
#       or in a terminal you leave open), and just schedule this script, or
#   (b) use daily_update_standalone.py instead, which re-fetches + retrains
#       directly without needing the server to be up.
#
# Usage (manual test):
#   powershell -ExecutionPolicy Bypass -File daily_update.ps1
#
# Task Scheduler setup:
#   1. Open Task Scheduler -> Create Basic Task
#   2. Name: "Football Predictor Daily Update"
#   3. Trigger: Daily, pick a time (e.g. 6:00 AM)
#   4. Action: Start a program
#        Program/script:  powershell.exe
#        Add arguments:   -ExecutionPolicy Bypass -File "C:\path\to\football-predictor\backend\daily_update.ps1"
#   5. Finish, then right-click the task -> Run, to test it once manually.

$ApiBase = "http://localhost:8000"

Write-Host "[$(Get-Date)] Triggering update..."

try {
    $response = Invoke-RestMethod -Uri "$ApiBase/api/update" -Method Post -ErrorAction Stop
    Write-Host "Update started: $($response.message)"
} catch {
    Write-Host "ERROR: Could not reach the backend at $ApiBase. Is uvicorn running?"
    Write-Host $_.Exception.Message
    exit 1
}

# Poll for completion (checks every 5s, times out after 5 minutes)
$maxAttempts = 60
$attempt = 0
do {
    Start-Sleep -Seconds 5
    $attempt++
    $status = Invoke-RestMethod -Uri "$ApiBase/api/update/status" -Method Get
    Write-Host "[$(Get-Date)] Status: $($status.status)"
} while ($status.status -eq "running" -and $attempt -lt $maxAttempts)

if ($status.status -eq "success") {
    Write-Host "[$(Get-Date)] Update completed successfully."
    exit 0
} else {
    Write-Host "[$(Get-Date)] Update did not complete successfully. Status: $($status.status)"
    Write-Host "Error: $($status.error)"
    exit 1
}
