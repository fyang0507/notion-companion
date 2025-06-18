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
    { key: 'NOTION_CLIENT_ID', description: 'Notion integration client ID' },
    { key: 'NOTION_CLIENT_SECRET', description: 'Notion integration client secret' },
    { key: 'COHERE_API_KEY', description: 'Cohere API key for reranking (optional)' }
  ];

  const sqlScript = `-- Enable pgvector extension
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

-- Create workspaces table
CREATE TABLE IF NOT EXISTS workspaces (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  notion_workspace_id text NOT NULL,
  name text NOT NULL,
  type text NOT NULL,
  document_count integer DEFAULT 0,
  last_sync timestamptz DEFAULT now(),
  status text DEFAULT 'active',
  created_at timestamptz DEFAULT now()
);

-- Create documents table with vector embeddings
CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid REFERENCES workspaces(id) ON DELETE CASCADE,
  notion_page_id text NOT NULL,
  title text NOT NULL,
  content text NOT NULL,
  embedding vector(1536), -- OpenAI embedding dimension
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create chat_sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  workspace_id uuid REFERENCES workspaces(id) ON DELETE CASCADE,
  title text NOT NULL,
  messages jsonb DEFAULT '[]',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create api_usage table
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
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can read own data" ON users FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own data" ON users FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can read own workspaces" ON workspaces FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Users can manage own workspaces" ON workspaces FOR ALL USING (user_id = auth.uid());

CREATE POLICY "Users can read workspace documents" ON documents FOR SELECT USING (
  workspace_id IN (SELECT id FROM workspaces WHERE user_id = auth.uid())
);

CREATE POLICY "Users can read own chat sessions" ON chat_sessions FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Users can manage own chat sessions" ON chat_sessions FOR ALL USING (user_id = auth.uid());

CREATE POLICY "Users can read own usage" ON api_usage FOR SELECT USING (user_id = auth.uid());

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS documents_workspace_id_idx ON documents(workspace_id);
CREATE INDEX IF NOT EXISTS workspaces_user_id_idx ON workspaces(user_id);

-- Create function for vector similarity search
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(1536),
  workspace_id uuid,
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 10
)
RETURNS TABLE (
  id uuid,
  title text,
  content text,
  metadata jsonb,
  notion_page_id text,
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
    d.metadata,
    d.notion_page_id,
    1 - (d.embedding <=> query_embedding) AS similarity
  FROM documents d
  WHERE d.workspace_id = match_documents.workspace_id
    AND 1 - (d.embedding <=> query_embedding) > match_threshold
  ORDER BY d.embedding <=> query_embedding
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
              Complete setup for your Notion Companion application
            </p>
          </div>
        </div>



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
              <span>Notion workspace with admin access</span>
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
                <CardDescription>Run this SQL script in your Supabase SQL Editor</CardDescription>
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
              You're All Set!
            </CardTitle>
            <CardDescription>
              Once you've completed all steps above, you can start using Notion Companion.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm font-medium">Next steps:</p>
              <ol className="space-y-1 text-sm text-muted-foreground">
                <li>1. Start your development server: <code className="bg-muted px-1 rounded">npm run dev</code></li>
                <li>2. Visit your application and sign up</li>
                <li>3. Connect your first Notion workspace</li>
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
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}