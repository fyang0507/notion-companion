#!/usr/bin/env python3
"""
Test runner script for backend tests.
Provides easy commands to run different test suites.
"""

import subprocess
import sys
import os
from pathlib import Path

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
        print("Usage: python run_tests.py [unit|integration|api|all|install]")
        print("\nOptions:")
        print("  unit        - Run unit tests only")
        print("  integration - Run integration tests only") 
        print("  api         - Run API tests only")
        print("  all         - Run all tests")
        print("  install     - Install test dependencies")
        print("  coverage    - Run tests with coverage report")
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    if command == "install":
        print("📦 Installing test dependencies...")
        success = run_command([
            ".venv/bin/python", "-m", "pip", "install", 
            "pytest", "pytest-mock", "pytest-asyncio", "respx", "coverage"
        ], "Installing test dependencies")
        
        if success:
            print("✅ Test dependencies installed successfully!")
        else:
            print("❌ Failed to install test dependencies")
            sys.exit(1)
            
    elif command == "unit":
        success = run_command([
            ".venv/bin/python", "-m", "pytest", "tests/unit/", "-v", "-m", "unit"
        ], "Running unit tests")
        
    elif command == "integration":
        success = run_command([
            ".venv/bin/python", "-m", "pytest", "tests/integration/", "-v", "-m", "integration"
        ], "Running integration tests")
        
    elif command == "api":
        success = run_command([
            ".venv/bin/python", "-m", "pytest", "tests/api/", "-v", "-m", "api"
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
        for test_args, name in test_suites:
            cmd = [".venv/bin/python", "-m", "pytest"] + test_args + ["-v"]
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
            
    elif command == "coverage":
        print("📈 Running tests with coverage...")
        
        # Run tests with coverage
        success = run_command([
            ".venv/bin/python", "-m", "coverage", "run", 
            "-m", "pytest", "tests/", "-v"
        ], "Running tests with coverage")
        
        if success:
            # Generate coverage report
            run_command([
                ".venv/bin/python", "-m", "coverage", "report"
            ], "Generating coverage report")
            
            # Generate HTML report
            run_command([
                ".venv/bin/python", "-m", "coverage", "html"
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