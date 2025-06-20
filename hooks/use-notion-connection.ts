import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { useAuth } from './use-auth'
import { logger } from '@/lib/logger'
import { useFrontendErrorLogger } from '@/lib/frontend-error-logger'

export interface NotionConnection {
  id: string
  name: string
  icon?: string
  database_id: string
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
  const errorLogger = useFrontendErrorLogger('use-notion-connection')
  
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

      // Fetch the primary notion database
      const { data: databaseData, error: databaseError } = await supabase
        .from('notion_databases')
        .select(`
          database_id,
          database_name,
          notion_access_token,
          is_active,
          last_sync_at
        `)
        .eq('is_active', true)
        .order('created_at', { ascending: false })
        .limit(1)
        .single()

      let documentCount = 0
      if (databaseData) {
        // Get document count separately
        const { count } = await supabase
          .from('documents')
          .select('*', { count: 'exact', head: true })
          .eq('notion_database_id', databaseData.database_id)
        
        documentCount = count || 0
      }

      if (databaseError) {
        // No database found is not an error, just means not connected
        if (databaseError.code === 'PGRST116') {
          setConnection(null)
          return
        }
        throw databaseError
      }

      if (databaseData) {
        const connectionData: NotionConnection = {
          id: databaseData.database_id,
          name: databaseData.database_name,
          database_id: databaseData.database_id,
          is_active: databaseData.is_active,
          last_sync_at: databaseData.last_sync_at,
          document_count: documentCount,
          status: getConnectionStatus(databaseData.last_sync_at)
        }
        setConnection(connectionData)
      } else {
        setConnection(null)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch Notion connection'
      logger.error('Error fetching Notion connection', 'use-notion-connection', {
        error_message: errorMessage,
        user_id: user?.id
      }, err instanceof Error ? err : undefined)
      errorLogger.logHookError('Failed to fetch Notion connection', err instanceof Error ? err : undefined, {
        user_id: user?.id,
        error_message: errorMessage
      })
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const connectNotion = async (notionToken: string) => {
    if (!user) throw new Error('User not authenticated')
    if (!supabase) throw new Error('Supabase not configured')

    try {
      // Call backend API to connect Notion workspace (single-user app)
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/notion/connect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          notion_token: notionToken
        })
      })

      if (!response.ok) {
        throw new Error('Failed to connect Notion')
      }

      // Refresh connection after connecting
      await fetchConnection()
    } catch (err) {
      logger.error('Error connecting Notion', 'use-notion-connection', {
        user_id: user?.id
      }, err instanceof Error ? err : undefined)
      errorLogger.logApiError('Failed to connect Notion', err instanceof Error ? err : undefined, {
        user_id: user?.id
      })
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
          database_id: connection.database_id
        })
      })

      if (!response.ok) {
        throw new Error('Failed to sync Notion')
      }

      // Refresh connection after syncing
      await fetchConnection()
    } catch (err) {
      logger.error('Error syncing Notion', 'use-notion-connection', {
        connection_id: connection.id,
        database_id: connection.database_id
      }, err instanceof Error ? err : undefined)
      errorLogger.logApiError('Failed to sync Notion', err instanceof Error ? err : undefined, {
        connection_id: connection.id,
        database_id: connection.database_id
      })
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