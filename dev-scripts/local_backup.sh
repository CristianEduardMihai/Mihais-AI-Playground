#!/bin/bash
# Remove all __pycache__ folders
find . -type d -name "__pycache__" -print -exec rm -rf {} +
echo "All __pycache__ folders removed."

# Backup everything except .venv and .github to ../playground-backup
rsync -av --exclude='.venv' --exclude='.github' ./ ../playground-backup/
echo "Backup complete: all files except .venv and .github copied to ../playground-backup."