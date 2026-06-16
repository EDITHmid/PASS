#!/usr/bin/env bash
# Render build script for the PASS ERP
# Install Python dependencies via Poetry (if pyproject.toml exists) or pip.
if [ -f pyproject.toml ]; then
    poetry install --no-interaction --no-ansi
else
    pip install -r requirements.txt
fi
# Ensure the SQLite DB is created (flask command will do it)
python -m flask db upgrade || true
# No explicit build step needed for a pure Flask app.
# Render will start the service using the start command you configure.
