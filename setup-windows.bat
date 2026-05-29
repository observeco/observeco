@echo off
REM ObserveCo Windows Installer
REM Run as Administrator for system-wide install

echo.
echo ========================================
echo   ObserveCo - Windows Installer
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.10+ from python.org
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Installing ObserveCo...
pip install observeco
if %errorlevel% neq 0 (
    echo ERROR: pip install failed
    pause
    exit /b 1
)

echo [2/4] Installing optional dependencies...
pip install observeco[dashboard,adapters]
if %errorlevel% neq 0 (
    echo WARNING: Optional deps install failed (non-critical)
)

echo [3/4] Running ObserveCo Doctor...
python -m observeco.cli doctor run --auto-fix
if %errorlevel% neq 0 (
    echo WARNING: Doctor check had issues (non-critical)
)

echo [4/4] Creating Start Menu shortcut...
set SCRIPT_DIR=%~dp0
set PYTHON_PATH=%SCRIPT_DIR%python.exe
set OBSERVECO_PATH=%PYTHON_PATH% -m observeco.cli

REM Create shortcut via PowerShell
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Programs') + '\ObserveCo Dashboard.lnk'); $sc.TargetPath = 'cmd.exe'; $sc.Arguments = '/c python -m observeco.cli dashboard'; $sc.WorkingDirectory = '%SCRIPT_DIR%'; $sc.Description = 'ObserveCo Dashboard'; $sc.Save()"

echo.
echo ========================================
echo   Installation complete!
echo ========================================
echo.
echo Quick start:
echo   observeco dashboard       - Launch web dashboard
echo   observeco doctor run      - Diagnose environment
echo   observeco adapters test   - Test channel connections
echo   observeco --help          - Show all commands
echo.
echo Start Menu shortcut created: ObserveCo Dashboard
echo.
pause
