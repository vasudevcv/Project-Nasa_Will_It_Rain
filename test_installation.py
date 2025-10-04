#!/usr/bin/env python3
"""
Test script to verify ParadeGuard installation.
"""
import sys
import importlib

def test_imports():
    """Test that all required packages can be imported."""
    required_packages = [
        'streamlit',
        'requests', 
        'httpx',
        'tenacity',
        'pydantic',
        'pandas',
        'numpy',
        'plotly',
        'pydeck',
        'python_dotenv',
        'pytz'
    ]
    
    print("Testing package imports...")
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package}")
        except ImportError as e:
            print(f"❌ {package}: {e}")
            return False
    
    return True

def test_app_imports():
    """Test that our app modules can be imported."""
    print("\nTesting app module imports...")
    
    try:
        from app.core.schemas import GeocodeResult
        print("✅ app.core.schemas")
    except ImportError as e:
        print(f"❌ app.core.schemas: {e}")
        return False
    
    try:
        from app.core.config import validate_secrets
        print("✅ app.core.config")
    except ImportError as e:
        print(f"❌ app.core.config: {e}")
        return False
    
    try:
        from app.services.geocode import geocode_location
        print("✅ app.services.geocode")
    except ImportError as e:
        print(f"❌ app.services.geocode: {e}")
        return False
    
    return True

def main():
    """Main test function."""
    print("ParadeGuard Installation Test")
    print("=" * 40)
    
    # Test package imports
    if not test_imports():
        print("\n❌ Package import test failed!")
        sys.exit(1)
    
    # Test app imports
    if not test_app_imports():
        print("\n❌ App module import test failed!")
        sys.exit(1)
    
    print("\n✅ All tests passed! ParadeGuard is ready to use.")
    print("\nTo run the app:")
    print("  streamlit run app/app.py")

if __name__ == "__main__":
    main()
