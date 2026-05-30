# Installs claude-control as a clickable Windows application.
# Run from PowerShell:  .\install.ps1
# (Right-click → Run with PowerShell. May prompt about execution policy;
#  if so:  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)

$ErrorActionPreference = "Stop"

$ProjectDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython   = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$LauncherPath = Join-Path $ProjectDir "launcher.py"
$IconPath     = Join-Path $ProjectDir "assets\icon.png"

Write-Host "▸ Installing claude-control on Windows" -ForegroundColor Cyan
Write-Host "  Project dir: $ProjectDir"
Write-Host ""

# 1. Python check
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
  Write-Host "ERROR: python not found. Install Python 3.11+ from python.org or the Microsoft Store." -ForegroundColor Red
  exit 1
}

# 2. Stop any running instance before upgrading
Write-Host "▸ Stopping running instance (if any)" -ForegroundColor Cyan
$stopScript = Join-Path $ProjectDir "launcher.py"
if (Test-Path $VenvPython) {
  & $VenvPython $stopScript --stop 2>$null
}
Start-Sleep -Seconds 1

# 3. venv
if (-not (Test-Path (Join-Path $ProjectDir ".venv"))) {
  Write-Host "▸ Creating Python venv" -ForegroundColor Cyan
  python -m venv (Join-Path $ProjectDir ".venv")
}

# 4. deps
Write-Host "▸ Installing Python dependencies" -ForegroundColor Cyan
& $VenvPython -m pip install --quiet --upgrade pip
& $VenvPython -m pip install --quiet -r (Join-Path $ProjectDir "requirements.txt")

try {
  & $VenvPython -m pip install --quiet pywebview 2>$null
  Write-Host "  ✓ pywebview installed (native window mode available)" -ForegroundColor Green
} catch {
  Write-Host "  ⚠ pywebview not installed; falling back to browser" -ForegroundColor Yellow
}

# 5. Convert PNG to ICO if magick / ImageMagick is available; else use PNG directly
$IcoPath = Join-Path $ProjectDir "assets\icon.ico"
if (-not (Test-Path $IcoPath)) {
  $magick = Get-Command magick -ErrorAction SilentlyContinue
  if ($magick) {
    & magick convert $IconPath -define icon:auto-resize=256,128,64,48,32,16 $IcoPath 2>$null
  }
}
$ShortcutIcon = if (Test-Path $IcoPath) { $IcoPath } else { $IconPath }

# 6. Start Menu shortcut
$StartMenu  = [Environment]::GetFolderPath("Programs")
$Shortcut   = Join-Path $StartMenu "Claude Control.lnk"

Write-Host "▸ Creating Start Menu shortcut" -ForegroundColor Cyan
$WshShell = New-Object -ComObject WScript.Shell
$lnk = $WshShell.CreateShortcut($Shortcut)
$lnk.TargetPath       = $VenvPython
$lnk.Arguments        = "`"$LauncherPath`""
$lnk.WorkingDirectory = $ProjectDir
$lnk.IconLocation     = $ShortcutIcon
$lnk.Description      = "Manage your ~/.claude/ skills, plugins, agents, and commands"
$lnk.WindowStyle      = 7  # minimized
$lnk.Save()

Write-Host ""
Write-Host "✓ Installed successfully." -ForegroundColor Green
Write-Host ""
Write-Host "Getting started" -ForegroundColor White
Write-Host "  1. Press the Windows key, type 'Claude Control', press Enter."
Write-Host "  2. Click the icon to launch — the dashboard opens in your browser."
Write-Host "  3. Right-click the Start Menu entry and select 'Pin to taskbar' to keep it handy."
Write-Host ""
Write-Host "Commands" -ForegroundColor White
Write-Host "  Uninstall:      powershell -File `"$ProjectDir\uninstall.ps1`""
Write-Host "  Launch via CLI: `"$VenvPython`" `"$LauncherPath`""
Write-Host "  Stop server:    `"$VenvPython`" `"$LauncherPath`" --stop"
