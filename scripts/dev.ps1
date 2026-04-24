param(
  [switch]$Install
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

if (!(Test-Path "$root\.env")) {
  Copy-Item "$root\.env.example" "$root\.env"
  Write-Host "Created .env from .env.example"
}

if ($Install) {
  Push-Location "$root\backend"
  python -m pip install -r requirements.txt
  Pop-Location
  Push-Location "$root\frontend"
  npm install
  Pop-Location
}

Write-Host "Starting CRM Heal backend on http://localhost:8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

Write-Host "Starting CRM Heal frontend on http://localhost:3000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Start-Sleep -Seconds 3
Write-Host "Health check: http://localhost:8000/health"
try {
  Invoke-RestMethod "http://localhost:8000/health" | ConvertTo-Json
} catch {
  Write-Host "Backend is still starting. Open http://localhost:8000/health in a moment."
}
