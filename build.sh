#!/usr/bin/env bash
# Render build script for PASS ERP
if [ -f PASS/pyproject.toml ]; then
    cd PASS && poetry install --no-interaction --no-ansi
else
    cd PASS && pip install -r requirements.txt
fi
# Ensure DB tables are created (Flask will do it at runtime)
# No further build steps required.
