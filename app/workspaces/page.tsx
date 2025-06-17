'use client';

import { useState } from 'react';
import { useNotionConnection } from '@/hooks/use-notion-connection';
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

export default function WorkspacesPage() {
  const [isConnecting, setIsConnecting] = useState(false);
  const [newWorkspaceUrl, setNewWorkspaceUrl] = useState('');
  const { connection, isConnected, loading, error, connectNotion, syncNotion } = useNotionConnection();

  const handleConnectNotion = async () => {
    if (!newWorkspaceUrl.trim()) return;
    
    setIsConnecting(true);
    
    try {
      await connectNotion(newWorkspaceUrl);
      setNewWorkspaceUrl('');
    } catch (error) {
      console.error('Failed to connect Notion:', error);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleSyncNotion = async () => {
    try {
      await syncNotion();
    } catch (error) {
      console.error('Failed to sync Notion:', error);
    }
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

  const getTypeIcon = () => {
    return <Database className="h-4 w-4" />;
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

  const totalDocuments = connection?.document_count || 0;
  const connectionStatus = connection?.status || 'pending';

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
            <h1 className="text-3xl font-bold">Notion Connection</h1>
            <p className="text-muted-foreground">
              Connect and manage your Notion workspace for AI-powered search and chat
            </p>
          </div>
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Connection Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{isConnected ? 'Connected' : 'Not Connected'}</div>
              <p className="text-xs text-muted-foreground">{connection?.name || 'No workspace'}</p>
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
              <div className="text-2xl font-bold">{connectionStatus === 'active' ? 'Active' : 'Pending'}</div>
              <p className="text-xs text-muted-foreground">{isConnected ? 'Real-time sync' : 'Not syncing'}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Last Update</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {connection?.last_sync_at ? new Date(connection.last_sync_at).toLocaleTimeString() : 'Never'}
              </div>
              <p className="text-xs text-muted-foreground">Last sync</p>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="connection" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="connection">My Connection</TabsTrigger>
            <TabsTrigger value="connect">Connect Notion</TabsTrigger>
          </TabsList>

          <TabsContent value="connection" className="space-y-6">
            {/* Notion Connection */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  Notion Connection
                </CardTitle>
                <CardDescription>
                  Manage your Notion workspace connection and sync settings
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {loading ? (
                    <div className="flex items-center justify-center p-8">
                      <Loader2 className="h-6 w-6 animate-spin" />
                      <span className="ml-2">Loading connection...</span>
                    </div>
                  ) : error ? (
                    <div className="text-center p-8 text-red-600">
                      Error loading connection: {error}
                    </div>
                  ) : !connection ? (
                    <div className="text-center p-8 text-muted-foreground">
                      No Notion workspace connected yet. Use the &quot;Connect Notion&quot; tab to get started.
                    </div>
                  ) : (
                    <div className="flex items-center gap-4 p-4 rounded-lg border hover:bg-accent transition-colors">
                      <div className="p-2 rounded-lg bg-muted">
                        {getTypeIcon()}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-medium text-sm">{connection.name}</h3>
                          <Badge 
                            variant="outline" 
                            className={`text-xs ${getStatusColor(connection.status)}`}
                          >
                            <div className="flex items-center gap-1">
                              {getStatusIcon(connection.status)}
                              {connection.status}
                            </div>
                          </Badge>
                          {connection.is_active && (
                            <Badge variant="secondary" className="text-xs">
                              <Zap className="h-3 w-3 mr-1" />
                              Auto-sync
                            </Badge>
                          )}
                        </div>
                        
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span>{connection.document_count || 0} documents</span>
                          <span>•</span>
                          <span>Last sync: {connection.last_sync_at ? new Date(connection.last_sync_at).toLocaleString() : 'Never'}</span>
                          <span>•</span>
                          <span>Workspace</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={handleSyncNotion}
                          disabled={connection.status === 'syncing'}
                        >
                          <RefreshCw className={`h-4 w-4 ${connection.status === 'syncing' ? 'animate-spin' : ''}`} />
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
                            <DropdownMenuItem className="text-red-600">
                              <Trash2 className="mr-2 h-4 w-4" />
                              Disconnect
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                  )}
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
                    onClick={handleConnectNotion}
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
                        Connect Notion
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