"""Entry point for Streamlit - placed at project root for reliable imports."""

import sys
import os

# Ensure project root is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import and run the actual app
from app.main import run

run()
