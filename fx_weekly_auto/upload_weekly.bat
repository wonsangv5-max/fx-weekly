@echo off
SET FX_OUTPUT_DIR=C:\Users\infomax\Downloads
SET FORCE_REUPLOAD=false

IF "%GITHUB_TOKEN%"=="" (
    echo ERROR: GITHUB_TOKEN is not set.
    pause
    exit /b 1
)

python "%~dp0upload.py"
pause
