import { NextRequest, NextResponse } from 'next/server';
import { generateStreamingResponse } from '@/lib/openai';
import { supabase } from '@/lib/supabase';

export async function POST(request: NextRequest) {
  try {
    const { messages, workspaceId, userId } = await request.json();

    // Get relevant context from workspace documents
    const { data: documents } = await supabase
      .from('documents')
      .select('content, title, metadata')
      .eq('workspace_id', workspaceId)
      .order('created_at', { ascending: false })
      .limit(5);

    const context = documents
      ?.map(doc => `Document: ${doc.title}\nContent: ${doc.content.slice(0, 500)}`)
      .join('\n\n');

    // Generate streaming response
    const responseStream = await generateStreamingResponse(messages, context);

    // Create readable stream
    const stream = new ReadableStream({
      async start(controller) {
        const encoder = new TextEncoder();
        
        try {
          for await (const chunk of responseStream) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ content: chunk })}\n\n`));
          }
          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        } catch (error) {
          controller.error(error);
        } finally {
          controller.close();
        }
      },
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}