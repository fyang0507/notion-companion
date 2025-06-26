'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { 
  ArrowLeft,
  CheckCircle,
  Copy,
  ExternalLink,
  Key,
  Database,
  Webhook,
  Bot,
  Settings,
  AlertCircle,
  Info
} from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

export default function SetupGuide() {
  const [copiedStep, setCopiedStep] = useState<string | null>(null);

  const copyToClipboard = (text: string, stepId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedStep(stepId);
    setTimeout(() => setCopiedStep(null), 2000);
  };

  const steps = [
    {
      id: 'notion-app',
      title: 'Create Notion Integration',
      description: 'Set up a new integration in your Notion workspace',
      items: [
        'Go to https://www.notion.so/my-integrations',
        'Click "New integration"',
        'Name it "Notion Companion"',
        'Select your workspace',
        'Copy the Internal Integration Token'
      ]
    },
    {
      id: 'supabase',
      title: 'Configure Supabase',
      description: 'Set up your database and enable vector search',
      items: [
        'Create a new Supabase project',
        'Go to SQL Editor and run the setup script',
        'Enable pgvector extension',
        'Copy your project URL and anon key'
      ]
    },
    {
      id: 'openai',
      title: 'Get OpenAI API Key',
      description: 'Required for embeddings and chat functionality',
      items: [
        'Visit https://platform.openai.com/api-keys',
        'Create a new API key',
        'Copy the key (starts with sk-)',
        'Ensure you have credits in your account'
      ]
    },
    {
      id: 'env-vars',
      title: 'Environment Variables',
      description: 'Configure your application with the required keys',
      items: []
    }
  ];

  const envVars = [
    { key: 'NEXT_PUBLIC_SUPABASE_URL', description: 'Your Supabase project URL' },
    { key: 'NEXT_PUBLIC_SUPABASE_ANON_KEY', description: 'Supabase anonymous key' },
    { key: 'SUPABASE_SERVICE_ROLE_KEY', description: 'Supabase service role key (for server-side operations)' },
    { key: 'OPENAI_API_KEY', description: 'OpenAI API key for embeddings and chat' },
    { key: 'NOTION_ACCESS_TOKEN', description: 'Notion integration access token' },
    { key: 'COHERE_API_KEY', description: 'Cohere API key for reranking (optional)' }
  ];

  // SINGLE DATABASE MODEL - NO WORKSPACE CONCEPT
  // This webapp supports ONLY ONE Notion workspace with multiple databases
  const sqlScript = `-- Notion Companion Database Schema - Single Database Model
-- This webapp supports ONLY ONE Notion workspace with multiple databases
-- NO workspace concept exists - all operations are per-database

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  notion_access_token text,
  monthly_token_limit integer DEFAULT 100000,
  current_token_usage integer DEFAULT 0
);

-- Create documents table with enhanced vector embeddings
-- NO workspace_id - operates on single workspace with multiple databases
CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  database_id text NOT NULL,
  notion_page_id text UNIQUE NOT NULL,
  notion_database_id text,
  title text NOT NULL,
  content text NOT NULL,
  title_embedding vector(1536),
  content_embedding vector(1536),
  summary_embedding vector(1536),
  page_url text,
  parent_page_id text,
  notion_created_time timestamptz,
  notion_last_edited_time timestamptz,
  content_type text DEFAULT 'document',
  content_length integer DEFAULT 0,
  token_count integer DEFAULT 0,
  notion_properties jsonb DEFAULT '{}',
  extracted_metadata jsonb DEFAULT '{}',
  has_multimedia boolean DEFAULT false,
  multimedia_refs jsonb DEFAULT '[]',
  is_chunked boolean DEFAULT false,
  chunk_count integer DEFAULT 0,
  document_summary text,
  processing_status text DEFAULT 'pending',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create database schemas table (NO workspace_id)
CREATE TABLE IF NOT EXISTS database_schemas (
  database_id text PRIMARY KEY,
  database_name text NOT NULL,
  notion_schema jsonb,
  field_definitions jsonb,
  queryable_fields jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  last_analyzed_at timestamptz
);

-- Create document chunks table
CREATE TABLE IF NOT EXISTS document_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index integer NOT NULL,
  content text NOT NULL,
  embedding vector(1536),
  token_count integer DEFAULT 0,
  content_type text DEFAULT 'text',
  created_at timestamptz DEFAULT now()
);

-- Create document metadata table
CREATE TABLE IF NOT EXISTS document_metadata (
  document_id uuid REFERENCES documents(id) ON DELETE CASCADE,
  field_name text NOT NULL,
  field_type text NOT NULL,
  raw_value jsonb,
  text_value text,
  number_value numeric,
  date_value date,
  datetime_value timestamptz,
  boolean_value boolean,
  array_value jsonb,
  created_at timestamptz DEFAULT now(),
  PRIMARY KEY (document_id, field_name)
);

-- Create chat sessions table (NO workspace_id)
CREATE TABLE IF NOT EXISTS chat_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  title text NOT NULL,
  messages jsonb DEFAULT '[]',
  database_filters jsonb DEFAULT '[]',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create search analytics table (NO workspace_id)
CREATE TABLE IF NOT EXISTS search_analytics (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  query text NOT NULL,
  result_count integer DEFAULT 0,
  clicked_document_id uuid,
  created_at timestamptz DEFAULT now()
);

-- Create api usage table
CREATE TABLE IF NOT EXISTS api_usage (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  endpoint text NOT NULL,
  tokens_used integer NOT NULL,
  cost numeric(10,4) NOT NULL,
  timestamp timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE database_schemas ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (single user model)
CREATE POLICY "Users can read own data" ON users FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own data" ON users FOR UPDATE USING (auth.uid() = id);

-- Documents are accessible to authenticated users (single workspace model)
CREATE POLICY "Users can read documents" ON documents FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY "Users can manage documents" ON documents FOR ALL USING (auth.uid() IS NOT NULL);

-- Database schemas are accessible to authenticated users
CREATE POLICY "Users can read database schemas" ON database_schemas FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY "Users can manage database schemas" ON database_schemas FOR ALL USING (auth.uid() IS NOT NULL);

-- Document chunks follow document permissions
CREATE POLICY "Users can read document chunks" ON document_chunks FOR SELECT USING (
  document_id IN (SELECT id FROM documents WHERE auth.uid() IS NOT NULL)
);
CREATE POLICY "Users can manage document chunks" ON document_chunks FOR ALL USING (
  document_id IN (SELECT id FROM documents WHERE auth.uid() IS NOT NULL)
);

-- Document metadata follows document permissions
CREATE POLICY "Users can read document metadata" ON document_metadata FOR SELECT USING (
  document_id IN (SELECT id FROM documents WHERE auth.uid() IS NOT NULL)
);
CREATE POLICY "Users can manage document metadata" ON document_metadata FOR ALL USING (
  document_id IN (SELECT id FROM documents WHERE auth.uid() IS NOT NULL)
);

CREATE POLICY "Users can read own chat sessions" ON chat_sessions FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Users can manage own chat sessions" ON chat_sessions FOR ALL USING (user_id = auth.uid());

CREATE POLICY "Users can read own search analytics" ON search_analytics FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Users can create search analytics" ON search_analytics FOR INSERT USING (user_id = auth.uid());

CREATE POLICY "Users can read own usage" ON api_usage FOR SELECT USING (user_id = auth.uid());

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS documents_title_embedding_idx ON documents USING ivfflat (title_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS documents_content_embedding_idx ON documents USING ivfflat (content_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS documents_summary_embedding_idx ON documents USING ivfflat (summary_embedding vector_cosine_ops) WHERE summary_embedding IS NOT NULL;
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx ON document_chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS documents_database_id_idx ON documents(database_id);
CREATE INDEX IF NOT EXISTS documents_notion_page_id_idx ON documents(notion_page_id);
CREATE INDEX IF NOT EXISTS document_chunks_document_id_idx ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS document_metadata_document_id_idx ON document_metadata(document_id);
CREATE INDEX IF NOT EXISTS database_schemas_database_id_idx ON database_schemas(database_id);

-- Create function for enhanced vector similarity search by content
CREATE OR REPLACE FUNCTION match_documents_by_content(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 10,
  database_ids text[] DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  title text,
  content text,
  extracted_metadata jsonb,
  notion_page_id text,
  database_id text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id,
    d.title,
    d.content,
    d.extracted_metadata,
    d.notion_page_id,
    d.database_id,
    1 - (d.content_embedding <=> query_embedding) AS similarity
  FROM documents d
  WHERE (database_ids IS NULL OR d.database_id = ANY(database_ids))
    AND d.content_embedding IS NOT NULL
    AND 1 - (d.content_embedding <=> query_embedding) > match_threshold
  ORDER BY d.content_embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Create function for chunk-level search
CREATE OR REPLACE FUNCTION match_document_chunks(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 10,
  database_ids text[] DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  document_id uuid,
  content text,
  chunk_index integer,
  similarity float,
  document_title text,
  database_id text
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    dc.id,
    dc.document_id,
    dc.content,
    dc.chunk_index,
    1 - (dc.embedding <=> query_embedding) AS similarity,
    d.title as document_title,
    d.database_id
  FROM document_chunks dc
  JOIN documents d ON dc.document_id = d.id
  WHERE (database_ids IS NULL OR d.database_id = ANY(database_ids))
    AND dc.embedding IS NOT NULL
    AND 1 - (dc.embedding <=> query_embedding) > match_threshold
  ORDER BY dc.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;`;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto p-8 space-y-8">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          
          <div>
            <h1 className="text-3xl font-bold">Setup Guide</h1>
            <p className="text-muted-foreground">
              Complete setup for your Notion Companion application (Single Database Model)
            </p>
          </div>
        </div>

        {/* Important Notice */}
        <Card className="border-yellow-200 bg-yellow-50/50 dark:border-yellow-800 dark:bg-yellow-950/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-yellow-600" />
              Single Database Model
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm">
              <strong>This webapp is designed to support ONLY ONE Notion workspace with multiple databases.</strong>
            </p>
            <p className="text-sm text-muted-foreground">
              No workspace concept exists - all operations are per-database. Configure your NOTION_ACCESS_TOKEN 
              for the single workspace you want to use.
            </p>
          </CardContent>
        </Card>

        {/* Prerequisites */}
        <Card className="border-blue-200 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-950/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Info className="h-5 w-5 text-blue-600" />
              Prerequisites
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <span>ONE Notion workspace with admin access</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <span>Supabase account (free tier available)</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <span>OpenAI API account with credits</span>
            </div>
          </CardContent>
        </Card>

        {/* Setup Steps */}
        <div className="space-y-6">
          {steps.map((step, index) => (
            <Card key={step.id}>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold">
                    {index + 1}
                  </div>
                  <div>
                    <CardTitle>{step.title}</CardTitle>
                    <CardDescription>{step.description}</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {step.id === 'env-vars' ? (
                  <div className="space-y-4">
                    <p className="text-sm text-muted-foreground">
                      Create a <code className="bg-muted px-1 rounded">.env.local</code> file in your project root with these variables:
                    </p>
                    
                    <div className="space-y-3">
                      {envVars.map((envVar) => (
                        <div key={envVar.key} className="space-y-1">
                          <div className="flex items-center justify-between">
                            <code className="text-sm font-mono bg-muted px-2 py-1 rounded">
                              {envVar.key}=your_value_here
                            </code>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6"
                              onClick={() => copyToClipboard(envVar.key, envVar.key)}
                            >
                              {copiedStep === envVar.key ? (
                                <CheckCircle className="h-3 w-3 text-green-600" />
                              ) : (
                                <Copy className="h-3 w-3" />
                              )}
                            </Button>
                          </div>
                          <p className="text-xs text-muted-foreground">{envVar.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <ol className="space-y-2">
                    {step.items.map((item, itemIndex) => (
                      <li key={itemIndex} className="flex items-start gap-2">
                        <span className="text-sm text-muted-foreground mt-0.5">
                          {itemIndex + 1}.
                        </span>
                        <span className="text-sm">{item}</span>
                      </li>
                    ))}
                  </ol>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Database Setup */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold">
                5
              </div>
              <div>
                <CardTitle>Database Setup</CardTitle>
                <CardDescription>Run this SQL script in your Supabase SQL Editor (Single Database Model)</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Copy and paste this script into your Supabase SQL Editor:
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => copyToClipboard(sqlScript, 'sql-script')}
                >
                  {copiedStep === 'sql-script' ? (
                    <>
                      <CheckCircle className="h-4 w-4 mr-2 text-green-600" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="h-4 w-4 mr-2" />
                      Copy SQL
                    </>
                  )}
                </Button>
              </div>
              
              <div className="bg-muted p-4 rounded-lg overflow-x-auto">
                <pre className="text-xs font-mono whitespace-pre-wrap">
                  {sqlScript}
                </pre>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Final Steps */}
        <Card className="border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              You&apos;re All Set!
            </CardTitle>
            <CardDescription>
              Once you&apos;ve completed all steps above, you can start using Notion Companion.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm font-medium">Next steps:</p>
              <ol className="space-y-1 text-sm text-muted-foreground">
                <li>1. Start your development server: <code className="bg-muted px-1 rounded">pnpm run dev</code></li>
                <li>2. Visit your application and sign up</li>
                <li>3. Configure your databases in the backend config</li>
                <li>4. Start chatting with your knowledge base!</li>
              </ol>
            </div>
            
            <Separator />
            
            <div className="flex gap-2">
              <Link href="/">
                <Button>
                  Return to App
                </Button>
              </Link>
              <Button variant="outline" asChild>
                <a href="https://github.com/your-repo/notion-companion" target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  View Documentation
                </a>
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Troubleshooting */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-yellow-600" />
              Troubleshooting
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <p className="text-sm font-medium">Common Issues:</p>
              <ul className="space-y-1 text-sm text-muted-foreground">
                <li>• <strong>Database connection errors:</strong> Verify your Supabase URL and keys</li>
                <li>• <strong>OpenAI API errors:</strong> Check your API key and account credits</li>
                <li>• <strong>Notion integration issues:</strong> Ensure your integration has proper permissions</li>
                <li>• <strong>Vector search not working:</strong> Confirm pgvector extension is enabled</li>
                <li>• <strong>No workspace found:</strong> Remember this app supports only ONE workspace</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}