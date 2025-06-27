# Development Workflow Guide

This guide outlines the recommended development workflow for the Notion Companion project, including testing procedures and best practices.

## Pre-Commit Testing

### Quick Start

Run the automated pre-commit test script:

```bash
./scripts/pre-commit-test.sh
```

This script performs all necessary checks to ensure your code is ready for CI/CD.

### Manual Testing Steps

If you prefer to run tests manually:

#### 1. TypeScript Compilation Check (30 seconds)
```bash
npx tsc --noEmit
```
- **Purpose**: Catches type errors across the entire codebase
- **Why it matters**: Ensures type safety and prevents runtime errors
- **What it checks**: TypeScript compilation without generating files

#### 2. Code Quality Check (1 minute)
```bash
pnpm run lint
```
- **Purpose**: Ensures code style consistency and catches potential issues
- **Why it matters**: Maintains code quality standards and readability
- **What it checks**: ESLint rules, formatting, and best practices

#### 3. Production Build Test (2-3 minutes) **[MOST IMPORTANT]**
```bash
rm -rf .next && pnpm run build
```
- **Purpose**: Verifies the production build works correctly
- **Why it matters**: Catches compilation issues that TypeScript alone might miss
- **What it checks**: 
  - Next.js compilation
  - Static page generation
  - Dependency resolution
  - Template literal processing
  - Build optimization

## Why This Workflow is Critical

### Lessons Learned from Build Issues

Our experience troubleshooting compilation errors revealed that:

1. **TypeScript compilation ≠ successful build**
   - TypeScript can pass while build fails due to dependency issues
   - JavaScript compilation can have different requirements than TypeScript

2. **Build issues can be environment-specific**
   - Template literal processing in UI components
   - Dependency compilation problems
   - Webpack configuration edge cases

3. **GitHub Actions mirrors local build**
   - If local build fails, CI/CD will fail
   - Early detection saves time and reduces failed commits

### Test Confidence Levels

| Testing Level | Time Investment | Confidence | Recommended For |
|---------------|----------------|------------|-----------------|
| TypeScript only | 30 seconds | 70% | Quick syntax checks |
| TypeScript + Lint | 1.5 minutes | 85% | Code review prep |
| **Full Build** | **3 minutes** | **95%** | **Before committing** |

## Common Issues and Solutions

### TypeScript Errors
```bash
# Common fixes:
- Check import paths
- Verify interface definitions
- Ensure all required properties are defined
```

### Linting Errors
```bash
# Common fixes:
- Fix formatting with: pnpm run lint --fix
- Add proper dependencies to useEffect arrays
- Remove unused imports
```

### Build Failures
```bash
# Common causes:
- Template literal issues in UI components
- Missing dependencies
- Circular imports
- Invalid Next.js configuration

# Debugging:
- Check the error output for specific file references
- Look for "SyntaxError" messages
- Verify all imports are correct
```

## Best Practices

### Before Starting Development
1. Pull latest changes: `git pull origin main`
2. Install dependencies: `pnpm install`
3. Run initial tests: `./scripts/pre-commit-test.sh`

### During Development
1. Run TypeScript check frequently: `npx tsc --noEmit`
2. Use editor with TypeScript integration for real-time feedback
3. Test components individually if making major changes

### Before Committing
1. **Always run the full test suite**: `./scripts/pre-commit-test.sh`
2. Review your changes: `git diff`
3. Write descriptive commit messages
4. Ensure all tests pass before pushing

### Emergency Fixes
If you need to push urgent fixes:
1. Run at minimum: `npx tsc --noEmit && pnpm run build`
2. Document any skipped tests in commit message
3. Run full test suite on next commit

## Troubleshooting

### Script Permissions
```bash
# If you get permission denied:
chmod +x scripts/pre-commit-test.sh
```

### Build Timeouts
```bash
# If build takes too long:
# The script has a 3-minute timeout
# For slower machines, edit the timeout in the script
```

### Memory Issues
```bash
# If you encounter memory issues:
export NODE_OPTIONS="--max-old-space-size=4096"
```

## Integration with Git Hooks

You can automate this workflow using Git hooks:

### Pre-commit Hook (Optional)
```bash
# Create .git/hooks/pre-commit
#!/bin/bash
./scripts/pre-commit-test.sh
```

### Manual Approach (Recommended)
We recommend running tests manually to maintain control over the development workflow and avoid blocking commits when needed.

## CI/CD Pipeline

Our GitHub Actions workflow mirrors this local testing:
1. TypeScript compilation check
2. ESLint validation
3. Production build test
4. Static page generation verification

By following this local workflow, you ensure compatibility with the CI/CD pipeline.

---

## Quick Reference

**Before every commit:**
```bash
./scripts/pre-commit-test.sh
```

**Quick syntax check:**
```bash
npx tsc --noEmit
```

**Quick style check:**
```bash
pnpm run lint
```

**Full build verification:**
```bash
rm -rf .next && pnpm run build
```

This workflow ensures high code quality and prevents build failures in production environments.