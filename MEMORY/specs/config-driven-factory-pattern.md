# Config-Driven Factory Pattern Specification

*Last Updated: 2025-07-29*

## Overview
Standardized pattern for creating pluggable, config-driven component architectures that enable strategy switching without code changes.

## Core Components

### 1. Registry Class
```python
class ComponentRegistry:
    def __init__(self):
        self._strategies = {}
        self._register_default_strategies()
    
    def register(self, name: str, strategy_class: Type[BaseStrategy])
    def get_strategy_class(self, name: str) -> Type[BaseStrategy]
    def list_strategies() -> list[str]
```

### 2. Factory Class  
```python
class ComponentFactory:
    def __init__(self):
        self.registry = ComponentRegistry()
    
    def create_strategy(self, strategy_config: Dict, **deps) -> BaseStrategy
```

### 3. Configuration Structure
```toml
[strategies.component_type]
strategy = "strategy_name"
```

## Implementation Pattern

1. **Define Base Interface** - Abstract base class defining strategy contract
2. **Create Registry** - Maps strategy names to implementation classes  
3. **Build Factory** - Handles config parsing and dependency injection
4. **Configure Strategies** - TOML sections for declarative selection
5. **Auto-Registration** - Default strategies register themselves on import

## Benefits
- **Extensibility**: New strategies self-register without core changes
- **Configuration**: Strategy selection via config files, not code
- **Testing**: Easy mocking and strategy swapping for tests
- **Modularity**: Clear separation between strategy logic and instantiation

## Usage Examples

### Chunking Strategy Factory
```python
# Configuration
[strategies.chunking]
strategy = "basic_paragraph"

# Usage (domain-located in ingestion/)
from ingestion.factory import get_chunking_factory
factory = get_chunking_factory()
chunker = factory.create_strategy(strategy_config, ingestion_config)
```

### Retrieval Strategy Factory
```python
# Configuration  
[strategies.retrieval]
strategy = "basic_similarity"

# Usage (domain-located in rag/)
from rag.factory import get_retrieval_factory
factory = get_retrieval_factory()
retriever = factory.create_strategy(strategy_config, db, openai, embeddings_config)
```

## Guidelines
- Use registry pattern for strategy discovery and validation
- Separate configuration parsing from object construction
- Provide global factory instances via getter functions
- Log strategy registration and creation for debugging
- Validate strategy names and provide helpful error messages
- Support dependency injection for complex strategy constructors
- **Domain Co-location**: Place factories in their respective domain modules (ingestion/, rag/) for better cohesion
- **Clear Ownership**: Each factory should own strategies within its domain boundaries