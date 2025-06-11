'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Activity,
  Clock,
  MessageSquare,
  Search,
  Database,
  Zap,
  DollarSign,
  Users,
  FileText,
  Calendar,
  Filter,
  Pin,
  ExternalLink
} from 'lucide-react';
import Link from 'next/link';

export default function AnalyticsPage() {
  const [selectedPeriod, setSelectedPeriod] = useState('7d');
  const [selectedType, setSelectedType] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const overviewStats = {
    totalTokens: 245780,
    monthlyLimit: 100000,
    totalChats: 156,
    totalSearches: 89,
    avgResponseTime: 1.2,
    costThisMonth: 24.56,
    documentsProcessed: 1247,
    activeWorkspaces: 3,
    successRate: 98.7
  };

  const weeklyData = [
    { day: 'Mon', tokens: 8500, chats: 12, searches: 8, cost: 0.17 },
    { day: 'Tue', tokens: 12300, chats: 18, searches: 15, cost: 0.25 },
    { day: 'Wed', tokens: 9800, chats: 14, searches: 11, cost: 0.20 },
    { day: 'Thu', tokens: 15600, chats: 22, searches: 19, cost: 0.31 },
    { day: 'Fri', tokens: 11200, chats: 16, searches: 13, cost: 0.22 },
    { day: 'Sat', tokens: 6400, chats: 9, searches: 6, cost: 0.13 },
    { day: 'Sun', tokens: 4200, chats: 6, searches: 4, cost: 0.08 }
  ];

  const workspaceUsage = [
    { name: 'Product Documentation', tokens: 125000, percentage: 51, chats: 89, documents: 156 },
    { name: 'Meeting Notes', tokens: 78000, percentage: 32, chats: 45, documents: 43 },
    { name: 'Project Roadmap', tokens: 42780, percentage: 17, chats: 22, documents: 12 }
  ];

  const recentOperations = [
    {
      id: '1',
      timestamp: '2024-01-15 14:30:22',
      type: 'chat',
      operation: 'Chat Response',
      workspace: 'Product Documentation',
      query: 'API authentication methods',
      tokens: 1250,
      cost: 0.025,
      duration: 1.2,
      status: 'success'
    },
    {
      id: '2',
      timestamp: '2024-01-15 14:28:15',
      type: 'search',
      operation: 'Document Search',
      workspace: 'Product Documentation',
      query: 'user onboarding flow',
      tokens: 450,
      cost: 0.009,
      duration: 0.8,
      status: 'success'
    },
    {
      id: '3',
      timestamp: '2024-01-15 14:25:33',
      type: 'embedding',
      operation: 'Document Processing',
      workspace: 'Meeting Notes',
      query: 'New document sync',
      tokens: 2100,
      cost: 0.021,
      duration: 2.1,
      status: 'success'
    },
    {
      id: '4',
      timestamp: '2024-01-15 14:20:45',
      type: 'chat',
      operation: 'Chat Response',
      workspace: 'Project Roadmap',
      query: 'Q4 roadmap milestones',
      tokens: 890,
      cost: 0.018,
      duration: 1.5,
      status: 'success'
    },
    {
      id: '5',
      timestamp: '2024-01-15 14:18:12',
      type: 'sync',
      operation: 'Workspace Sync',
      workspace: 'Product Documentation',
      query: 'Automatic sync',
      tokens: 3200,
      cost: 0.064,
      duration: 4.2,
      status: 'success'
    }
  ];

  const topQueries = [
    { query: 'API authentication methods', count: 23, workspace: 'Product Documentation', avgTokens: 1200 },
    { query: 'Q4 roadmap milestones', count: 18, workspace: 'Project Roadmap', avgTokens: 890 },
    { query: 'Meeting action items', count: 15, workspace: 'Meeting Notes', avgTokens: 650 },
    { query: 'User onboarding flow', count: 12, workspace: 'Product Documentation', avgTokens: 1100 },
    { query: 'Performance metrics', count: 9, workspace: 'Meeting Notes', avgTokens: 780 }
  ];

  const getOperationIcon = (type: string) => {
    switch (type) {
      case 'chat': return <MessageSquare className="h-4 w-4" />;
      case 'search': return <Search className="h-4 w-4" />;
      case 'embedding': return <FileText className="h-4 w-4" />;
      case 'sync': return <Zap className="h-4 w-4" />;
      default: return <BarChart3 className="h-4 w-4" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'text-green-600 bg-green-50 border-green-200';
      case 'error': return 'text-red-600 bg-red-50 border-red-200';
      case 'pending': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const filteredOperations = recentOperations.filter(item => {
    const matchesType = selectedType === 'all' || item.type === selectedType;
    const matchesSearch = !searchQuery || 
      item.query.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.workspace.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesSearch;
  });

  const usagePercentage = (overviewStats.totalTokens / overviewStats.monthlyLimit) * 100;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto p-8 space-y-8">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          
          <div>
            <h1 className="text-3xl font-bold">Analytics & Usage</h1>
            <p className="text-muted-foreground">
              Comprehensive insights into your AI assistant usage and performance
            </p>
          </div>
        </div>

        {/* Overview Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Tokens</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{overviewStats.totalTokens.toLocaleString()}</div>
              <div className="flex items-center gap-1 text-xs text-green-600">
                <TrendingUp className="h-3 w-3" />
                <span>+12% from last month</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Operations</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{overviewStats.totalChats + overviewStats.totalSearches}</div>
              <div className="flex items-center gap-1 text-xs text-green-600">
                <TrendingUp className="h-3 w-3" />
                <span>+8% from last month</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Success Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{overviewStats.successRate}%</div>
              <div className="flex items-center gap-1 text-xs text-green-600">
                <TrendingUp className="h-3 w-3" />
                <span>+2% from last month</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Monthly Cost</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${overviewStats.costThisMonth}</div>
              <div className="flex items-center gap-1 text-xs text-red-600">
                <TrendingUp className="h-3 w-3" />
                <span>+15% from last month</span>
              </div>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="usage">Usage Trends</TabsTrigger>
            <TabsTrigger value="workspaces">Workspaces</TabsTrigger>
            <TabsTrigger value="operations">Operations Log</TabsTrigger>
            <TabsTrigger value="insights">Insights</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            {/* Token Usage Overview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Token Usage This Month
                </CardTitle>
                <CardDescription>
                  Track your AI token consumption and remaining quota
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Monthly Usage</span>
                    <span className="text-sm text-muted-foreground">
                      {overviewStats.totalTokens.toLocaleString()} / {overviewStats.monthlyLimit.toLocaleString()}
                    </span>
                  </div>
                  <Progress value={usagePercentage} className="h-3" />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{Math.round(usagePercentage)}% used</span>
                    <span>{(overviewStats.monthlyLimit - overviewStats.totalTokens).toLocaleString()} remaining</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quick Stats Grid */}
            <div className="grid md:grid-cols-3 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Avg Response Time</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{overviewStats.avgResponseTime}s</div>
                  <p className="text-xs text-muted-foreground">Across all operations</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Active Workspaces</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{overviewStats.activeWorkspaces}</div>
                  <p className="text-xs text-muted-foreground">Connected and syncing</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Documents Indexed</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{overviewStats.documentsProcessed.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground">Across all workspaces</p>
                </CardContent>
              </Card>
            </div>

            {/* Cost Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5" />
                  Cost Breakdown
                </CardTitle>
                <CardDescription>
                  Detailed cost analysis for this month
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold">$18.40</div>
                    <div className="text-xs text-muted-foreground">OpenAI API</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">$4.20</div>
                    <div className="text-xs text-muted-foreground">Cohere Rerank</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">$1.96</div>
                    <div className="text-xs text-muted-foreground">Supabase</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">$24.56</div>
                    <div className="text-xs text-muted-foreground font-semibold">Total</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="usage" className="space-y-6">
            {/* Weekly Activity */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Weekly Activity Breakdown
                </CardTitle>
                <CardDescription>
                  Your daily usage patterns over the past week
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {weeklyData.map((day) => (
                    <div key={day.day} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-12 text-sm font-medium">{day.day}</div>
                          <div className="text-sm text-muted-foreground">
                            {day.tokens.toLocaleString()} tokens • {day.chats} chats • {day.searches} searches
                          </div>
                        </div>
                        <div className="text-sm font-medium">${day.cost.toFixed(2)}</div>
                      </div>
                      <Progress value={(day.tokens / 16000) * 100} className="h-2" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Usage Metrics */}
            <div className="grid md:grid-cols-3 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Daily Average</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {Math.round(weeklyData.reduce((sum, day) => sum + day.tokens, 0) / weeklyData.length).toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">tokens per day</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Peak Day</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {Math.max(...weeklyData.map(d => d.tokens)).toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">tokens on Thursday</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Weekly Total</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    ${weeklyData.reduce((sum, day) => sum + day.cost, 0).toFixed(2)}
                  </div>
                  <p className="text-xs text-muted-foreground">total cost</p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="workspaces" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  Workspace Usage Breakdown
                </CardTitle>
                <CardDescription>
                  See which workspaces are used most frequently
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {workspaceUsage.map((workspace, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-medium">{workspace.name}</span>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>{workspace.tokens.toLocaleString()} tokens</span>
                        <span>•</span>
                        <span>{workspace.chats} chats</span>
                        <span>•</span>
                        <span>{workspace.documents} docs</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Progress value={workspace.percentage} className="flex-1 h-2" />
                      <span className="text-sm font-medium w-12">{workspace.percentage}%</span>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="operations" className="space-y-6">
            {/* Filters */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Filter className="h-5 w-5" />
                  Filter Operations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-4">
                  <div className="flex-1">
                    <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
                      <SelectTrigger>
                        <SelectValue placeholder="Time Period" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1d">Last 24 hours</SelectItem>
                        <SelectItem value="7d">Last 7 days</SelectItem>
                        <SelectItem value="30d">Last 30 days</SelectItem>
                        <SelectItem value="90d">Last 90 days</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex-1">
                    <Select value={selectedType} onValueChange={setSelectedType}>
                      <SelectTrigger>
                        <SelectValue placeholder="Operation Type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Operations</SelectItem>
                        <SelectItem value="chat">Chat Responses</SelectItem>
                        <SelectItem value="search">Document Search</SelectItem>
                        <SelectItem value="embedding">Document Processing</SelectItem>
                        <SelectItem value="sync">Workspace Sync</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex-1">
                    <Input 
                      placeholder="Search operations..." 
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Operations List */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Recent Operations
                </CardTitle>
                <CardDescription>
                  Detailed log of all AI operations with token usage and costs
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {filteredOperations.map((operation) => (
                    <div key={operation.id} className="flex items-center gap-4 p-4 rounded-lg border hover:bg-accent transition-colors">
                      <div className="p-2 rounded-lg bg-muted">
                        {getOperationIcon(operation.type)}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-medium text-sm">{operation.operation}</p>
                          <Badge 
                            variant="outline" 
                            className={`text-xs ${getStatusColor(operation.status)}`}
                          >
                            {operation.status}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mb-1 truncate">"{operation.query}"</p>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span>{operation.workspace}</span>
                          <span>•</span>
                          <span>{operation.timestamp}</span>
                          <span>•</span>
                          <span>{operation.duration}s</span>
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="font-medium text-sm">{operation.tokens.toLocaleString()} tokens</div>
                        <div className="text-xs text-muted-foreground">${operation.cost.toFixed(3)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="insights" className="space-y-6">
            {/* Top Queries */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Search className="h-5 w-5" />
                  Most Popular Queries
                </CardTitle>
                <CardDescription>
                  The questions and searches you use most often
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {topQueries.map((query, index) => (
                    <div key={index} className="flex items-center justify-between p-3 rounded-lg border">
                      <div className="flex-1">
                        <p className="font-medium text-sm">"{query.query}"</p>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                          <span>{query.workspace}</span>
                          <span>•</span>
                          <span>Avg {query.avgTokens} tokens</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{query.count} times</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Performance Metrics */}
            <div className="grid md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="h-5 w-5" />
                    Response Times
                  </CardTitle>
                  <CardDescription>
                    Average response times by operation type
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Chat responses</span>
                      <span className="font-medium">1.2s</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Document search</span>
                      <span className="font-medium">0.8s</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Workspace sync</span>
                      <span className="font-medium">3.4s</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Document processing</span>
                      <span className="font-medium">2.1s</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="h-5 w-5" />
                    System Health
                  </CardTitle>
                  <CardDescription>
                    Current system performance metrics
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm">API Uptime</span>
                      <Badge variant="outline" className="text-green-600">99.9%</Badge>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Success Rate</span>
                      <Badge variant="outline" className="text-green-600">98.7%</Badge>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Error Rate</span>
                      <Badge variant="outline" className="text-yellow-600">1.3%</Badge>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Avg Token/Query</span>
                      <Badge variant="outline">1,124</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}