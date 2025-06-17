import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { useAuth } from './use-auth'

export interface NotionConnection {
  id: string
  name: string
  icon?: string
  notion_workspace_id: string
  is_active: boolean
  last_sync_at?: string
  document_count?: number
  status: 'active' | 'syncing' | 'error' | 'pending'
}

export function useNotionConnection() {
  const [connection, setConnection] = useState<NotionConnection | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { user } = useAuth()
  
  // Helper to check if user has Notion connected
  const isConnected = !!connection

  const fetchConnection = async () => {
    if (!user) {
      setConnection(null)
      setLoading(false)
      return
    }

    // If Supabase is not configured, return no connection
    if (!supabase) {
      setConnection(null)
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      // Fetch the user's primary workspace (first active one) with document count
      const { data: workspaceData, error: workspaceError } = await supabase
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
        .limit(1)
        .single()

      if (workspaceError) {
        // No workspace found is not an error, just means not connected
        if (workspaceError.code === 'PGRST116') {
          setConnection(null)
          return
        }
        throw workspaceError
      }

      if (workspaceData) {
        const connectionData: NotionConnection = {
          id: workspaceData.id,
          name: workspaceData.name,
          icon: workspaceData.icon,
          notion_workspace_id: workspaceData.notion_workspace_id,
          is_active: workspaceData.is_active,
          last_sync_at: workspaceData.last_sync_at,
          document_count: workspaceData.documents?.[0]?.count || 0,
          status: getConnectionStatus(workspaceData.last_sync_at)
        }
        setConnection(connectionData)
      } else {
        setConnection(null)
      }
    } catch (err) {
      console.error('Error fetching Notion connection:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch Notion connection')
    } finally {
      setLoading(false)
    }
  }

  const connectNotion = async (notionToken: string) => {
    if (!user) throw new Error('User not authenticated')
    if (!supabase) throw new Error('Supabase not configured')

    try {
      // Call backend API to connect Notion workspace
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
        throw new Error('Failed to connect Notion')
      }

      // Refresh connection after connecting
      await fetchConnection()
    } catch (err) {
      console.error('Error connecting Notion:', err)
      throw err
    }
  }

  const syncNotion = async () => {
    if (!supabase) throw new Error('Supabase not configured')
    if (!connection) throw new Error('No Notion connection found')
    
    try {
      // Call backend API to sync the user's Notion workspace
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/notion/sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          workspace_id: connection.id
        })
      })

      if (!response.ok) {
        throw new Error('Failed to sync Notion')
      }

      // Refresh connection after syncing
      await fetchConnection()
    } catch (err) {
      console.error('Error syncing Notion:', err)
      throw err
    }
  }

  useEffect(() => {
    fetchConnection()
  }, [user])

  return {
    connection,
    isConnected,
    loading,
    error,
    refetch: fetchConnection,
    connectNotion,
    syncNotion
  }
}

function getConnectionStatus(lastSyncAt?: string): 'active' | 'syncing' | 'error' | 'pending' {
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