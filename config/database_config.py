"""
Database configuration for local vs production environments
"""
import os

def get_iv_database_path():
    """Get the appropriate database path based on environment"""
    if os.getenv('GITHUB_ACTIONS'):
        # Use the tracked database in GitHub Actions
        return 'historical_iv.db'
    else:
        # Use a local untracked database for development
        return 'historical_iv_local.db'

# Example usage:
# from config.database_config import get_iv_database_path
# db_path = get_iv_database_path()