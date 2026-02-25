#!/usr/bin/env bash
# PASS — Render Build Script
# Runs during each deploy to install deps and prepare the app.

set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Create required directories
mkdir -p instance uploads flask_session
