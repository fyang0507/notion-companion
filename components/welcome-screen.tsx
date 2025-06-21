'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Bot, 
  Search, 
  Zap, 
  BookOpen, 
  MessageSquare, 
  TrendingUp,
  Plus,
  ExternalLink,
  CheckCircle
} from 'lucide-react';
import Link from 'next/link';

interface WelcomeScreenProps {
  onSelectWorkspace: (id: string) => void;
}

export function WelcomeScreen({ onSelectWorkspace }: WelcomeScreenProps) {
  const features = [
    {
      icon: <Search className="h-5 w-5" />,
      title: 'Intelligent Search',
      description: 'Find information instantly across all your Notion pages with AI-powered semantic search.'
    },
    {
      icon: <MessageSquare className="h-5 w-5" />,
      title: 'Chat Interface',
      description: 'Ask questions in natural language and get answers with source citations from your workspace.'
    },
    {
      icon: <Zap className="h-5 w-5" />,
      title: 'Real-time Sync',
      description: 'Automatically stays updated with your latest Notion content through webhook integration.'
    },
    {
      icon: <TrendingUp className="h-5 w-5" />,
      title: 'Usage Analytics',
      description: 'Track your AI usage, token consumption, and optimize your knowledge base.'
    }
  ];

  const sampleQuestions = [
    "What are the key features planned for Q4?",
    "Summarize the latest meeting notes about the product launch",
    "Find all documents related to user authentication",
    "What decisions were made in yesterday's standup?"
  ];

  return (
    <div className="flex-1 overflow-auto">
      <div className="max-w-4xl mx-auto p-4 md:p-8 space-y-6 md:space-y-8">
        {/* Hero Section */}
        <div className="text-center space-y-4">
          <div className="w-16 h-16 mx-auto rounded-2xl gradient-bg flex items-center justify-center">
            <Bot className="h-8 w-8 text-white" />
          </div>
          
          <div className="space-y-2">
            <h1 className="text-3xl md:text-4xl font-bold">Welcome to Notion Companion</h1>
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
              Your AI-powered knowledge assistant. Connect your Notion workspace and start having intelligent conversations with your content.
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-2">
            <Badge variant="secondary" className="text-sm">
              <CheckCircle className="h-3 w-3 mr-1" />
              Enterprise Ready
            </Badge>
            <Badge variant="secondary" className="text-sm">
              <Zap className="h-3 w-3 mr-1" />
              Real-time Sync
            </Badge>
          </div>
        </div>

        {/* Quick Start */}
        <Card className="border-2 border-primary/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg md:text-xl">
              <Plus className="h-5 w-5" />
              Get Started
            </CardTitle>
            <CardDescription className="text-sm md:text-base">
              Connect your first Notion workspace to begin chatting with your knowledge base.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button size="lg" className="w-full">
              <Plus className="mr-2 h-5 w-5" />
              Connect Notion Workspace
            </Button>
            
            <div className="text-center">
              <Link href="/setup">
                <Button variant="link" className="text-sm text-muted-foreground">
                  <ExternalLink className="mr-2 h-4 w-4" />
                  View setup guide
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Features Grid */}
        <div className="space-y-4">
          <h2 className="text-xl md:text-2xl font-semibold text-center">What you can do</h2>
          
          <div className="grid gap-4 md:grid-cols-2">
            {features.map((feature, index) => (
              <Card key={index} className="hover:shadow-md transition-shadow">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/10 text-primary">
                      {feature.icon}
                    </div>
                    <CardTitle className="text-base md:text-lg">{feature.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-sm md:text-base">
                    {feature.description}
                  </CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Sample Questions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg md:text-xl">
              <MessageSquare className="h-5 w-5" />
              Try asking these questions
            </CardTitle>
            <CardDescription className="text-sm md:text-base">
              Once connected, you can ask questions like these about your Notion content.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3">
              {sampleQuestions.map((question, index) => (
                <div 
                  key={index}
                  className="p-3 rounded-lg border bg-muted/50 hover:bg-muted cursor-pointer transition-colors"
                >
                  <p className="text-sm font-medium">&quot;{question}&quot;</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Demo Workspace */}
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg md:text-xl">
              <BookOpen className="h-5 w-5" />
              Try the Demo
            </CardTitle>
            <CardDescription className="text-sm md:text-base">
              Explore the interface with our sample workspace filled with demo content.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              variant="outline" 
              className="w-full"
              onClick={() => onSelectWorkspace('demo')}
            >
              <BookOpen className="mr-2 h-4 w-4" />
              Open Demo Workspace
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}