#!/usr/bin/env python3
"""
Validate ParadeGuard project structure without requiring dependencies.
"""
import os
import sys

def check_file_exists(filepath, description):
    """Check if a file exists and report status."""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} (missing)")
        return False

def check_directory_exists(dirpath, description):
    """Check if a directory exists and report status."""
    if os.path.isdir(dirpath):
        print(f"✅ {description}: {dirpath}")
        return True
    else:
        print(f"❌ {description}: {dirpath} (missing)")
        return False

def main():
    """Main validation function."""
    print("ParadeGuard Project Structure Validation")
    print("=" * 50)
    
    all_good = True
    
    # Check main files
    print("\n📁 Main Files:")
    files_to_check = [
        ("requirements.txt", "Dependencies file"),
        ("README.md", "Documentation"),
        ("SETUP.md", "Setup instructions"),
        ("env.example", "Environment variables example"),
        (".gitignore", "Git ignore file"),
        ("Makefile", "Build commands"),
        ("test_installation.py", "Installation test script")
    ]
    
    for filepath, description in files_to_check:
        if not check_file_exists(filepath, description):
            all_good = False
    
    # Check directories
    print("\n📂 Directories:")
    dirs_to_check = [
        ("app", "Main application directory"),
        ("app/core", "Core modules directory"),
        ("app/services", "API services directory"),
        ("app/assets", "Assets directory")
    ]
    
    for dirpath, description in dirs_to_check:
        if not check_directory_exists(dirpath, description):
            all_good = False
    
    # Check core modules
    print("\n🔧 Core Modules:")
    core_files = [
        ("app/__init__.py", "App package init"),
        ("app/core/__init__.py", "Core package init"),
        ("app/core/schemas.py", "Pydantic schemas"),
        ("app/core/config.py", "Configuration management"),
        ("app/core/risk.py", "Risk scoring algorithm"),
        ("app/core/timeutil.py", "Time utilities"),
        ("app/core/exporter.py", "Data export functionality"),
        ("app/core/maputil.py", "Map utilities")
    ]
    
    for filepath, description in core_files:
        if not check_file_exists(filepath, description):
            all_good = False
    
    # Check services
    print("\n🌐 API Services:")
    service_files = [
        ("app/services/__init__.py", "Services package init"),
        ("app/services/geocode.py", "Google Geocoding service"),
        ("app/services/google_weather.py", "Google Weather service"),
        ("app/services/meteostat.py", "Meteostat service"),
        ("app/services/open_meteo.py", "Open-Meteo service")
    ]
    
    for filepath, description in service_files:
        if not check_file_exists(filepath, description):
            all_good = False
    
    # Check main app
    print("\n🚀 Main Application:")
    if not check_file_exists("app/app.py", "Streamlit application"):
        all_good = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_good:
        print("✅ All files and directories are present!")
        print("\nNext steps:")
        print("1. Install dependencies: pip3 install -r requirements.txt")
        print("2. Set up API keys: cp env.example .env")
        print("3. Test installation: python3 test_installation.py")
        print("4. Run the app: streamlit run app/app.py")
    else:
        print("❌ Some files or directories are missing!")
        print("Please check the missing items above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
