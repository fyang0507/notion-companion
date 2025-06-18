# Testing Best Practices

> **Problem**: Starting uvicorn with `&` causes 2-minute timeouts  
> **Solution**: Use targeted testing approaches that avoid blocking processes

## 🚨 Avoid These Patterns

### ❌ Background Server (Always Times Out)
```bash
# DON'T DO THIS - Always times out after 2 minutes
.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
```

**Why it fails**: Uvicorn outputs logs continuously, so the command never "completes" even with `&`

## ✅ Better Testing Approaches

### 1. Direct Component Testing (Fastest)
Test individual components without starting the web server:

```bash
# Test database and OpenAI integration directly
.venv/bin/python -c "
import asyncio
from database import get_db, init_db
from services.openai_service import get_openai_service

async def test_components():
    await init_db()
    db = get_db()
    openai_service = get_openai_service()
    
    # Test embedding
    embedding = await openai_service.generate_embedding('test')
    print(f'✓ Embedding: {len(embedding.embedding)} dims')
    
    # Test vector search
    results = db.vector_search_for_single_workspace(
        query_embedding=embedding.embedding,
        match_threshold=0.1,
        match_count=3
    )
    print(f'✓ Vector search: {len(results)} results')

asyncio.run(test_components())
"
```

### 2. Quick Server Test (10 seconds max)
When you need to test the full API:

```bash
# Start server briefly, test, then kill
(.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 &) && \
sleep 3 && \
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "test"}]}' \
  --max-time 10 && \
lsof -ti:8000 | xargs kill -9
```

### 3. Isolated Function Testing
Create small test scripts for specific functionality:

```python
# test_chat_flow.py
async def test_chat_flow():
    # Test the exact chat logic without HTTP layer
    from routers.chat import chat_endpoint
    from models import ChatRequest, ChatMessage
    
    request = ChatRequest(messages=[
        ChatMessage(role="user", content="test query")
    ])
    
    # Test the core logic
    response = await chat_endpoint(request)
    print("✓ Chat endpoint logic works")

asyncio.run(test_chat_flow())
```

### 4. Database-Only Testing
When testing database changes:

```bash
# Test database functions directly
.venv/bin/python -c "
from database import get_db
import asyncio

async def test_db():
    await get_db().init()
    db = get_db()
    
    # Test specific database operations
    workspace_id = db.get_single_workspace_id()
    print(f'✓ Workspace: {workspace_id}')
    
    docs = db.get_documents_for_single_workspace(limit=3)
    print(f'✓ Documents: {len(docs)} found')

asyncio.run(test_db())
"
```

## 🎯 When to Use Each Approach

| Testing Need | Best Approach | Time | Command |
|--------------|---------------|------|---------|
| Database changes | Component testing | ~5s | Direct Python script |
| OpenAI integration | Component testing | ~10s | Direct async call |
| API endpoint logic | Function testing | ~15s | Import and test function |
| Full HTTP flow | Quick server test | ~30s | Start→Test→Kill pattern |
| Frontend integration | Manual testing | Variable | User starts servers |

## 🔧 Debugging Patterns

### For Database Issues
```bash
# Quick database connectivity test
.venv/bin/python -c "
import asyncio
from database import init_db, get_db

async def check_db():
    try:
        await init_db()
        print('✓ Database connected')
        
        db = get_db()
        response = db.client.table('documents').select('id').limit(1).execute()
        print(f'✓ Query works: {len(response.data)} records')
    except Exception as e:
        print(f'✗ Database error: {e}')

asyncio.run(check_db())
"
```

### For OpenAI Issues
```bash
# Test OpenAI service only
.venv/bin/python -c "
import asyncio
from services.openai_service import get_openai_service

async def check_openai():
    try:
        service = get_openai_service()
        embedding = await service.generate_embedding('test')
        print(f'✓ OpenAI works: {len(embedding.embedding)} dimensions')
    except Exception as e:
        print(f'✗ OpenAI error: {e}')

asyncio.run(check_openai())
"
```

### For Vector Search Issues
```bash
# Test vector search specifically
.venv/bin/python -c "
import asyncio
from database import init_db, get_db
from services.openai_service import get_openai_service

async def check_vector_search():
    await init_db()
    db = get_db()
    openai_service = get_openai_service()
    
    # Generate test embedding
    embedding_response = await openai_service.generate_embedding('test query')
    
    # Test vector search
    results = db.vector_search_for_single_workspace(
        query_embedding=embedding_response.embedding,
        match_threshold=0.1,
        match_count=3
    )
    
    print(f'✓ Vector search: {len(results)} results')
    if results:
        print(f'  First result: {results[0].get(\"title\", \"No title\")}')

asyncio.run(check_vector_search())
"
```

## 📝 Testing Script Templates

### Quick Health Check
```bash
# health_check.sh
echo "Testing backend health..."

# 1. Database
.venv/bin/python -c "
import asyncio
from database import init_db
async def test(): 
    await init_db(); print('✓ DB OK')
asyncio.run(test())
" || echo "✗ DB Failed"

# 2. OpenAI
.venv/bin/python -c "
import asyncio
from services.openai_service import get_openai_service
async def test(): 
    await get_openai_service().generate_embedding('test'); print('✓ OpenAI OK')
asyncio.run(test())
" || echo "✗ OpenAI Failed"

echo "Health check complete"
```

### Chat Flow Test
```bash
# test_chat.sh
echo "Testing chat flow..."

.venv/bin/python -c "
import asyncio
from database import init_db, get_db
from services.openai_service import get_openai_service

async def test_chat():
    await init_db()
    db = get_db()
    openai_service = get_openai_service()
    
    # Test the full chat pipeline
    message = 'test query'
    embedding = await openai_service.generate_embedding(message)
    
    sources = db.vector_search_for_single_workspace(
        query_embedding=embedding.embedding,
        match_threshold=0.1,
        match_count=3
    )
    
    print(f'✓ Chat pipeline: {len(sources)} sources found')

asyncio.run(test_chat())
"
```

## 🏃‍♂️ Speed Optimization Tips

1. **Reuse connections**: Don't initialize database/OpenAI multiple times
2. **Test incrementally**: Start with smallest component, work up
3. **Use specific tests**: Don't test everything when you changed one thing
4. **Cache imports**: Import modules once in longer scripts
5. **Parallel testing**: Test database and OpenAI concurrently when possible

## 🎯 Decision Tree

```
Need to test something?
├── Database only? → Use component testing
├── OpenAI only? → Use component testing  
├── Specific function? → Use function testing
├── API endpoint? → Use quick server test
└── Everything? → Use health check script
```

---

**Key Takeaway**: Avoid starting servers in background. Test components directly for faster, more reliable results.