#!/usr/bin/env python3
"""
Script to check active databases from Supabase
Queries the database_schemas table to show available Notion databases
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client
import json

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DatabaseChecker:
    def __init__(self):
        self.client: Client = None
        
    def init_connection(self):
        """Initialize Supabase connection using environment variables"""
        # Load environment variables from .env file
        load_dotenv()
        
        supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            print("❌ Error: Supabase credentials not found in environment variables")
            print("Please ensure your .env file contains:")
            print("  - NEXT_PUBLIC_SUPABASE_URL")
            print("  - NEXT_PUBLIC_SUPABASE_ANON_KEY")
            sys.exit(1)
            
        try:
            self.client = create_client(supabase_url, supabase_key)
            print("✅ Successfully connected to Supabase")
            print(f"   URL: {supabase_url}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Supabase: {str(e)}")
            sys.exit(1)
    
    def get_workspaces(self) -> List[Dict[str, Any]]:
        """Get all workspaces from Supabase"""
        try:
            response = self.client.table('workspaces').select(
                'id, name, notion_access_token, created_at, updated_at, last_sync_at, is_active'
            ).execute()
            return response.data
        except Exception as e:
            print(f"❌ Error fetching workspaces: {str(e)}")
            return []
    
    def get_database_schemas(self, workspace_id: str = None) -> List[Dict[str, Any]]:
        """Get all database schemas from Supabase"""
        try:
            query = self.client.table('database_schemas').select(
                'database_id, workspace_id, database_name, notion_schema, field_definitions, '
                'queryable_fields, created_at, updated_at, last_analyzed_at'
            )
            
            if workspace_id:
                query = query.eq('workspace_id', workspace_id)
                
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"❌ Error fetching database schemas: {str(e)}")
            return []
    
    def get_document_counts(self) -> Dict[str, int]:
        """Get document counts per database"""
        try:
            response = self.client.table('documents').select(
                'database_id'
            ).execute()
            
            # Count documents per database
            counts = {}
            for doc in response.data:
                db_id = doc['database_id']
                counts[db_id] = counts.get(db_id, 0) + 1
                
            return counts
        except Exception as e:
            print(f"❌ Error fetching document counts: {str(e)}")
            return {}
    
    def format_datetime(self, dt_str: str) -> str:
        """Format datetime string for display"""
        if not dt_str:
            return "Never"
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except:
            return dt_str
    
    def display_workspaces(self, workspaces: List[Dict[str, Any]]):
        """Display workspace information"""
        print("\n" + "="*80)
        print("WORKSPACES")
        print("="*80)
        
        if not workspaces:
            print("❌ No workspaces found")
            return
            
        for i, workspace in enumerate(workspaces, 1):
            status = "🟢 Active" if workspace.get('is_active', False) else "🔴 Inactive"
            print(f"\n{i}. {workspace['name']} {status}")
            print(f"   ID: {workspace['id']}")
            print(f"   Created: {self.format_datetime(workspace.get('created_at'))}")
            print(f"   Updated: {self.format_datetime(workspace.get('updated_at'))}")
            print(f"   Last Sync: {self.format_datetime(workspace.get('last_sync_at'))}")
            print(f"   Has Token: {'✅' if workspace.get('notion_access_token') else '❌'}")
    
    def display_databases(self, databases: List[Dict[str, Any]], document_counts: Dict[str, int]):
        """Display database schema information"""
        print("\n" + "="*80)
        print("DATABASE SCHEMAS")
        print("="*80)
        
        if not databases:
            print("❌ No database schemas found")
            return
            
        for i, db in enumerate(databases, 1):
            doc_count = document_counts.get(db['database_id'], 0)
            print(f"\n{i}. {db['database_name']}")
            print(f"   Database ID: {db['database_id']}")
            print(f"   Workspace ID: {db['workspace_id']}")
            print(f"   Documents: {doc_count}")
            print(f"   Created: {self.format_datetime(db.get('created_at'))}")
            print(f"   Updated: {self.format_datetime(db.get('updated_at'))}")
            print(f"   Last Analyzed: {self.format_datetime(db.get('last_analyzed_at'))}")
            
            # Display field information
            if db.get('field_definitions'):
                try:
                    fields = db['field_definitions']
                    if isinstance(fields, str):
                        fields = json.loads(fields)
                    if isinstance(fields, dict) and len(fields) > 0:
                        print(f"   Fields: {', '.join(fields.keys())}")
                except:
                    print("   Fields: Unable to parse")
            
            # Display queryable fields
            if db.get('queryable_fields'):
                try:
                    q_fields = db['queryable_fields']
                    if isinstance(q_fields, str):
                        q_fields = json.loads(q_fields)
                    if isinstance(q_fields, (list, dict)) and len(q_fields) > 0:
                        if isinstance(q_fields, list):
                            print(f"   Queryable Fields: {', '.join(q_fields)}")
                        else:
                            print(f"   Queryable Fields: {', '.join(q_fields.keys())}")
                except:
                    print("   Queryable Fields: Unable to parse")
    
    def get_summary_stats(self, workspaces: List[Dict[str, Any]], databases: List[Dict[str, Any]], document_counts: Dict[str, int]):
        """Display summary statistics"""
        print("\n" + "="*80)
        print("SUMMARY STATISTICS")
        print("="*80)
        
        active_workspaces = len([w for w in workspaces if w.get('is_active', False)])
        total_databases = len(databases)
        total_documents = sum(document_counts.values())
        
        print(f"Total Workspaces: {len(workspaces)}")
        print(f"Active Workspaces: {active_workspaces}")
        print(f"Total Database Schemas: {total_databases}")
        print(f"Total Documents: {total_documents}")
        
        if databases:
            # Find most recent sync
            recent_updates = [db.get('updated_at') for db in databases if db.get('updated_at')]
            if recent_updates:
                most_recent = max(recent_updates)
                print(f"Most Recent Database Update: {self.format_datetime(most_recent)}")
        
        print("\nDatabase Document Distribution:")
        for db in databases:
            db_id = db['database_id']
            count = document_counts.get(db_id, 0)
            print(f"  - {db['database_name']}: {count} documents")
    
    def run_check(self):
        """Main method to run the database check"""
        print("🔍 Checking Active Databases from Supabase...")
        print("-" * 50)
        
        # Initialize connection
        self.init_connection()
        
        # Fetch data
        print("\n📊 Fetching data...")
        workspaces = self.get_workspaces()
        databases = self.get_database_schemas()
        document_counts = self.get_document_counts()
        
        # Display results
        self.display_workspaces(workspaces)
        self.display_databases(databases, document_counts)
        self.get_summary_stats(workspaces, databases, document_counts)
        
        print("\n" + "="*80)
        print("✅ Database check completed!")

def main():
    """Main entry point"""
    checker = DatabaseChecker()
    try:
        checker.run_check()
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 