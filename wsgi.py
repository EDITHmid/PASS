"""
PASS — WSGI Entry Point
=========================
Production entry point for Gunicorn on Render.
"""

import os
import sys

# Add the PASS directory to the Python path
pass_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PASS")
sys.path.insert(0, pass_dir)
os.chdir(pass_dir)

from app import create_app, db
from models import User

app = create_app("production")

# Ensure tables exist on first deploy
with app.app_context():
    db.create_all()

    # Seed demo data if database is empty (first deploy only)
    if not User.query.first():
        from run import seed_demo_data
        seed_demo_data()
