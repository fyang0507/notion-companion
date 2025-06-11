import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';
import { generateEmbedding } from '@/lib/openai';

export async function POST(request: NextRequest) {
  try {
    const payload = await request.json();
    
    // Verify webhook signature (in production)
    // const signature = request.headers.get('notion-webhook-signature');
    // if (!verifySignature(payload, signature)) {
    //   return NextResponse.json({ error: 'Invalid signature' }, { status: 401 });
    // }

    const { object, event_type, data } = payload;

    if (object === 'page' && event_type === 'updated') {
      await handlePageUpdate(data);
    } else if (object === 'page' && event_type === 'created') {
      await handlePageCreated(data);
    } else if (object === 'page' && event_type === 'deleted') {
      await handlePageDeleted(data);
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Webhook error:', error);
    return NextResponse.json(
      { error: 'Webhook processing failed' },
      { status: 500 }
    );
  }
}

async function handlePageUpdate(pageData: any) {
  const { id: notionPageId, properties, archived } = pageData;

  if (archived) {
    // Remove from database if archived
    await supabase
      .from('documents')
      .delete()
      .eq('notion_page_id', notionPageId);
    return;
  }

  // Extract content and generate embedding
  const title = extractTitle(properties);
  const content = await extractPageContent(notionPageId);
  const { embedding } = await generateEmbedding(`${title}\n${content}`);

  // Update or insert document
  await supabase
    .from('documents')
    .upsert({
      notion_page_id: notionPageId,
      title,
      content,
      embedding,
      metadata: {
        last_edited_time: pageData.last_edited_time,
        properties: properties,
      },
    });
}

async function handlePageCreated(pageData: any) {
  // Similar to handlePageUpdate but for new pages
  await handlePageUpdate(pageData);
}

async function handlePageDeleted(pageData: any) {
  const { id: notionPageId } = pageData;
  
  await supabase
    .from('documents')
    .delete()
    .eq('notion_page_id', notionPageId);
}

function extractTitle(properties: any): string {
  // Extract title from Notion page properties
  const titleProperty = properties.title || properties.Name || properties.name;
  if (titleProperty?.title) {
    return titleProperty.title.map((t: any) => t.plain_text).join('');
  }
  return 'Untitled';
}

async function extractPageContent(pageId: string): Promise<string> {
  // In production, use Notion API to fetch page content
  // This is a placeholder implementation
  return `Content for page ${pageId}`;
}