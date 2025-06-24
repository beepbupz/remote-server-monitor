#!/usr/bin/env python3
"""Test runner for RSM with coverage reporting."""

import sys
import subprocess
from pathlib import Path


def run_tests():
    """Run all tests with coverage."""
    print("🧪 Running Remote Server Monitor Test Suite")
    print("=" * 50)
    
    # Change to project directory
    project_dir = Path(__file__).parent
    
    try:
        # Run tests with coverage
        print("\n📊 Running tests with coverage...")
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "tests/",
            "--cov=rsm",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--verbose"
        ], cwd=project_dir)
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
            print("📈 Coverage report generated in htmlcov/")
            return True
        else:
            print("\n❌ Some tests failed!")
            return False
            
    except FileNotFoundError:
        print("❌ pytest-cov not installed. Running tests without coverage...")
        
        # Fallback to basic pytest
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "tests/",
            "--verbose"
        ], cwd=project_dir)
        
        return result.returncode == 0


def run_quick_tests():
    """Run unit tests only for quick feedback."""
    print("⚡ Running Quick Unit Tests")
    print("=" * 30)
    
    project_dir = Path(__file__).parent
    
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/unit/",
        "--verbose",
        "--tb=short"
    ], cwd=project_dir)
    
    return result.returncode == 0


def run_linting():
    """Run code quality checks."""
    print("🔍 Running Code Quality Checks")
    print("=" * 35)
    
    project_dir = Path(__file__).parent
    success = True
    
    # Run ruff (linting)
    print("\n📋 Running ruff linting...")
    result = subprocess.run([
        sys.executable, "-m", "ruff", "check", "rsm/"
    ], cwd=project_dir)
    if result.returncode != 0:
        success = False
    
    # Run mypy (type checking)
    print("\n🔍 Running mypy type checking...")
    result = subprocess.run([
        sys.executable, "-m", "mypy", "rsm/"
    ], cwd=project_dir)
    if result.returncode != 0:
        success = False
    
    return success


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "quick":
            success = run_quick_tests()
        elif command == "lint":
            success = run_linting()
        elif command == "all":
            success = run_linting() and run_tests()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python run_tests.py [quick|lint|all]")
            sys.exit(1)
    else:
        success = run_tests()
    
    sys.exit(0 if success else 1)