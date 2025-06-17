import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { useAuth } from './use-auth'

export interface Workspace {
  id: string
  name: string
  icon?: string
  notion_workspace_id: string
  is_active: boolean
  last_sync_at?: string
  document_count?: number
  status: 'active' | 'syncing' | 'error' | 'pending'
}

export function useWorkspaces() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { user } = useAuth()

  const fetchWorkspaces = async () => {
    if (!user) {
      setWorkspaces([])
      setLoading(false)
      return
    }

    // If Supabase is not configured, return empty workspaces
    if (!supabase) {
      setWorkspaces([])
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      // Fetch workspaces with document counts
      const { data: workspacesData, error: workspacesError } = await supabase
        .from('workspaces')
        .select(`
          id,
          name,
          icon,
          notion_workspace_id,
          is_active,
          last_sync_at,
          documents(count)
        `)
        .eq('user_id', user.id)
        .eq('is_active', true)

      if (workspacesError) throw workspacesError

      const workspacesWithCounts = workspacesData?.map(workspace => ({
        id: workspace.id,
        name: workspace.name,
        icon: workspace.icon,
        notion_workspace_id: workspace.notion_workspace_id,
        is_active: workspace.is_active,
        last_sync_at: workspace.last_sync_at,
        document_count: workspace.documents?.[0]?.count || 0,
        status: getWorkspaceStatus(workspace.last_sync_at)
      })) || []

      setWorkspaces(workspacesWithCounts)
    } catch (err) {
      console.error('Error fetching workspaces:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch workspaces')
    } finally {
      setLoading(false)
    }
  }

  const connectWorkspace = async (notionToken: string) => {
    if (!user) throw new Error('User not authenticated')
    if (!supabase) throw new Error('Supabase not configured')

    try {
      // Call backend API to connect workspace
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/notion/connect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          notion_token: notionToken
        })
      })

      if (!response.ok) {
        throw new Error('Failed to connect workspace')
      }

      // Refresh workspaces after connecting
      await fetchWorkspaces()
    } catch (err) {
      console.error('Error connecting workspace:', err)
      throw err
    }
  }

  const syncWorkspace = async (workspaceId: string) => {
    if (!supabase) throw new Error('Supabase not configured')
    
    try {
      // Call backend API to sync workspace
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/notion/sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          workspace_id: workspaceId
        })
      })

      if (!response.ok) {
        throw new Error('Failed to sync workspace')
      }

      // Refresh workspaces after syncing
      await fetchWorkspaces()
    } catch (err) {
      console.error('Error syncing workspace:', err)
      throw err
    }
  }

  useEffect(() => {
    fetchWorkspaces()
  }, [user])

  return {
    workspaces,
    loading,
    error,
    refetch: fetchWorkspaces,
    connectWorkspace,
    syncWorkspace
  }
}

function getWorkspaceStatus(lastSyncAt?: string): 'active' | 'syncing' | 'error' | 'pending' {
  if (!lastSyncAt) return 'pending'
  
  const lastSync = new Date(lastSyncAt)
  const now = new Date()
  const daysSinceSync = (now.getTime() - lastSync.getTime()) / (1000 * 60 * 60 * 24)
  
  // If synced within last day, consider active
  if (daysSinceSync < 1) return 'active'
  
  // If synced within last week, still active but might need refresh
  if (daysSinceSync < 7) return 'active'
  
  // If older than a week, might have issues
  return 'error'
}