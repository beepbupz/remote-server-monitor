#!/usr/bin/env python3
"""Basic smoke test to verify the package structure is correct."""

import sys
import importlib

def test_imports():
    """Test that all modules can be imported."""
    modules = [
        'rsm',
        'rsm.__main__',
        'rsm.core.config',
        'rsm.core.ssh_manager',
        'rsm.collectors.base',
        'rsm.collectors.system',
        'rsm.utils.platform',
        'rsm.ui.app',
    ]
    
    print("Testing module imports...")
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"✓ {module}")
        except ImportError as e:
            print(f"✗ {module}: {e}")
            return False
    
    return True

def test_version():
    """Test that version is defined."""
    try:
        from rsm import __version__
        print(f"\n✓ Version: {__version__}")
        return True
    except ImportError:
        print("\n✗ Version not found")
        return False

def main():
    """Run basic tests."""
    print("Running basic smoke tests for Remote Server Monitor\n")
    
    success = True
    success &= test_imports()
    success &= test_version()
    
    if success:
        print("\n✅ All basic tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())