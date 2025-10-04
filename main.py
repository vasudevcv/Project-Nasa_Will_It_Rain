#!/usr/bin/env python3
"""
ParadeGuard - Main entry point for the Streamlit application.
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the Streamlit app
if __name__ == "__main__":
    import streamlit.web.cli as stcli
    import sys
    
    # Run the Streamlit app
    sys.argv = ["streamlit", "run", "app/app.py"]
    sys.exit(stcli.main())
