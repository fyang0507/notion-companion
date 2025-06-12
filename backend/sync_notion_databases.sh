#!/bin/bash

# Notion Database Sync Wrapper Script
# This script provides a convenient way to run the database sync

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config"
PYTHON_SCRIPT="$SCRIPT_DIR/scripts/sync_databases.py"

# Default values
CONFIG_FILE="$CONFIG_DIR/databases.toml"
DRY_RUN=false

# Help function
show_help() {
    cat << EOF
Notion Database Sync Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -c, --config FILE       Config file path (default: config/databases.toml)
    -d, --dry-run           Dry run - validate config but don't sync
    -h, --help              Show this help

EXAMPLES:
    # Basic sync (reads NOTION_ACCESS_TOKEN from environment or .env file)
    $0

    # Dry run to test configuration
    $0 --dry-run

    # Use custom config file
    $0 --config /path/to/custom/config.toml

ENVIRONMENT SETUP:
    # Set token in environment (recommended)
    export NOTION_ACCESS_TOKEN="your_token_here"
    
    # Or add to .env file in backend directory
    echo "NOTION_ACCESS_TOKEN=your_token_here" >> .env

    # Make sure to never commit .env files to version control!

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if config file exists
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: Config file not found: $CONFIG_FILE"
    echo "Create one based on the example in config/databases.example.toml"
    exit 1
fi

# Check if Python script exists
if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    echo "Error: Python script not found: $PYTHON_SCRIPT"
    exit 1
fi

# Check if NOTION_ACCESS_TOKEN is set (either in environment or .env file)
if [[ -z "$NOTION_ACCESS_TOKEN" ]] && [[ ! -f "$SCRIPT_DIR/.env" ]]; then
    echo "Error: NOTION_ACCESS_TOKEN not found in environment or .env file"
    echo "Set it with: export NOTION_ACCESS_TOKEN='your_token'"
    echo "Or add it to a .env file in the backend directory"
    exit 1
fi

# Activate virtual environment if it exists
VENV_PATH="$SCRIPT_DIR/.venv"
if [[ -d "$VENV_PATH" ]]; then
    echo "Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
fi

# Build Python command
PYTHON_CMD="python $PYTHON_SCRIPT --config $CONFIG_FILE"

# Add dry run if specified
if [[ "$DRY_RUN" == true ]]; then
    PYTHON_CMD="$PYTHON_CMD --dry-run"
fi

echo "Starting Notion database sync..."
echo "Config: $CONFIG_FILE"
echo "Command: $PYTHON_CMD"
echo ""

# Run the Python script
eval $PYTHON_CMD

echo ""
echo "Sync completed!"