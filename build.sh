#!/usr/bin/env bash
# Render build script for PASS ERP
if [ -f PASS/pyproject.toml ]; then
    # Install with Poetry inside the PASS directory
    poetry install --no-interaction --no-ansi -C PASS
else
    # Install dependencies from the requirements file inside PASS
    pip install -r PASS/requirements.txt
fi
# No further build steps needed – Flask will create DB tables at runtime.

