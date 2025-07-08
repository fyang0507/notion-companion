# Evaluation Test Suite

This directory contains the test suite for the evaluation system components, including the multilingual chunker, data collection, and other evaluation tools.

## Test Structure

```
evaluation/tests/
├── __init__.py              # Test package init
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests
│   ├── __init__.py
│   └── test_multilingual_chunker.py
├── integration/             # Integration tests
│   ├── __init__.py
│   └── test_data_collection.py
└── README.md               # This file
```

## Running Tests

### Quick Start

Use the test runner script from the evaluation directory:

```bash
cd evaluation
python run_tests.py all
```

### Test Categories

#### Fast Tests (default)
- Unit tests with mocked dependencies
- Basic integration tests with short timeouts
- Quick validation of core functionality

#### Slow Tests
- Large database collection tests
- Rate limiting and concurrent access tests
- Performance and stress testing scenarios
- Extended timeout handling (45-60 seconds)

### Test Runner Options

```bash
python run_tests.py [command]
```

Available commands:
- `unit` - Run unit tests only
- `integration` - Run integration tests only (requires NOTION_ACCESS_TOKEN)
- `all` - Run all tests
- `ci` - Run all tests (optimized for CI)
- `coverage` - Run tests with coverage report
- `install` - Install test dependencies
- `chunker` - Run multilingual chunker tests only
- `collection` - Run data collection tests only
- `slow` - Run slow/large tests only (60s timeouts)
- `fast` - Run all tests except slow ones

### Using pytest directly

You can also run tests directly with pytest from the root directory:

```bash
# From project root
uv run python -m pytest evaluation/tests/ -v

# Run only unit tests
uv run python -m pytest evaluation/tests/unit/ -v -m unit

# Run only integration tests
uv run python -m pytest evaluation/tests/integration/ -v -m integration
```

## Environment Setup

### For Unit Tests
Unit tests use mocked services and don't require external setup.

### For Integration Tests
Integration tests automatically load environment variables from the root `.env` file:

1. **Notion API Token**: Set `NOTION_ACCESS_TOKEN` in root `.env` file
2. **Test Database**: Optionally set `TEST_DATABASE_ID` for a specific test database

```bash
# In the root folder, create/update .env file:
NOTION_ACCESS_TOKEN=your_notion_token_here
TEST_DATABASE_ID=your_test_database_id  # Optional
```

The test suite automatically loads these variables using `python-dotenv`.

## Test Fixtures

The test suite includes comprehensive fixtures defined in `conftest.py`:

### Mock Services
- `mock_embedding_service` - Mock embedding generation
- `mock_tokenizer` - Mock text tokenization
- `mock_notion_client` - Mock Notion API client

### Sample Data
- `sample_test_texts` - Multilingual text samples for testing
- `sample_documents` - Sample document data
- `chunking_config` - Default chunking configuration
- `temp_output_dir` - Temporary directory for test outputs

### Configuration
- `sample_evaluation_config` - Sample evaluation configuration
- Environment variable setup for testing

## Test Markers

Tests are marked with pytest markers for easy filtering:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests  
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.asyncio` - Async tests

## Writing New Tests

### Unit Test Example

```python
import pytest
from services.your_service import YourService

@pytest.mark.unit
class TestYourService:
    @pytest.fixture
    def service(self, mock_dependency):
        return YourService(dependency=mock_dependency)
    
    @pytest.mark.asyncio
    async def test_your_method(self, service):
        result = await service.your_method()
        assert result is not None
```

### Integration Test Example

```python
import pytest
import os

@pytest.mark.integration
class TestYourIntegration:
    def test_environment_setup(self):
        if not os.getenv("REQUIRED_TOKEN"):
            pytest.skip("REQUIRED_TOKEN not set")
        
        # Your integration test here
```

## Coverage Reports

Generate coverage reports:

```bash
python run_tests.py coverage
```

This generates:
- Console coverage report
- HTML coverage report in `htmlcov_evaluation/`

## Continuous Integration

For CI environments, use the optimized CI mode:

```bash
python run_tests.py ci
```

This mode:
- Stops on first failure (`-x`)
- Uses short traceback format
- Suppresses warnings
- Uses quiet output

## Dependencies

Test dependencies are managed in the root `pyproject.toml`:

- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-mock` - Mocking utilities
- `coverage` - Code coverage

Install with:

```bash
uv sync  # From evaluation directory
# or
python run_tests.py install
```