@echo off
SET FX_OUTPUT_DIR=%~dp0output

IF "%GITHUB_TOKEN%"=="" (
    echo ERROR: GITHUB_TOKEN is not set.
    echo Please run: setx GITHUB_TOKEN ghp_xxxxxxxxxxxxxxxxxxxx
    echo Then restart this window and try again.
    pause
    exit /b 1
)

python "%~dp0upload.py"
pause
