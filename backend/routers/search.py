from fastapi import APIRouter, HTTPException
from database import get_db
from services.openai_service import get_openai_service
from models import SearchRequest, SearchResponse, SearchResult

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def search_endpoint(request: SearchRequest):
    try:
        db = get_db()
        openai_service = get_openai_service()
        
        # Generate embedding for the search query
        embedding_response = await openai_service.generate_embedding(request.query)
        
        # Perform vector similarity search
        results = await db.vector_search(
            query_embedding=embedding_response.embedding,
            workspace_id=request.workspaceId,
            match_threshold=0.7,
            match_count=request.limit
        )
        
        # Format results for client
        search_results = [
            SearchResult(
                id=doc['id'],
                title=doc['title'],
                content=doc['content'][:200] + '...' if len(doc['content']) > 200 else doc['content'],
                similarity=doc['similarity'],
                metadata=doc['metadata'],
                notion_page_id=doc['notion_page_id']
            )
            for doc in results
        ]
        
        return SearchResponse(
            results=search_results,
            query=request.query,
            total=len(search_results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")