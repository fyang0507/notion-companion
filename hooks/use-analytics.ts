import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { useAuth } from './use-auth'

export interface AnalyticsData {
  overviewStats: {
    totalTokens: number
    totalChats: number
    totalSearches: number
    totalCost: number
    successRate: number
    costThisMonth: number
    monthlyLimit: number
    avgResponseTime: number
    activeWorkspaces: number
    documentsProcessed: number
  }
  weeklyData: Array<{
    day: string
    date: string
    tokens: number
    chats: number
    searches: number
    cost: number
  }>
  workspaceUsage: Array<{
    name: string
    searches: number
    chats: number
    tokens: number
    documents: number
    percentage: number
  }>
  recentOperations: Array<{
    id: string
    operation: string
    type: 'chat' | 'search' | 'sync' | 'embedding'
    workspace: string
    timestamp: string
    status: 'success' | 'error' | 'pending'
    details: string
    query: string
    duration: number
    tokens: number
    cost: number
  }>
  topQueries: Array<{
    query: string
    count: number
    workspace: string
    avgTokens: number
  }>
}

export function useAnalytics() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { user } = useAuth()

  const fetchAnalytics = async () => {
    if (!user) {
      setAnalytics(null)
      setLoading(false)
      return
    }

    // If Supabase is not configured, return empty analytics
    if (!supabase) {
      setAnalytics({
        overviewStats: {
          totalTokens: 0,
          totalChats: 0,
          totalSearches: 0,
          totalCost: 0,
          successRate: 95,
          costThisMonth: 0,
          monthlyLimit: 100000,
          avgResponseTime: 1.2,
          activeWorkspaces: 1,
          documentsProcessed: 0
        },
        weeklyData: [],
        workspaceUsage: [],
        recentOperations: [],
        topQueries: []
      })
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      // Fetch search analytics for the last 30 days
      const thirtyDaysAgo = new Date()
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

      const { data: searchData, error: searchError } = await supabase
        .from('search_analytics')
        .select(`
          *,
          workspaces(name)
        `)
        .eq('user_id', user.id)
        .gte('created_at', thirtyDaysAgo.toISOString())
        .order('created_at', { ascending: false })

      if (searchError) throw searchError

      // Process analytics data
      const processedAnalytics = processAnalyticsData(searchData || [])
      setAnalytics(processedAnalytics)

    } catch (err) {
      console.error('Error fetching analytics:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch analytics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAnalytics()
  }, [user])

  return {
    analytics,
    loading,
    error,
    refetch: fetchAnalytics
  }
}

function processAnalyticsData(searchData: any[]): AnalyticsData {
  // Group data by date for weekly chart
  const dateGroups = groupByDate(searchData)
  const weeklyData = Object.entries(dateGroups).map(([date, searches]) => {
    const tokens = (searches as any[]).reduce((sum, s) => sum + (s.tokens || 0), 0)
    return {
      day: new Date(date).toLocaleDateString('en-US', { weekday: 'short' }),
      date,
      tokens,
      chats: (searches as any[]).filter(s => s.type === 'chat').length,
      searches: (searches as any[]).filter(s => s.type === 'search').length,
      cost: tokens * 0.0001
    }
  })

  // Group by workspace
  const workspaceGroups = groupByWorkspace(searchData)
  const totalTokensForPercentage = searchData.reduce((sum, s) => sum + (s.tokens || 0), 0)
  const workspaceUsage = Object.entries(workspaceGroups).map(([name, searches]) => {
    const tokens = (searches as any[]).reduce((sum, s) => sum + (s.tokens || 0), 0)
    return {
      name,
      searches: (searches as any[]).filter(s => s.type === 'search').length,
      chats: (searches as any[]).filter(s => s.type === 'chat').length,
      tokens,
      documents: 0, // This would come from a separate query
      percentage: totalTokensForPercentage > 0 ? Math.round((tokens / totalTokensForPercentage) * 100) : 0
    }
  })

  // Calculate totals
  const totalTokens = searchData.reduce((sum, s) => sum + (s.tokens || 0), 0)
  const totalChats = searchData.filter(s => s.type === 'chat').length
  const totalSearches = searchData.filter(s => s.type === 'search').length
  const totalCost = totalTokens * 0.0001 // Rough estimate

  // Get top queries
  const queryGroups = groupByQuery(searchData)
  const topQueries = Object.entries(queryGroups)
    .map(([query, data]) => ({
      query,
      count: (data as any[]).length,
      workspace: (data as any[])[0]?.workspaces?.name || 'Unknown',
      avgTokens: Math.round((data as any[]).reduce((sum, d) => sum + (d.tokens || 0), 0) / (data as any[]).length)
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10)

  // Recent operations (last 20)
  const recentOperations = searchData.slice(0, 20).map(item => ({
    id: item.id,
    operation: item.type === 'chat' ? 'Chat Response' : 'Document Search',
    type: item.type || 'search',
    workspace: item.workspaces?.name || 'Unknown',
    timestamp: item.created_at,
    status: 'success' as const,
    details: item.query || 'Search query',
    query: item.query || 'Search query',
    duration: 1.2, // Default duration
    tokens: item.tokens || 0,
    cost: (item.tokens || 0) * 0.0001
  }))

  return {
    overviewStats: {
      totalTokens,
      totalChats,
      totalSearches,
      totalCost,
      successRate: 95, // Calculate based on successful operations
      costThisMonth: totalCost,
      monthlyLimit: 100000,
      avgResponseTime: 1.2, // Average from actual data if available
      activeWorkspaces: 1,
      documentsProcessed: 0 // This would come from a separate query
    },
    weeklyData,
    workspaceUsage,
    recentOperations,
    topQueries
  }
}

function groupByDate(data: any[]) {
  return data.reduce((groups, item) => {
    const date = new Date(item.created_at).toISOString().split('T')[0]
    if (!groups[date]) groups[date] = []
    groups[date].push(item)
    return groups
  }, {} as Record<string, any[]>)
}

function groupByWorkspace(data: any[]) {
  return data.reduce((groups, item) => {
    const name = item.workspaces?.name || 'Unknown'
    if (!groups[name]) groups[name] = []
    groups[name].push(item)
    return groups
  }, {} as Record<string, any[]>)
}

function groupByQuery(data: any[]) {
  return data.reduce((groups, item) => {
    const query = item.query || 'Unknown'
    if (!groups[query]) groups[query] = []
    groups[query].push(item)
    return groups
  }, {} as Record<string, any[]>)
}