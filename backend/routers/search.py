from fastapi import APIRouter, HTTPException
from database_v3 import get_db
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
        
        # Search both documents and chunks (V3 simplified)
        doc_results = db.vector_search_documents(
            query_embedding=embedding_response.embedding,
            database_filter=request.database_filters,
            match_threshold=0.7,
            match_count=request.limit
        )
        
        chunk_results = db.vector_search_chunks(
            query_embedding=embedding_response.embedding,
            database_filter=request.database_filters,
            match_threshold=0.7,
            match_count=request.limit
        )
        
        # Combine and sort results by similarity
        all_results = []
        
        # Add document results
        for doc in doc_results:
            all_results.append({
                'id': doc['id'],
                'title': doc['title'],
                'content': doc['content'][:200] + '...' if len(doc['content']) > 200 else doc['content'],
                'similarity': doc['similarity'],
                'metadata': doc.get('metadata', {}),
                'notion_page_id': doc['notion_page_id'],
                'page_url': doc.get('page_url', ''),
                'type': 'document'
            })
        
        # Add chunk results
        for chunk in chunk_results:
            all_results.append({
                'id': chunk['chunk_id'],
                'title': chunk['title'],
                'content': chunk['chunk_content'],
                'similarity': chunk['similarity'],
                'metadata': {'chunk_index': chunk['chunk_index'], 'type': 'chunk'},
                'notion_page_id': chunk['notion_page_id'],
                'page_url': chunk.get('page_url', ''),
                'type': 'chunk'
            })
        
        # Sort by similarity and limit results
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        final_results = all_results[:request.limit]
        
        # Format results for client
        search_results = [
            SearchResult(
                id=result['id'],
                title=result['title'],
                content=result['content'],
                similarity=result['similarity'],
                metadata=result['metadata'],
                notion_page_id=result['notion_page_id']
            )
            for result in final_results
        ]
        
        return SearchResponse(
            results=search_results,
            query=request.query,
            total=len(search_results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")