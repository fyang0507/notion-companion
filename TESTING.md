# Testing Guide

This document outlines the testing strategy and setup for the Notion Companion application.

## Overview

Our testing strategy focuses on **connection services and stable infrastructure** while keeping RAG components flexible for algorithm tuning.

### Testing Architecture

```
Frontend Tests           Backend Tests
├── API Integration     ├── Unit Tests
├── Hook Tests          │   ├── OpenAI Service
├── Component Tests     │   ├── Notion Service  
└── E2E Integration     │   └── Database Layer
                        ├── Integration Tests
                        │   ├── Database Operations
                        │   └── Full Workflows
                        └── API Tests
                            ├── Chat Endpoints
                            └── Search Endpoints
```

## Frontend Testing

### Setup
- **Framework**: Jest + React Testing Library
- **Mocking**: MSW (Mock Service Worker) for API calls
- **Environment**: jsdom for browser simulation

### Test Types

#### 1. API Integration Tests (`__tests__/lib/`)
Test frontend ↔ backend communication:
```bash
npm run test:frontend -- __tests__/lib/
```

#### 2. Hook Tests (`__tests__/hooks/`)
Test custom React hooks:
```bash
npm run test:frontend -- __tests__/hooks/
```

#### 3. Component Tests (`__tests__/components/`)
Test React component behavior:
```bash
npm run test:frontend -- __tests__/components/
```

#### 4. Integration Tests (`__tests__/integration/`)
Test complete user flows:
```bash
npm run test:frontend -- __tests__/integration/
```

### Running Frontend Tests

```bash
# All frontend tests
npm run test:frontend

# Watch mode (development)
npm run test:frontend:watch

# With coverage
npm run test:frontend:coverage

# Specific test file
npm run test:frontend -- api.test.ts
```

## Backend Testing

### Setup
- **Framework**: pytest with async support
- **Mocking**: pytest-mock + custom fixtures
- **API Testing**: httpx for FastAPI testing

### Test Types

#### 1. Unit Tests (`backend/tests/unit/`)
Test individual services and components:
```bash
cd backend && python run_tests.py unit
```

#### 2. Integration Tests (`backend/tests/integration/`)
Test database operations and workflows:
```bash
cd backend && python run_tests.py integration
```

#### 3. API Tests (`backend/tests/api/`)
Test HTTP endpoints and contracts:
```bash
cd backend && python run_tests.py api
```

### Running Backend Tests

```bash
# All backend tests
npm run test:backend

# Specific test types
npm run test:backend:unit
npm run test:backend:integration  
npm run test:backend:api

# With coverage
npm run test:backend:coverage

# Direct pytest commands
cd backend && .venv/bin/python -m pytest tests/unit/ -v
```

## Test Configuration

### Frontend (Jest)
- **Config**: `jest.config.js`
- **Setup**: `jest.setup.js` 
- **Polyfills**: `jest.polyfills.js`

### Backend (Pytest)
- **Config**: `backend/pytest.ini`
- **Fixtures**: `backend/tests/conftest.py`
- **Runner**: `backend/run_tests.py`

## Continuous Integration

Tests run automatically on every push to `main` branch:

```yaml
# .github/workflows/test.yml
- Frontend tests + linting
- Backend tests (unit/integration/api)
- Build verification
- Coverage reporting
```

### CI Commands
```bash
# Run the same tests as CI locally
npm run lint
npm run test:frontend
npm run test:backend
npm run build
```

## Testing Strategy

### ✅ Currently Tested
- **OpenAI Service**: API connections, rate limiting, error handling
- **Notion Service**: Database queries, pagination, authentication
- **Database Layer**: Supabase operations, vector search, CRUD
- **API Endpoints**: Chat, search, session management
- **Frontend Hooks**: Chat sessions, Notion connection, state management
- **Components**: Chat interface, user interactions, error states
- **Integration**: Full chat flow, database filtering, session creation

### 🚧 TODO (Future Implementation)
- **RAG Components**: When algorithms stabilize
  - Contextual chunking
  - Content type detection  
  - Enhanced search engine
- **Performance Tests**: Embedding generation, vector search timing
- **Resilience Tests**: External API failures, graceful degradation
- **E2E Tests**: Full browser automation (optional)

## Mock Strategy

### Frontend Mocks
- **API Calls**: MSW for realistic HTTP mocking
- **External Services**: Jest mocks for hooks and utilities
- **Browser APIs**: Polyfills for Node.js environment

### Backend Mocks
- **External APIs**: pytest-mock for OpenAI, Notion
- **Database**: Mock Supabase client with realistic responses
- **Time/Random**: Deterministic test data

## Best Practices

### Writing Tests
1. **Arrange-Act-Assert**: Clear test structure
2. **Descriptive Names**: Test intent should be obvious
3. **Single Responsibility**: One assertion per test concept
4. **Realistic Data**: Use representative test fixtures
5. **Error Cases**: Test both success and failure paths

### Maintaining Tests
1. **Keep Tests Simple**: Easy to understand and modify
2. **Update with Code**: Tests change with implementation
3. **Fast Execution**: Optimize for quick feedback
4. **Deterministic**: Tests should be reliable and repeatable

## Debugging Tests

### Frontend
```bash
# Run specific test with debug output
npm run test:frontend -- --verbose api.test.ts

# Debug in watch mode
npm run test:frontend:watch
```

### Backend
```bash
# Run with detailed output
cd backend && python -m pytest tests/unit/test_openai_service.py -v -s

# Debug specific test
cd backend && python -m pytest tests/unit/test_openai_service.py::TestOpenAIService::test_embedding_generation -v -s
```

## Coverage Goals

- **Backend Services**: >80% coverage for connection services
- **Frontend Hooks**: >75% coverage for core business logic  
- **API Endpoints**: 100% coverage for all exposed endpoints
- **Integration Flows**: Coverage of critical user paths

## Contributing

When adding new features:

1. **Write tests first** for stable infrastructure components
2. **Test API contracts** to ensure frontend-backend compatibility  
3. **Mock external services** to avoid dependencies in tests
4. **Update test documentation** when adding new test patterns

For RAG algorithm development:
- Skip comprehensive testing during rapid iteration
- Add TODO comments for future test implementation
- Focus on integration points with stable components