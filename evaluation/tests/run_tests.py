#!/usr/bin/env python3
"""
Test runner script for evaluation tests.
Provides easy commands to run different test suites in the evaluation system.
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
        print("Usage: python run_tests.py [unit|integration|all|ci|coverage|install]")
        print("\nOptions:")
        print("  unit        - Run unit tests only")
        print("  integration - Run integration tests only (requires NOTION_ACCESS_TOKEN)")
        print("  all         - Run all tests")
        print("  ci          - Run all tests (optimized for CI)")
        print("  coverage    - Run tests with coverage report")
        print("  install     - Install test dependencies")
        print("  chunker     - Run multilingual chunker tests only")
        print("  collection  - Run data collection tests only")
        print("  slow        - Run slow/large tests only")
        print("  fast        - Run all tests except slow ones")
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Change to evaluation directory
    evaluation_dir = Path(__file__).parent
    os.chdir(evaluation_dir)
    
    # Use uv to run tests (following project's uv pattern)
    uv_python = "uv run python"
    pytest_cmd = f"{uv_python} -m pytest"
    
    if command == "install":
        print("📦 Installing evaluation test dependencies...")
        
        # The dependencies are already in the root pyproject.toml
        success = run_command([
            "uv", "sync"
        ], "Syncing evaluation dependencies with uv")
        
        if success:
            print("✅ Test dependencies installed successfully!")
        else:
            print("❌ Failed to install test dependencies")
            sys.exit(1)
            
    elif command == "unit":
        success = run_command([
            "uv", "run", "python", "-m", "pytest", "tests/unit/", "-v", "-m", "unit"
        ], "Running evaluation unit tests")
        
    elif command == "integration":
        print("🔗 Running integration tests (requires NOTION_ACCESS_TOKEN)...")
        
        # Check if NOTION_ACCESS_TOKEN is set
        if not os.getenv("NOTION_ACCESS_TOKEN"):
            print("⚠️  NOTION_ACCESS_TOKEN not set - integration tests will be skipped")
        
        success = run_command([
            "uv", "run", "python", "-m", "pytest", "tests/integration/", "-v", "-m", "integration"
        ], "Running evaluation integration tests")
        
    elif command == "chunker":
        success = run_command([
            "uv", "run", "python", "-m", "pytest", "tests/unit/test_multilingual_chunker.py", "-v"
        ], "Running multilingual chunker tests")
        
    elif command == "collection":
        success = run_command([
            "uv", "run", "python", "-m", "pytest", "tests/integration/test_data_collection.py", "-v"
        ], "Running data collection tests")
        
    elif command == "slow":
        success = run_command([
            "uv", "run", "python", "-m", "pytest", "tests/", "-v", "-m", "slow"
        ], "Running slow/large tests only")
        
    elif command == "fast":
        success = run_command([
            "uv", "run", "python", "-m", "pytest", "tests/", "-v", "-m", "not slow"
        ], "Running all tests except slow ones")
        
    elif command == "all":
        print("🧪 Running all evaluation tests...")
        
        # Run each test suite
        test_suites = [
            (["tests/unit/", "-m", "unit"], "Unit Tests"),
            (["tests/integration/", "-m", "integration"], "Integration Tests")
        ]
        
        results = []
        for test_args, name in test_suites:
            cmd = ["uv", "run", "python", "-m", "pytest"] + test_args + ["-v"]
            success = run_command(cmd, f"Running {name}")
            results.append((name, success))
        
        # Summary
        print("\n" + "="*60)
        print("📊 EVALUATION TEST SUMMARY")
        print("="*60)
        
        all_passed = True
        for name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{name:20} {status}")
            if not success:
                all_passed = False
        
        if all_passed:
            print("\n🎉 All evaluation tests passed!")
            sys.exit(0)
        else:
            print("\n💥 Some evaluation tests failed!")
            sys.exit(1)
            
    elif command == "ci":
        print("🏗️ Running evaluation tests in CI mode (fail-fast, concise output)...")
        
        # Run all tests with CI-optimized flags
        success = run_command([
            "uv", "run", "python", "-m", "pytest", "tests/", 
            "-x",  # Stop on first failure
            "--tb=short",  # Short traceback format
            "--disable-warnings",  # Suppress warnings for cleaner output
            "-q",  # Quiet mode (less verbose than -v)
            "--no-header"  # No pytest header
        ], "Running all evaluation tests (CI mode)")
        
        if success:
            print("\n✅ All evaluation tests passed in CI mode!")
            sys.exit(0)
        else:
            print("\n❌ Evaluation tests failed in CI mode!")
            sys.exit(1)
            
    elif command == "coverage":
        print("📈 Running evaluation tests with coverage...")
        
        # Run tests with coverage
        success = run_command([
            "uv", "run", "python", "-m", "coverage", "run", 
            "-m", "pytest", "tests/", "-v",
            "--source=services,utils,models"
        ], "Running tests with coverage")
        
        if success:
            # Generate coverage report
            run_command([
                "uv", "run", "python", "-m", "coverage", "report"
            ], "Generating coverage report")
            
            # Generate HTML report
            run_command([
                "uv", "run", "python", "-m", "coverage", "html",
                "--directory=htmlcov_evaluation"
            ], "Generating HTML coverage report")
            
            print("\n📄 Coverage reports generated:")
            print("  - Text report: printed above")
            print("  - HTML report: htmlcov_evaluation/index.html")
        
    else:
        print(f"❌ Unknown command: {command}")
        print("Valid commands: unit, integration, all, ci, coverage, install, chunker, collection, slow, fast")
        sys.exit(1)


if __name__ == "__main__":
    main() 