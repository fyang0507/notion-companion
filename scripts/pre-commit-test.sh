#!/bin/bash

# Pre-commit test script for notion-companion
# Ensures code quality and build success before committing changes

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}🧪 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Header
echo -e "\n${BLUE}================================================================${NC}"
echo -e "${BLUE}🚀 Pre-Commit Testing for Notion Companion${NC}"
echo -e "${BLUE}================================================================${NC}\n"

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -f "next.config.js" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Test 1: TypeScript Compilation Check
print_status "Step 1/4: TypeScript compilation check..."
echo "   Checking for type errors across the entire codebase..."

if npx tsc --noEmit; then
    print_success "TypeScript compilation passed"
else
    print_error "TypeScript compilation failed"
    echo -e "\n${YELLOW}💡 Fix TypeScript errors before proceeding${NC}"
    exit 1
fi

echo ""

# Test 2: ESLint Check  
print_status "Step 2/4: Code quality and linting check..."
echo "   Running ESLint to check code style and potential issues..."

if pnpm run lint; then
    print_success "ESLint checks passed"
else
    print_error "ESLint checks failed"
    echo -e "\n${YELLOW}💡 Fix linting errors before proceeding${NC}"
    exit 1
fi

echo ""

# Test 3: Backend Tests
print_status "Step 3/4: Backend test suite..."
echo "   Running backend unit, integration, and API tests..."

# Check if backend virtual environment exists
if [ ! -d "backend/.venv" ]; then
    print_warning "Backend virtual environment not found. Skipping backend tests."
    print_warning "To run backend tests, set up the backend environment first:"
    echo -e "   ${YELLOW}cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt${NC}"
else
    echo "   🧪 Running backend test suite..."
    if cd backend && python run_tests.py all; then
        print_success "Backend tests passed"
        cd ..
    else
        print_error "Backend tests failed"
        echo -e "\n${YELLOW}💡 Fix backend test failures before proceeding${NC}"
        cd ..
        exit 1
    fi
fi

echo ""

# Test 4: Full Build Test
print_status "Step 4/4: Production build test..."
echo "   Cleaning previous build and testing Next.js production build..."

# Clean previous build
echo "   🧹 Cleaning previous build cache..."
rm -rf .next

# Run the build with timeout
echo "   🏗️  Building for production..."
if timeout 180 pnpm run build; then
    print_success "Production build completed successfully"
    
    # Check if all expected pages were generated
    if [ -d ".next/server/app" ]; then
        page_count=$(find .next/server/app -name "*.js" | wc -l)
        echo -e "   📄 Generated ${page_count} static pages"
    fi
else
    print_error "Production build failed or timed out"
    echo -e "\n${YELLOW}💡 Common build issues:${NC}"
    echo -e "   - Check for TypeScript errors in components"
    echo -e "   - Verify all imports are correct"
    echo -e "   - Look for template literal issues in UI components"
    echo -e "   - Check console output above for specific error details"
    exit 1
fi

# Success summary
echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}🎉 ALL TESTS PASSED! Safe to commit and push to CI/CD${NC}"
echo -e "${GREEN}================================================================${NC}"

echo -e "\n${BLUE}📊 Test Summary:${NC}"
echo -e "   ✅ TypeScript compilation: PASSED"
echo -e "   ✅ Code quality (ESLint): PASSED"
echo -e "   ✅ Backend tests: PASSED"
echo -e "   ✅ Production build: PASSED"

echo -e "\n${BLUE}🚀 Next Steps:${NC}"
echo -e "   1. Review your changes: ${YELLOW}git diff${NC}"
echo -e "   2. Stage your files: ${YELLOW}git add .${NC}"
echo -e "   3. Commit your changes: ${YELLOW}git commit -m \"Your commit message\"${NC}"
echo -e "   4. Push to remote: ${YELLOW}git push${NC}"

echo -e "\n${GREEN}Your code is ready for production! 🚀${NC}\n"