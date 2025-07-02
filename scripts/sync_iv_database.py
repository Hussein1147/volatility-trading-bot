#!/usr/bin/env python3
"""
Sync IV database from GitHub to local
Handles merge conflicts by always taking the cloud version
"""
import subprocess
import shutil
import os
from datetime import datetime

def sync_iv_database():
    """Sync the IV database from GitHub"""
    print("Syncing IV database from GitHub...")
    
    # Backup local database
    if os.path.exists('historical_iv.db'):
        backup_name = f'historical_iv_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        shutil.copy2('historical_iv.db', backup_name)
        print(f"Backed up local database to {backup_name}")
    
    # Stash any local changes
    subprocess.run(['git', 'stash', 'push', '-m', 'Stashing before IV sync', 'historical_iv.db'], 
                   capture_output=True)
    
    # Pull latest from main, accepting cloud version
    result = subprocess.run(['git', 'pull', '--strategy-option=theirs', 'origin', 'main'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Successfully synced IV database from GitHub")
        print("  Latest IV data is now available locally")
    else:
        print("✗ Error syncing database:")
        print(result.stderr)
        
        # Try to recover
        print("\nAttempting recovery...")
        subprocess.run(['git', 'reset', '--hard', 'origin/main'])
        print("Reset to cloud version")
    
    # Show recent updates
    result = subprocess.run(['git', 'log', '--oneline', '-5', '--grep=Update IV data'], 
                          capture_output=True, text=True)
    print("\nRecent IV updates:")
    print(result.stdout)

if __name__ == "__main__":
    sync_iv_database()