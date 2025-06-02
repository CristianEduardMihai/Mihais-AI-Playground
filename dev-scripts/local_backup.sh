#!/bin/bash
# Remove all __pycache__ folders
find . -type d -name "__pycache__" -print -exec rm -rf {} +
echo "All __pycache__ folders removed."

# Backup everything except .venv and .git to ../playground-backup
rsync -av --exclude='.venv' --exclude='.git' --exclude='server-assets/persistent' ../ ../../playground-backup/
echo "Backup complete: all files except .venv and .git copied to ../../playground-backup."