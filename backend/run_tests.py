#!/usr/bin/env python3
"""
Test runner script for backend tests.
Provides easy commands to run different test suites.
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def get_python_executable():
    """Get the appropriate Python executable for the current environment."""
    # Check if we're in a uv environment
    if shutil.which("uv") and os.getenv("VIRTUAL_ENV"):
        # Use uv run python if uv is available and we're in a virtual env
        return ["uv", "run", "python"]
    elif Path(".venv/bin/python").exists():
        # Use local venv if it exists
        return [".venv/bin/python"]
    else:
        # Fall back to current Python executable
        return [sys.executable]

def run_command(cmd, description):
    """Run a command and handle the output."""
    print(f"\n🏃 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False

def main():
    """Main test runner."""
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py [unit|integration|api|all|install|ci]")
        print("\nOptions:")
        print("  unit        - Run unit tests only")
        print("  integration - Run integration tests only") 
        print("  api         - Run API tests only")
        print("  all         - Run all tests")
        print("  ci          - Run all tests (optimized for CI)")
        print("  install     - Install test dependencies")
        print("  coverage    - Run tests with coverage report")
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    if command == "install":
        print("📦 Installing test dependencies...")
        python_cmd = get_python_executable()
        success = run_command(
            python_cmd + ["-m", "pip", "install", 
            "pytest", "pytest-mock", "pytest-asyncio", "respx", "coverage"
        ], "Installing test dependencies")
        
        if success:
            print("✅ Test dependencies installed successfully!")
        else:
            print("❌ Failed to install test dependencies")
            sys.exit(1)
            
    elif command == "unit":
        python_cmd = get_python_executable()
        success = run_command(
            python_cmd + ["-m", "pytest", "tests/unit/", "-v", "-m", "unit"
        ], "Running unit tests")
        
    elif command == "integration":
        python_cmd = get_python_executable()
        success = run_command(
            python_cmd + ["-m", "pytest", "tests/integration/", "-v", "-m", "integration"
        ], "Running integration tests")
        
    elif command == "api":
        python_cmd = get_python_executable()
        success = run_command(
            python_cmd + ["-m", "pytest", "tests/api/", "-v", "-m", "api"
        ], "Running API tests")
        
    elif command == "all":
        print("🧪 Running all tests...")
        
        # Run each test suite
        test_suites = [
            (["tests/unit/", "-m", "unit"], "Unit Tests"),
            (["tests/integration/", "-m", "integration"], "Integration Tests"),
            (["tests/api/", "-m", "api"], "API Tests")
        ]
        
        results = []
        python_cmd = get_python_executable()
        for test_args, name in test_suites:
            cmd = python_cmd + ["-m", "pytest"] + test_args + ["-v"]
            success = run_command(cmd, f"Running {name}")
            results.append((name, success))
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        all_passed = True
        for name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{name:20} {status}")
            if not success:
                all_passed = False
        
        if all_passed:
            print("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print("\n💥 Some tests failed!")
            sys.exit(1)
            
    elif command == "ci":
        print("🏗️ Running tests in CI mode (fail-fast, concise output)...")
        
        # Run all tests with CI-optimized flags
        python_cmd = get_python_executable()
        success = run_command(
            python_cmd + ["-m", "pytest", "tests/", 
            "-x",  # Stop on first failure
            "--tb=short",  # Short traceback format
            "--disable-warnings",  # Suppress warnings for cleaner output
            "-q",  # Quiet mode (less verbose than -v)
            "--no-header"  # No pytest header
        ], "Running all tests (CI mode)")
        
        if success:
            print("\n✅ All tests passed in CI mode!")
            sys.exit(0)
        else:
            print("\n❌ Tests failed in CI mode!")
            sys.exit(1)
            
    elif command == "coverage":
        print("📈 Running tests with coverage...")
        
        # Run tests with coverage
        python_cmd = get_python_executable()
        success = run_command(
            python_cmd + ["-m", "coverage", "run", 
            "-m", "pytest", "tests/", "-v"
        ], "Running tests with coverage")
        
        if success:
            # Generate coverage report
            run_command(
                python_cmd + ["-m", "coverage", "report"
            ], "Generating coverage report")
            
            # Generate HTML report
            run_command(
                python_cmd + ["-m", "coverage", "html"
            ], "Generating HTML coverage report")
            
            print("\n📄 Coverage reports generated:")
            print("  - Text report: printed above")
            print("  - HTML report: htmlcov/index.html")
        
    else:
        print(f"❌ Unknown command: {command}")
        print("Valid commands: unit, integration, api, all, install, coverage")
        sys.exit(1)

if __name__ == "__main__":
    main()