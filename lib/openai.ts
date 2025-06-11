import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY!,
});

export interface EmbeddingResponse {
  embedding: number[];
  tokens: number;
}

export interface ChatResponse {
  content: string;
  tokens: number;
}

export async function generateEmbedding(text: string): Promise<EmbeddingResponse> {
  const response = await openai.embeddings.create({
    model: 'text-embedding-3-small',
    input: text,
  });

  return {
    embedding: response.data[0].embedding,
    tokens: response.usage.total_tokens,
  };
}

export async function generateChatResponse(
  messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>,
  context?: string
): Promise<ChatResponse> {
  const systemMessage = {
    role: 'system' as const,
    content: `You are a helpful AI assistant that answers questions based on the user's Notion workspace content. 
    ${context ? `Here is relevant context from their workspace: ${context}` : ''}
    
    Guidelines:
    - Be concise and helpful
    - Reference specific documents when possible
    - If you're not sure about something, say so
    - Format responses in markdown when appropriate`,
  };

  const response = await openai.chat.completions.create({
    model: 'gpt-4',
    messages: [systemMessage, ...messages],
    temperature: 0.7,
    max_tokens: 1000,
  });

  return {
    content: response.choices[0].message.content || '',
    tokens: response.usage?.total_tokens || 0,
  };
}

export async function generateStreamingResponse(
  messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>,
  context?: string
): Promise<AsyncIterable<string>> {
  const systemMessage = {
    role: 'system' as const,
    content: `You are a helpful AI assistant that answers questions based on the user's Notion workspace content. 
    ${context ? `Here is relevant context from their workspace: ${context}` : ''}`,
  };

  const stream = await openai.chat.completions.create({
    model: 'gpt-4',
    messages: [systemMessage, ...messages],
    temperature: 0.7,
    max_tokens: 1000,
    stream: true,
  });

  return (async function* () {
    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content;
      if (content) {
        yield content;
      }
    }
  })();
}