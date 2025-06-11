'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ArrowLeft,
  Plus,
  Database,
  FileText,
  Users,
  ExternalLink,
  CheckCircle,
  AlertCircle,
  Loader2,
  Settings,
  Trash2,
  RefreshCw,
  Globe,
  Zap,
  Clock,
  MoreHorizontal
} from 'lucide-react';
import Link from 'next/link';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';

interface Workspace {
  id: string;
  name: string;
  type: 'workspace' | 'database' | 'page';
  documentCount: number;
  lastSync: string;
  status: 'active' | 'syncing' | 'error' | 'pending';
  notionUrl: string;
  permissions: string[];
  syncEnabled: boolean;
}

export default function WorkspacesPage() {
  const [isConnecting, setIsConnecting] = useState(false);
  const [newWorkspaceUrl, setNewWorkspaceUrl] = useState('');
  const [workspaces, setWorkspaces] = useState<Workspace[]>([
    {
      id: 'ws-1',
      name: 'Product Documentation',
      type: 'workspace',
      documentCount: 156,
      lastSync: '2 minutes ago',
      status: 'active',
      notionUrl: 'https://notion.so/product-docs',
      permissions: ['read', 'write'],
      syncEnabled: true
    },
    {
      id: 'ws-2',
      name: 'Meeting Notes',
      type: 'database',
      documentCount: 43,
      lastSync: '5 minutes ago',
      status: 'active',
      notionUrl: 'https://notion.so/meeting-notes',
      permissions: ['read'],
      syncEnabled: true
    },
    {
      id: 'ws-3',
      name: 'Project Roadmap',
      type: 'page',
      documentCount: 12,
      lastSync: '1 hour ago',
      status: 'syncing',
      notionUrl: 'https://notion.so/roadmap',
      permissions: ['read'],
      syncEnabled: true
    }
  ]);

  const handleConnectWorkspace = async () => {
    if (!newWorkspaceUrl.trim()) return;
    
    setIsConnecting(true);
    
    // Simulate connection process
    setTimeout(() => {
      const newWorkspace: Workspace = {
        id: `ws-${Date.now()}`,
        name: 'New Workspace',
        type: 'workspace',
        documentCount: 0,
        lastSync: 'Just now',
        status: 'pending',
        notionUrl: newWorkspaceUrl,
        permissions: ['read'],
        syncEnabled: false
      };
      
      setWorkspaces(prev => [...prev, newWorkspace]);
      setNewWorkspaceUrl('');
      setIsConnecting(false);
    }, 2000);
  };

  const handleDisconnectWorkspace = (workspaceId: string) => {
    setWorkspaces(prev => prev.filter(w => w.id !== workspaceId));
  };

  const handleSyncWorkspace = (workspaceId: string) => {
    setWorkspaces(prev => prev.map(w => 
      w.id === workspaceId 
        ? { ...w, status: 'syncing' as const, lastSync: 'Syncing...' }
        : w
    ));

    // Simulate sync completion
    setTimeout(() => {
      setWorkspaces(prev => prev.map(w => 
        w.id === workspaceId 
          ? { ...w, status: 'active' as const, lastSync: 'Just now' }
          : w
      ));
    }, 3000);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'syncing': return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'error': return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'pending': return <Clock className="h-4 w-4 text-yellow-500" />;
      default: return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'workspace': return <Users className="h-4 w-4" />;
      case 'database': return <Database className="h-4 w-4" />;
      case 'page': return <FileText className="h-4 w-4" />;
      default: return <Globe className="h-4 w-4" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-600 bg-green-50 border-green-200';
      case 'syncing': return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'error': return 'text-red-600 bg-red-50 border-red-200';
      case 'pending': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const totalDocuments = workspaces.reduce((sum, w) => sum + w.documentCount, 0);
  const activeWorkspaces = workspaces.filter(w => w.status === 'active').length;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto p-8 space-y-8">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          
          <div>
            <h1 className="text-3xl font-bold">Workspace Management</h1>
            <p className="text-muted-foreground">
              Connect and manage your Notion workspaces for AI-powered search and chat
            </p>
          </div>
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Connected Workspaces</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{workspaces.length}</div>
              <p className="text-xs text-muted-foreground">{activeWorkspaces} active</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Documents</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalDocuments.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">Indexed and searchable</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Sync Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">Real-time</div>
              <p className="text-xs text-muted-foreground">Webhook enabled</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Last Update</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">2m</div>
              <p className="text-xs text-muted-foreground">ago</p>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="workspaces" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="workspaces">My Workspaces</TabsTrigger>
            <TabsTrigger value="connect">Connect New</TabsTrigger>
          </TabsList>

          <TabsContent value="workspaces" className="space-y-6">
            {/* Workspace List */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  Connected Workspaces
                </CardTitle>
                <CardDescription>
                  Manage your connected Notion workspaces and their sync settings
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {workspaces.map((workspace) => (
                    <div key={workspace.id} className="flex items-center gap-4 p-4 rounded-lg border hover:bg-accent transition-colors">
                      <div className="p-2 rounded-lg bg-muted">
                        {getTypeIcon(workspace.type)}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-medium text-sm">{workspace.name}</h3>
                          <Badge 
                            variant="outline" 
                            className={`text-xs ${getStatusColor(workspace.status)}`}
                          >
                            <div className="flex items-center gap-1">
                              {getStatusIcon(workspace.status)}
                              {workspace.status}
                            </div>
                          </Badge>
                          {workspace.syncEnabled && (
                            <Badge variant="secondary" className="text-xs">
                              <Zap className="h-3 w-3 mr-1" />
                              Auto-sync
                            </Badge>
                          )}
                        </div>
                        
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span>{workspace.documentCount} documents</span>
                          <span>•</span>
                          <span>Last sync: {workspace.lastSync}</span>
                          <span>•</span>
                          <span className="capitalize">{workspace.type}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleSyncWorkspace(workspace.id)}
                          disabled={workspace.status === 'syncing'}
                        >
                          <RefreshCw className={`h-4 w-4 ${workspace.status === 'syncing' ? 'animate-spin' : ''}`} />
                        </Button>

                        <Button variant="ghost" size="icon" asChild>
                          <a href={workspace.notionUrl} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        </Button>

                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Settings className="mr-2 h-4 w-4" />
                              Settings
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                              onClick={() => handleDisconnectWorkspace(workspace.id)}
                              className="text-red-600"
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Disconnect
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="connect" className="space-y-6">
            {/* Connection Methods */}
            <div className="grid md:grid-cols-2 gap-6">
              {/* OAuth Connection */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Plus className="h-5 w-5" />
                    Connect via OAuth
                  </CardTitle>
                  <CardDescription>
                    Recommended method for secure workspace connection
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-sm">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span>Secure OAuth 2.0 authentication</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span>Automatic permission management</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span>Real-time webhook setup</span>
                    </div>
                  </div>

                  <Button className="w-full" size="lg">
                    <Plus className="mr-2 h-4 w-4" />
                    Connect with Notion
                  </Button>
                </CardContent>
              </Card>

              {/* Manual Connection */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Globe className="h-5 w-5" />
                    Manual Connection
                  </CardTitle>
                  <CardDescription>
                    Connect using a Notion page or database URL
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="workspace-url">Notion URL</Label>
                    <Input
                      id="workspace-url"
                      placeholder="https://notion.so/your-workspace"
                      value={newWorkspaceUrl}
                      onChange={(e) => setNewWorkspaceUrl(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">
                      Enter the URL of a Notion page, database, or workspace you want to connect
                    </p>
                  </div>

                  <Button 
                    className="w-full" 
                    variant="outline"
                    onClick={handleConnectWorkspace}
                    disabled={!newWorkspaceUrl.trim() || isConnecting}
                  >
                    {isConnecting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Connecting...
                      </>
                    ) : (
                      <>
                        <Plus className="mr-2 h-4 w-4" />
                        Connect Workspace
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            </div>

            {/* Setup Instructions */}
            <Card>
              <CardHeader>
                <CardTitle>Setup Instructions</CardTitle>
                <CardDescription>
                  Follow these steps to connect your Notion workspace
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-4">
                  <div className="flex gap-4">
                    <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold text-sm">
                      1
                    </div>
                    <div>
                      <h4 className="font-medium">Create Notion Integration</h4>
                      <p className="text-sm text-muted-foreground">
                        Go to <a href="https://www.notion.so/my-integrations" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">notion.so/my-integrations</a> and create a new integration
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold text-sm">
                      2
                    </div>
                    <div>
                      <h4 className="font-medium">Share Pages with Integration</h4>
                      <p className="text-sm text-muted-foreground">
                        In Notion, share the pages or databases you want to connect with your integration
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold text-sm">
                      3
                    </div>
                    <div>
                      <h4 className="font-medium">Connect via OAuth or URL</h4>
                      <p className="text-sm text-muted-foreground">
                        Use the OAuth button above for automatic setup, or manually enter the URL of your shared content
                      </p>
                    </div>
                  </div>
                </div>

                <Separator />

                <div className="flex gap-2">
                  <Button variant="outline" size="sm" asChild>
                    <Link href="/setup">
                      <ExternalLink className="mr-2 h-4 w-4" />
                      View Full Setup Guide
                    </Link>
                  </Button>
                  <Button variant="outline" size="sm" asChild>
                    <a href="https://developers.notion.com/docs/getting-started" target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="mr-2 h-4 w-4" />
                      Notion API Docs
                    </a>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}