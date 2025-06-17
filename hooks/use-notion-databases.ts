import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { useAuth } from './use-auth'
import { useNotionConnection } from './use-notion-connection'

export interface NotionDatabase {
  database_id: string
  database_name: string
  field_definitions: any
  queryable_fields: any
  created_at: string
  updated_at: string
  last_analyzed_at?: string
  document_count?: number
}

export function useNotionDatabases() {
  const [databases, setDatabases] = useState<NotionDatabase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { user } = useAuth()
  const { connection, isConnected } = useNotionConnection()

  const fetchDatabases = async () => {
    if (!user || !isConnected || !connection) {
      setDatabases([])
      setLoading(false)
      return
    }

    // If Supabase is not configured, return empty databases
    if (!supabase) {
      setDatabases([])
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      // Fetch databases for the connected workspace with document counts
      const { data: databaseData, error: databaseError } = await supabase
        .from('database_schemas')
        .select(`
          database_id,
          database_name,
          field_definitions,
          queryable_fields,
          created_at,
          updated_at,
          last_analyzed_at
        `)
        .eq('workspace_id', connection.id)

      if (databaseError) throw databaseError

      // Get document counts for each database
      const databasesWithCounts = await Promise.all(
        (databaseData || []).map(async (db) => {
          const { count } = await supabase
            .from('documents')
            .select('*', { count: 'exact', head: true })
            .eq('database_id', db.database_id)

          return {
            database_id: db.database_id,
            database_name: db.database_name,
            field_definitions: db.field_definitions,
            queryable_fields: db.queryable_fields,
            created_at: db.created_at,
            updated_at: db.updated_at,
            last_analyzed_at: db.last_analyzed_at,
            document_count: count || 0
          }
        })
      )

      setDatabases(databasesWithCounts)
    } catch (err) {
      console.error('Error fetching Notion databases:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch databases')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDatabases()
  }, [user, connection, isConnected])

  return {
    databases,
    loading,
    error,
    refetch: fetchDatabases
  }
}