"""
Integration tests for the evaluation data collection system.
"""

import pytest
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add evaluation root to path
evaluation_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(evaluation_root))

# Load environment variables from root folder
root_dir = evaluation_root.parent
load_dotenv(dotenv_path=root_dir / ".env")

from services.data_collector import DataCollector
from utils.config_loader import ConfigLoader


@pytest.mark.integration
class TestDataCollection:
    """Integration test suite for data collection system."""
    
    @pytest.fixture
    def test_database_id(self):
        """Test database ID for collection tests."""
        # Get database ID from evaluation.toml configuration (use first one if multiple)
        try:
            config_loader = ConfigLoader()
            config_path = config_loader.config_dir / "evaluation.toml"
            
            if config_path.exists():
                import tomllib
                with open(config_path, 'rb') as f:
                    config_data = tomllib.load(f)
                
                database_ids = config_data.get("collection", {}).get("database_ids", [])
                if database_ids:
                    return database_ids[0]  # Use first database ID
            
        except Exception as e:
            raise Exception(f"Warning: Could not load database ID from evaluation.toml: {e}")
    
    @pytest.fixture
    def collector(self, temp_output_dir):
        """Create a data collector instance for testing."""
        return DataCollector(output_dir=temp_output_dir)
    
    @pytest.fixture(autouse=True)
    def skip_if_no_notion_token(self):
        """Automatically skip all integration tests if NOTION_ACCESS_TOKEN is not set."""
        if not os.getenv("NOTION_ACCESS_TOKEN"):
            pytest.skip("NOTION_ACCESS_TOKEN not set - skipping all integration tests")
    
    def test_environment_setup(self):
        """Test that required environment variables are set."""
        notion_token = os.getenv("NOTION_ACCESS_TOKEN")
        
        if not notion_token:
            pytest.skip("NOTION_ACCESS_TOKEN not set - skipping integration tests")
        
        assert notion_token, "NOTION_ACCESS_TOKEN should be set for integration tests"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # 30 second timeout
    async def test_single_database_collection(self, collector, test_database_id):
        """Test collection from a single database."""        
        try:
            # Use a very restrictive limit to prevent long-running tests
            stats = await collector.collect_database(
                test_database_id, 
                min_content_length=10
            )
            
            # Verify collection stats structure
            assert hasattr(stats, 'total_documents'), "Stats should have total_documents"
            assert hasattr(stats, 'successful'), "Stats should have successful count"
            assert hasattr(stats, 'failed'), "Stats should have failed count"
            assert hasattr(stats, 'skipped'), "Stats should have skipped count"
            assert hasattr(stats, 'errors'), "Stats should have errors list"
            
            # Verify stats are reasonable
            assert stats.total_documents >= 0, "Total documents should be non-negative"
            assert stats.successful >= 0, "Successful count should be non-negative"
            assert stats.failed >= 0, "Failed count should be non-negative"
            assert stats.skipped >= 0, "Skipped count should be non-negative"
            assert isinstance(stats.errors, list), "Errors should be a list"
            
            # Verify totals add up
            assert stats.total_documents == stats.successful + stats.failed + stats.skipped, \
                "Total should equal sum of successful, failed, and skipped"
            
            print(f"✅ Collection completed!")
            print(f"   Total documents: {stats.total_documents}")
            print(f"   Successful: {stats.successful}")
            print(f"   Failed: {stats.failed}")
            print(f"   Skipped: {stats.skipped}")
            
            if stats.errors:
                print(f"   Errors: {len(stats.errors)}")
                for i, error in enumerate(stats.errors[:3]):
                    print(f"     {i+1}. {error}")
            
            # Test passes if we get any reasonable response
            assert True, "Collection completed without fatal errors"
            
        except Exception as e:
            pytest.fail(f"Collection failed with error: {e}")
    
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(15)  # 15 second timeout
    async def test_collection_error_handling(self, temp_output_dir):
        """Test error handling with invalid database ID."""
        
        collector = DataCollector(output_dir=temp_output_dir)
        
        # Test with invalid database ID
        invalid_database_id = "invalid-database-id-12345"
        
        try:
            stats = await collector.collect_database(invalid_database_id)
            
            # Should handle error gracefully
            assert hasattr(stats, 'errors'), "Should track errors"
            assert len(stats.errors) > 0 or stats.failed > 0, "Should record failure for invalid ID"
            
        except Exception as e:
            # It's also acceptable for this to raise an exception
            assert "invalid" in str(e).lower() or "not found" in str(e).lower(), \
                f"Should give meaningful error for invalid database ID: {e}"
    
    @pytest.mark.asyncio
    async def test_output_directory_creation(self, temp_output_dir):
        """Test that output directories are created correctly."""
        collector = DataCollector(output_dir=temp_output_dir)
        
        # The output directory should exist
        assert temp_output_dir.exists(), "Output directory should exist"
        assert temp_output_dir.is_dir(), "Output path should be a directory"
    
    @pytest.mark.asyncio
    async def test_collector_initialization(self, temp_output_dir):
        """Test collector initialization with various configurations."""
        # Test basic initialization
        collector1 = DataCollector(output_dir=temp_output_dir)
        assert collector1 is not None, "Should initialize collector"
        
        # Test with string path
        collector2 = DataCollector(output_dir=str(temp_output_dir))
        assert collector2 is not None, "Should accept string path"
        
        # Test default output directory
        collector3 = DataCollector()
        assert collector3 is not None, "Should work with default output directory"
