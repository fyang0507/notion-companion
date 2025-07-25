# Coding Standards & SOPs

*Last Updated: 2025-07-23*

## Best Practices
- Read doc before writing code: when working with external libraries that are in active development, use Context7 MCP or perform online search to read the latest documentation or analysis the bugs before writing code
- Parameterization: Ensure that no silent defaults are set up. Set up `.toml` files for configuration if there are multiple parameters. Do not over-use default keyword arguments with default values. Do not use `.get('key', 'default')` (unless the key is optional and a default none/null value is expected), instead use bracket notation and fail hard when the key is not found. 
- When raising exceptions, raise the entire traceback
- Use `TODO, FIXME, XXX` for comments

## Preferred Tools
- Use pnpm for frontend, uv for backend
- Use `load_dotenv()` for environment loading
- Use `loguru` for backend logging
- Use built-in `tomllib` for TOML parsing (Python 3.11+)
- Use `seaborn` for statistical visualizations (if applicable), use `pandas` for data parsing (e.g. csv reading)

## Testing Guidelines

**🚫 CRITICAL: NEVER start backend services silently**
**✅ CORRECT WORKFLOW:**
1. Ask user to start backend with `pnpm run backend`
2. Run curl tests against localhost:8000
3. Ask user to stop backend when testing is complete