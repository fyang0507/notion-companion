import { NextRequest, NextResponse } from 'next/server';
import { generateEmbedding } from '@/lib/openai';
import { supabase } from '@/lib/supabase';

export async function POST(request: NextRequest) {
  try {
    const { query, workspaceId, limit = 10 } = await request.json();

    // Generate embedding for the search query
    const { embedding } = await generateEmbedding(query);

    // Perform vector similarity search
    const { data: results, error } = await supabase.rpc('match_documents', {
      query_embedding: embedding,
      workspace_id: workspaceId,
      match_threshold: 0.7,
      match_count: limit,
    });

    if (error) {
      throw error;
    }

    // Format results for client
    const searchResults = results?.map((doc: any) => ({
      id: doc.id,
      title: doc.title,
      content: doc.content.slice(0, 200) + '...',
      similarity: doc.similarity,
      metadata: doc.metadata,
      notion_page_id: doc.notion_page_id,
    }));

    return NextResponse.json({
      results: searchResults,
      query,
      total: results?.length || 0,
    });
  } catch (error) {
    console.error('Search API error:', error);
    return NextResponse.json(
      { error: 'Search failed' },
      { status: 500 }
    );
  }
}