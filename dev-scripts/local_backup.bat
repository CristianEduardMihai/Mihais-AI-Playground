@echo off
REM Remove all __pycache__ folders
for /d /r %%d in (__pycache__) do if exist "%%d" rd /s /q "%%d"
echo All __pycache__ folders removed.

REM Backup everything except .venv and .github to ..\playground-backup
robocopy . ..\playground-backup /E /XD .venv .github

echo Backup complete: all files except .venv and .github copied to ..\playground-backup.
