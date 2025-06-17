'use client';

import { useWorkspaces } from '@/hooks/use-workspaces';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  MessageSquarePlus,
  TrendingUp,
  Clock,
  FileText,
  Database,
  Users,
  Zap,
  BarChart3,
  Calendar,
  ArrowRight,
  Bot
} from 'lucide-react';
import Link from 'next/link';

interface DashboardHomeProps {
  onSelectWorkspace: (id: string) => void;
  onNewChat: () => void;
  onStartGlobalChat: () => void;
}

export function DashboardHome({ onSelectWorkspace, onNewChat, onStartGlobalChat }: DashboardHomeProps) {
  const { workspaces, loading } = useWorkspaces();
  
  const recentActivity = [
    {
      id: '1',
      type: 'chat',
      title: 'Product roadmap discussion',
      workspace: 'Product Documentation',
      time: '2 hours ago',
      messages: 8
    },
    {
      id: '2',
      type: 'sync',
      title: 'Meeting Notes database updated',
      workspace: 'Meeting Notes',
      time: '4 hours ago',
      documents: 3
    },
    {
      id: '3',
      type: 'search',
      title: 'API authentication queries',
      workspace: 'Product Documentation',
      time: '1 day ago',
      results: 12
    }
  ];

  const workspaceStats = workspaces.map(workspace => ({
    name: workspace.name,
    id: workspace.id,
    documents: workspace.document_count || 0,
    lastSync: workspace.last_sync_at ? new Date(workspace.last_sync_at).toLocaleString() : 'Never',
    status: workspace.status,
    icon: <Database className="h-4 w-4" />
  }));

  const quickActions = [
    {
      title: 'Start Chat',
      description: 'Search and chat across all your workspaces with intelligent filtering',
      icon: <MessageSquarePlus className="h-5 w-5" />,
      action: onStartGlobalChat,
      primary: true
    },
    {
      title: 'View Analytics',
      description: 'Check usage stats and performance metrics for your AI assistant',
      icon: <BarChart3 className="h-5 w-5" />,
      href: '/analytics',
      primary: false
    }
  ];

  const totalDocuments = workspaces.reduce((sum, w) => sum + (w.document_count || 0), 0);
  
  const usageStats = {
    tokensUsed: 0,
    tokensLimit: 100000,
    chatsToday: 0,
    documentsProcessed: totalDocuments
  };

  const usagePercentage = (usageStats.tokensUsed / usageStats.tokensLimit) * 100;

  return (
    <div className="flex-1 overflow-auto">
      <div className="max-w-7xl mx-auto p-4 md:p-8 space-y-6 md:space-y-8">
        {/* Welcome Header */}
        <div className="space-y-2">
          <h1 className="text-2xl md:text-3xl font-bold">Welcome back!</h1>
          <p className="text-muted-foreground text-base md:text-lg">
            Your AI knowledge assistant is ready. What would you like to explore today?
          </p>
        </div>

        {/* Quick Actions */}
        <div className="grid gap-4 md:grid-cols-2">
          {quickActions.map((action, index) => {
            const CardComponent = (
              <Card 
                key={index} 
                className={`cursor-pointer transition-all hover:shadow-md h-full flex flex-col ${
                  action.primary ? 'border-primary bg-primary/5' : ''
                }`}
                onClick={action.action}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-3">
                    <div className={`p-3 rounded-lg ${
                      action.primary ? 'bg-primary text-primary-foreground' : 'bg-muted'
                    }`}>
                      {action.icon}
                    </div>
                    <div>
                      <CardTitle className="text-lg md:text-xl">{action.title}</CardTitle>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="flex-1">
                  <CardDescription className="text-sm md:text-base">
                    {action.description}
                  </CardDescription>
                </CardContent>
              </Card>
            );

            return action.href ? (
              <Link key={index} href={action.href} className="h-full">
                {CardComponent}
              </Link>
            ) : CardComponent;
          })}
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Usage Overview */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg md:text-xl">
                <TrendingUp className="h-5 w-5" />
                Usage Overview
              </CardTitle>
              <CardDescription className="text-sm md:text-base">
                Your activity and token consumption this month
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Token Usage</span>
                  <span className="text-xs md:text-sm text-muted-foreground">
                    {usageStats.tokensUsed.toLocaleString()} / {usageStats.tokensLimit.toLocaleString()}
                  </span>
                </div>
                <Progress value={usagePercentage} className="h-2" />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>{Math.round(usagePercentage)}% used</span>
                  <span>{(usageStats.tokensLimit - usageStats.tokensUsed).toLocaleString()} remaining</span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 md:gap-4">
                <div className="text-center">
                  <div className="text-lg md:text-2xl font-bold">{usageStats.chatsToday}</div>
                  <div className="text-xs text-muted-foreground">Chats today</div>
                </div>
                <div className="text-center">
                  <div className="text-lg md:text-2xl font-bold">{usageStats.documentsProcessed}</div>
                  <div className="text-xs text-muted-foreground">Documents indexed</div>
                </div>
                <div className="text-center">
                  <div className="text-lg md:text-2xl font-bold">1.2s</div>
                  <div className="text-xs text-muted-foreground">Avg response time</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Connected Workspaces */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg md:text-xl">
                <Database className="h-5 w-5" />
                Workspaces
              </CardTitle>
              <CardDescription className="text-sm md:text-base">
                Your connected Notion workspaces
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {workspaceStats.map((workspace) => (
                <div 
                  key={workspace.id}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent cursor-pointer transition-colors"
                  onClick={() => onSelectWorkspace(workspace.id)}
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="p-1.5 rounded bg-muted flex-shrink-0">
                      {workspace.icon}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-sm truncate">{workspace.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {workspace.documents} docs • {workspace.lastSync}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <div className={`w-2 h-2 rounded-full ${
                      workspace.status === 'active' ? 'bg-green-500' : 'bg-yellow-500 animate-pulse'
                    }`} />
                    <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg md:text-xl">
              <Clock className="h-5 w-5" />
              Recent Activity
            </CardTitle>
            <CardDescription className="text-sm md:text-base">
              Your latest interactions and workspace updates
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivity.map((activity) => (
                <div key={activity.id} className="flex items-center gap-4 p-3 rounded-lg border">
                  <div className="p-2 rounded-lg bg-muted flex-shrink-0">
                    {activity.type === 'chat' && <MessageSquarePlus className="h-4 w-4" />}
                    {activity.type === 'sync' && <Zap className="h-4 w-4" />}
                    {activity.type === 'search' && <BarChart3 className="h-4 w-4" />}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{activity.title}</p>
                    <div className="flex flex-wrap items-center gap-1 md:gap-2 text-xs text-muted-foreground">
                      <span className="truncate">{activity.workspace}</span>
                      <span className="hidden md:inline">•</span>
                      <span>{activity.time}</span>
                      {activity.messages && (
                        <>
                          <span className="hidden md:inline">•</span>
                          <span>{activity.messages} messages</span>
                        </>
                      )}
                      {activity.documents && (
                        <>
                          <span className="hidden md:inline">•</span>
                          <span>{activity.documents} documents</span>
                        </>
                      )}
                      {activity.results && (
                        <>
                          <span className="hidden md:inline">•</span>
                          <span>{activity.results} results</span>
                        </>
                      )}
                    </div>
                  </div>

                  <Badge variant="outline" className="text-xs flex-shrink-0">
                    {activity.type}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Tips & Getting Started */}
        <Card className="border-blue-200 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-950/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg md:text-xl">
              <Bot className="h-5 w-5 text-blue-600" />
              Pro Tips
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <p className="text-sm font-medium">Get the most out of Notion Companion:</p>
              <ul className="space-y-1 text-sm text-muted-foreground">
                <li>• Use filters to narrow down search scope for more precise results</li>
                <li>• Start with global chat to search across all workspaces at once</li>
                <li>• Ask specific questions about your documents for better results</li>
                <li>• Check citations to verify information from original sources</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}