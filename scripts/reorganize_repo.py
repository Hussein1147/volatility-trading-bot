#!/usr/bin/env python3
"""
Safely reorganize repository structure
Creates backups before moving files
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# Define the reorganization mapping
MOVES = {
    # Alpaca tests
    'scripts/data_verification/test_alpaca_auth.py': 'tests/integration/alpaca/test_alpaca_auth.py',
    'scripts/data_verification/test_alpaca_options_data.py': 'tests/integration/alpaca/test_alpaca_options_data.py',
    'scripts/data_verification/test_alpaca_puts.py': 'tests/integration/alpaca/test_alpaca_puts.py',
    'scripts/tests/test_alpaca_data.py': 'tests/integration/alpaca/test_alpaca_data.py',
    'scripts/tests/test_alpaca_options.py': 'tests/integration/alpaca/test_alpaca_options.py',
    'scripts/verify_alpaca_data.py': 'tests/integration/alpaca/verify_alpaca_data.py',
    'scripts/check_alpaca_iv_data.py': 'tests/integration/alpaca/check_alpaca_iv_data.py',
    'scripts/data_verification/check_alpaca_data_availability.py': 'tests/integration/alpaca/check_alpaca_data_availability.py',
    
    # Backtest tests
    'scripts/data_verification/test_backtest_flow.py': 'tests/integration/backtest/test_backtest_flow.py',
    'scripts/data_verification/test_backtest_with_activity.py': 'tests/integration/backtest/test_backtest_with_activity.py',
    'scripts/tests/test_backtest_components.py': 'tests/integration/backtest/test_backtest_components.py',
    'scripts/tests/test_backtest_ui.py': 'tests/integration/backtest/test_backtest_ui.py',
    'scripts/tests/test_backtest_with_progress.py': 'tests/integration/backtest/test_backtest_with_progress.py',
    'scripts/tests/verify_backtest_fixes.py': 'tests/integration/backtest/verify_backtest_fixes.py',
    'scripts/data_verification/verify_backtest_data.py': 'tests/integration/backtest/verify_backtest_data.py',
    'scripts/debug_backtest_flow.py': 'tests/integration/backtest/debug_backtest_flow.py',
    'scripts/test_real_iv_backtest.py': 'tests/integration/backtest/test_real_iv_backtest.py',
    
    # Options data tests
    'scripts/data_verification/test_options_data_fetch.py': 'tests/integration/options/test_options_data_fetch.py',
    'scripts/data_verification/test_options_pricing.py': 'tests/integration/options/test_options_pricing.py',
    'scripts/data_verification/test_simple_options.py': 'tests/integration/options/test_simple_options.py',
    
    # API tests
    'scripts/test_tastytrade_data.py': 'tests/integration/api/test_tastytrade_data.py',
    'scripts/test_polygon_tastytrade_options.py': 'tests/integration/api/test_polygon_tastytrade_options.py',
    'scripts/test_free_options_apis.py': 'tests/integration/api/test_free_options_apis.py',
    
    # Data verification
    'scripts/verify_iv_data.py': 'tests/integration/data/verify_iv_data.py',
    'scripts/data_verification/test_real_data_backtest.py': 'tests/integration/data/test_real_data_backtest.py',
    
    # Activity/logging tests
    'scripts/data_verification/test_activity_logging.py': 'tests/integration/logging/test_activity_logging.py',
    'scripts/data_verification/dump_activity_log.py': 'tests/integration/logging/dump_activity_log.py',
    
    # Utils
    'scripts/debug_trades.py': 'tests/utils/debug_trades.py',
    'scripts/data_availability_summary.py': 'tests/utils/data_availability_summary.py',
    
    # Production scripts
    'run_backtest.py': 'scripts/production/run_backtest.py',
    'run_dashboard.py': 'scripts/production/run_dashboard.py',
    'scripts/verify_system.py': 'scripts/production/verify_system.py',
    
    # Examples
    'scripts/backtest_config_example.py': 'scripts/examples/backtest_config_example.py',
}

def create_backup():
    """Create a backup of files to be moved"""
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating backup in {backup_dir}/")
    
    for src in MOVES.keys():
        if os.path.exists(src):
            backup_path = os.path.join(backup_dir, src)
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.copy2(src, backup_path)
            print(f"  Backed up: {src}")
    
    return backup_dir

def create_directories():
    """Create new directory structure"""
    dirs = [
        'tests/unit',
        'tests/integration/alpaca',
        'tests/integration/backtest',
        'tests/integration/options',
        'tests/integration/api',
        'tests/integration/data',
        'tests/integration/logging',
        'tests/utils',
        'scripts/production',
        'scripts/examples',
    ]
    
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"Created directory: {dir_path}")
        
        # Add __init__.py for Python packages
        if dir_path.startswith('tests/'):
            init_file = os.path.join(dir_path, '__init__.py')
            if not os.path.exists(init_file):
                with open(init_file, 'w') as f:
                    f.write('# Test package\n')

def move_files():
    """Move files to new locations"""
    moved = 0
    errors = []
    
    for src, dst in MOVES.items():
        if os.path.exists(src):
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(src, dst)
                print(f"Moved: {src} -> {dst}")
                moved += 1
            except Exception as e:
                errors.append(f"Error moving {src}: {e}")
        else:
            print(f"Skipped (not found): {src}")
    
    return moved, errors

def cleanup_empty_dirs():
    """Remove empty directories"""
    dirs_to_check = [
        'scripts/data_verification',
        'scripts/tests',
    ]
    
    for dir_path in dirs_to_check:
        if os.path.exists(dir_path) and not os.listdir(dir_path):
            os.rmdir(dir_path)
            print(f"Removed empty directory: {dir_path}")

def main():
    """Main reorganization process"""
    print("=" * 80)
    print("REPOSITORY REORGANIZATION")
    print("=" * 80)
    
    # Check if we're in the right directory
    if not os.path.exists('src') or not os.path.exists('scripts'):
        print("ERROR: Must run from project root directory")
        return
    
    print("\n1. Creating backup...")
    backup_dir = create_backup()
    
    print("\n2. Creating new directory structure...")
    create_directories()
    
    print("\n3. Moving files...")
    moved, errors = move_files()
    
    print("\n4. Cleaning up empty directories...")
    cleanup_empty_dirs()
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: Moved {moved} files")
    if errors:
        print(f"ERRORS: {len(errors)}")
        for error in errors:
            print(f"  - {error}")
    print(f"Backup saved in: {backup_dir}/")
    print("=" * 80)
    
    # Create a summary file
    with open('REORGANIZATION_SUMMARY.txt', 'w') as f:
        f.write(f"Repository Reorganization Summary\n")
        f.write(f"Date: {datetime.now()}\n")
        f.write(f"Files moved: {moved}\n")
        f.write(f"Errors: {len(errors)}\n")
        f.write(f"Backup location: {backup_dir}/\n\n")
        f.write("File movements:\n")
        for src, dst in MOVES.items():
            if os.path.exists(dst):
                f.write(f"  {src} -> {dst}\n")

if __name__ == "__main__":
    main()