# Schema Deployment TODO

> **Current Status**: Dynamic citations working with workarounds  
> **Goal**: Full schema deployment for complete vector search functionality  
> **Priority**: High - Required for optimal performance and chunk-level search

## 🎯 Overview

During the dynamic citations implementation, we discovered that key database functions are missing from the Supabase deployment. The current system uses workarounds that limit functionality. This document outlines the steps needed to deploy the complete schema and unlock full capabilities.

## 🚨 Current Limitations

### Missing Database Functions ❌
- **`match_documents`** - Proper vector similarity search for documents
- **`match_chunks`** - Vector similarity search for document chunks
- **Chunk-level search disabled** - Only document-level results available
- **Inconsistent parameters** - Using `hybrid_search_documents` with different parameter names

### Active Workarounds 🔧
1. **Document Search**: Using `hybrid_search_documents` instead of `match_documents`
   ```python
   # Workaround in database.py:48-59
   response = self.client.rpc('hybrid_search_documents', {
       'workspace_id_param': workspace_id,  # Different parameter name
   })
   ```

2. **Chunk Search**: Completely disabled
   ```python
   # Workaround in database.py:102-109
   print(f"Chunk search not available - schema functions not deployed")
   return []
   ```

## 📋 Deployment Steps

### Step 1: Access Supabase Dashboard
1. Navigate to your Supabase project dashboard
2. Go to **SQL Editor** (left sidebar)
3. Create a new query

### Step 2: Deploy Complete Schema
1. Open `backend/schema.sql` in your local editor
2. Copy the **entire file contents** (all ~600 lines)
3. Paste into Supabase SQL Editor
4. Click **Run** to execute

### Step 3: Verify Function Creation
After deployment, verify these functions exist:
```sql
-- Check if functions were created
SELECT proname, pronargs 
FROM pg_proc 
WHERE proname IN ('match_documents', 'match_chunks');
```

Expected output:
```
proname         | pronargs
----------------|----------
match_documents |        4
match_chunks    |        4
```

### Step 4: Test Functions
```sql
-- Test match_documents function
SELECT * FROM match_documents(
    ARRAY[0.1, 0.2, ...]::vector(1536),  -- Test embedding
    'your-workspace-id'::uuid,
    0.1,  -- threshold
    5     -- limit
);
```

## 🔄 Code Updates Needed After Deployment

### File: `backend/database.py`

**Replace lines 48-59** (vector_search method):
```python
def vector_search(self, query_embedding: List[float], workspace_id: str, 
                      match_threshold: float = 0.7, match_count: int = 10) -> List[Dict[str, Any]]:
    response = self.client.rpc('match_documents', {
        'query_embedding': query_embedding,
        'workspace_id': workspace_id,  # Consistent parameter name
        'match_threshold': match_threshold,
        'match_count': match_count
    }).execute()
    
    return response.data
```

**Replace lines 100-109** (vector_search_chunks method):
```python
def vector_search_chunks(self, query_embedding: List[float], workspace_id: str, 
                             match_threshold: float = 0.7, match_count: int = 10) -> List[Dict[str, Any]]:
    response = self.client.rpc('match_chunks', {
        'query_embedding': query_embedding,
        'workspace_id': workspace_id,
        'match_threshold': match_threshold,
        'match_count': match_count
    }).execute()
    
    return response.data
```

## ✅ Benefits After Deployment

### Immediate Improvements
- **🎯 Chunk-Level Search**: Find specific paragraphs within documents
- **📊 Hybrid Results**: Combine document and chunk results for better precision
- **🔧 Consistent API**: Standardized function signatures across all searches
- **⚡ Better Performance**: Native Supabase functions vs. workaround calls

### Enhanced User Experience
- **📚 More Granular Citations**: Show exact sections that informed AI responses
- **🎨 Better Source Attribution**: Mix of full documents and specific chunks
- **🔍 Improved Relevance**: Chunk-level matching for detailed queries
- **📈 Higher Similarity Scores**: More precise matching algorithms

## 🧪 Testing After Deployment

### 1. Backend Testing
```bash
# Test the updated functions
cd backend
.venv/bin/python -c "
import asyncio
from database import get_db, init_db
from services.openai_service import get_openai_service

async def test_schema():
    await init_db()
    db = get_db()
    openai_service = get_openai_service()
    
    # Test embedding generation
    embedding = await openai_service.generate_embedding('test query')
    
    # Test document search
    docs = db.vector_search_for_single_workspace(
        query_embedding=embedding.embedding,
        match_threshold=0.1,
        match_count=3
    )
    print(f'Document results: {len(docs)}')
    
    # Test chunk search (should work now!)
    chunks = db.vector_search_chunks_for_single_workspace(
        query_embedding=embedding.embedding,
        match_threshold=0.1,
        match_count=3
    )
    print(f'Chunk results: {len(chunks)}')

asyncio.run(test_schema())
"
```

### 2. Frontend Testing
1. Start both frontend and backend
2. Ask a question in chat
3. Verify citations show both documents and chunks
4. Check similarity scores and source types

## 🎁 Future Enhancements Unlocked

Once schema is deployed, these become possible:
- **🔍 Advanced Filtering**: Search within specific document types or date ranges
- **🎯 Contextual Chunking**: Semantic boundary preservation in search results
- **📊 Analytics**: Track which sources are most frequently cited
- **🔄 Incremental Updates**: Efficient document updates without full replacement
- **🎨 Multimedia Support**: Search across text, images, and embedded content

## 📅 Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Schema Deployment | 10 minutes | ⏳ Pending |
| Code Updates | 15 minutes | ⏳ Pending |
| Testing & Verification | 20 minutes | ⏳ Pending |
| **Total** | **45 minutes** | ⏳ Ready to execute |

## 🚨 Rollback Plan

If deployment causes issues:
1. **Backup Current State**: Schema is additive, existing functions remain
2. **Disable New Functions**: Comment out new function calls in code
3. **Revert Code Changes**: Use git to restore workaround implementation
4. **Emergency Contact**: Check Supabase logs for specific error messages

## 📞 Support Resources

- **Schema File**: `backend/schema.sql` (lines 523-598 contain the missing functions)
- **Supabase Docs**: [Database Functions](https://supabase.com/docs/guides/database/functions)
- **Vector Extensions**: [pgvector Documentation](https://github.com/pgvector/pgvector)
- **Current Implementation**: `backend/database.py` (lines 46-121)

---

**Next Action**: Deploy schema to unlock full vector search capabilities and enhance user experience with chunk-level citations.