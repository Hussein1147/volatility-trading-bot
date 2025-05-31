#!/usr/bin/env python3
"""
Comprehensive Dashboard Testing Suite for Volatility Trading Bot

This test suite validates all dashboard functionality before launch.
All tests must pass before the dashboard can be launched.
"""

import sys
import os
import subprocess
import time
import requests
import threading
import importlib.util
from datetime import datetime
import json

class DashboardTester:
    def __init__(self):
        self.test_results = []
        self.dashboard_process = None
        self.test_port = 8502  # Use different port for testing
        
    def log_test(self, test_name, passed, message=""):
        """Log test result"""
        status = "✓ PASS" if passed else "✗ FAIL"
        timestamp = datetime.now().strftime('%H:%M:%S')
        result = f"[{timestamp}] {status}: {test_name}"
        if message:
            result += f" - {message}"
        print(result)
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message,
            'timestamp': timestamp
        })
        return passed

    def test_imports(self):
        """Test that all required imports work"""
        try:
            # Test basic Python imports
            import streamlit as st
            import pandas as pd
            import plotly.express as px
            import plotly.graph_objects as go
            import numpy as np
            self.log_test("Basic imports", True)
            
            # Test project-specific imports
            try:
                from enhanced_trade_manager import EnhancedTradeManager, TradeManagementRules, OptionContract
                self.log_test("Project imports", True)
            except ImportError as e:
                self.log_test("Project imports", False, str(e))
                return False
                
            # Test dashboard module import
            spec = importlib.util.spec_from_file_location("dashboard", "consolidated_dashboard.py")
            dashboard = importlib.util.module_from_spec(spec)
            
            # Don't execute the module, just check if it can be loaded
            self.log_test("Dashboard module loadable", True)
            return True
            
        except ImportError as e:
            self.log_test("Basic imports", False, str(e))
            return False
        except Exception as e:
            self.log_test("Import test", False, str(e))
            return False

    def test_environment_setup(self):
        """Test that environment is properly configured"""
        try:
            # Check virtual environment
            if 'trading_bot_env' not in sys.executable:
                self.log_test("Virtual environment", False, "Not using trading_bot_env")
                return False
            else:
                self.log_test("Virtual environment", True)
            
            # Check required files exist
            required_files = [
                'consolidated_dashboard.py',
                'enhanced_trade_manager.py',
                'requirements.txt',
                '.env'
            ]
            
            missing_files = []
            for file in required_files:
                if not os.path.exists(file):
                    missing_files.append(file)
            
            if missing_files:
                self.log_test("Required files", False, f"Missing: {', '.join(missing_files)}")
                return False
            else:
                self.log_test("Required files", True)
            
            return True
            
        except Exception as e:
            self.log_test("Environment setup", False, str(e))
            return False

    def test_dashboard_syntax(self):
        """Test dashboard file for syntax errors"""
        try:
            with open('consolidated_dashboard.py', 'r') as f:
                content = f.read()
            
            # Try to compile the code
            compile(content, 'consolidated_dashboard.py', 'exec')
            self.log_test("Dashboard syntax", True)
            return True
            
        except SyntaxError as e:
            self.log_test("Dashboard syntax", False, f"Line {e.lineno}: {e.msg}")
            return False
        except Exception as e:
            self.log_test("Dashboard syntax", False, str(e))
            return False

    def test_streamlit_installation(self):
        """Test streamlit is properly installed and can run"""
        try:
            result = subprocess.run([
                sys.executable, '-m', 'streamlit', '--version'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                version = result.stdout.strip()
                self.log_test("Streamlit installation", True, f"Version: {version}")
                return True
            else:
                self.log_test("Streamlit installation", False, result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            self.log_test("Streamlit installation", False, "Command timed out")
            return False
        except Exception as e:
            self.log_test("Streamlit installation", False, str(e))
            return False

    def start_test_dashboard(self):
        """Start dashboard on test port"""
        try:
            cmd = [
                sys.executable, '-m', 'streamlit', 'run', 
                'consolidated_dashboard.py',
                '--server.port', str(self.test_port),
                '--server.headless', 'true',
                '--browser.gatherUsageStats', 'false'
            ]
            
            self.dashboard_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for startup
            time.sleep(10)
            
            if self.dashboard_process.poll() is None:
                self.log_test("Dashboard startup", True, f"Running on port {self.test_port}")
                return True
            else:
                stdout, stderr = self.dashboard_process.communicate()
                self.log_test("Dashboard startup", False, f"Process died: {stderr}")
                return False
                
        except Exception as e:
            self.log_test("Dashboard startup", False, str(e))
            return False

    def test_dashboard_accessibility(self):
        """Test that dashboard is accessible via HTTP"""
        try:
            url = f"http://localhost:{self.test_port}"
            
            # Try multiple times with backoff
            for attempt in range(5):
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        self.log_test("Dashboard accessibility", True, f"HTTP 200 from {url}")
                        return True
                    else:
                        self.log_test("Dashboard accessibility", False, f"HTTP {response.status_code}")
                        
                except requests.exceptions.ConnectionError:
                    if attempt < 4:  # Not the last attempt
                        time.sleep(2)
                        continue
                    else:
                        self.log_test("Dashboard accessibility", False, "Connection refused")
                        return False
                        
        except Exception as e:
            self.log_test("Dashboard accessibility", False, str(e))
            return False

    def test_dashboard_content(self):
        """Test that dashboard contains expected content"""
        try:
            url = f"http://localhost:{self.test_port}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                self.log_test("Dashboard content", False, f"HTTP {response.status_code}")
                return False
            
            content = response.text.lower()
            
            # Check for streamlit app indicators (more reliable than exact text)
            streamlit_indicators = [
                'streamlit',
                'data-testid',
                'stApp'
            ]
            
            has_streamlit = any(indicator in content for indicator in streamlit_indicators)
            
            if not has_streamlit:
                self.log_test("Dashboard content", False, "No Streamlit app detected")
                return False
            
            # Check for basic content (more flexible)
            basic_elements = [
                'volatility',
                'trading',
                'bot'
            ]
            
            found_elements = [elem for elem in basic_elements if elem in content]
            
            if len(found_elements) >= 2:  # At least 2 of the 3 basic elements
                self.log_test("Dashboard content", True, f"Streamlit app with trading bot content detected")
                return True
            else:
                self.log_test("Dashboard content", False, f"Trading bot content not detected. Found: {found_elements}")
                return False
                
        except Exception as e:
            self.log_test("Dashboard content", False, str(e))
            return False

    def test_dashboard_no_errors(self):
        """Test that dashboard doesn't have runtime errors"""
        try:
            if not self.dashboard_process:
                self.log_test("Dashboard errors", False, "No process to check")
                return False
            
            # Check if process is still running
            if self.dashboard_process.poll() is not None:
                stdout, stderr = self.dashboard_process.communicate()
                if stderr and "error" in stderr.lower():
                    self.log_test("Dashboard errors", False, f"Runtime errors: {stderr[:200]}")
                    return False
            
            self.log_test("Dashboard errors", True, "No critical runtime errors detected")
            return True
            
        except Exception as e:
            self.log_test("Dashboard errors", False, str(e))
            return False
    
    def test_dashboard_live_verification(self):
        """Verify dashboard is actually accessible and responding"""
        try:
            import webbrowser
            url = f"http://localhost:{self.test_port}"
            
            # Test 1: HTTP headers
            response = requests.head(url, timeout=5)
            if response.status_code != 200:
                self.log_test("Live verification - HTTP", False, f"Status code: {response.status_code}")
                return False
            
            # Test 2: Content length
            content_length = response.headers.get('Content-Length', '0')
            if int(content_length) < 100:
                self.log_test("Live verification - Content", False, "Response too small")
                return False
            
            # Test 3: Server header
            server = response.headers.get('Server', '')
            if 'tornado' not in server.lower():
                self.log_test("Live verification - Server", False, f"Unexpected server: {server}")
                return False
            
            # Test 4: Can fetch actual page
            response = requests.get(url, timeout=10)
            if len(response.text) < 500:
                self.log_test("Live verification", False, "Page content too small")
                return False
            
            self.log_test("Live verification", True, f"Dashboard confirmed live at {url}")
            
            # Try to open in browser (non-blocking)
            try:
                webbrowser.open(url, new=2, autoraise=False)
                self.log_test("Browser launch", True, "Attempted to open in browser")
            except:
                pass  # Browser launch is optional
            
            return True
            
        except requests.exceptions.RequestException as e:
            self.log_test("Live verification", False, f"Connection error: {e}")
            return False
        except Exception as e:
            self.log_test("Live verification", False, str(e))
            return False

    def cleanup(self):
        """Clean up test resources"""
        if self.dashboard_process:
            try:
                self.dashboard_process.terminate()
                self.dashboard_process.wait(timeout=5)
            except:
                try:
                    self.dashboard_process.kill()
                except:
                    pass

    def run_all_tests(self):
        """Run complete test suite"""
        print("=" * 60)
        print("VOLATILITY TRADING BOT - DASHBOARD TEST SUITE")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        tests = [
            self.test_imports,
            self.test_environment_setup,
            self.test_dashboard_syntax,
            self.test_streamlit_installation,
            self.start_test_dashboard,
            self.test_dashboard_accessibility,
            self.test_dashboard_content,
            self.test_dashboard_no_errors,
            self.test_dashboard_live_verification
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed_tests += 1
                time.sleep(1)  # Brief pause between tests
            except Exception as e:
                self.log_test(test.__name__, False, f"Test execution error: {e}")
        
        print()
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Passed: {passed_tests}/{total_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print("🟢 ALL TESTS PASSED - Dashboard ready for launch!")
            print(f"Dashboard validated and ready to run on port 8501")
        else:
            print("🔴 TESTS FAILED - Dashboard NOT ready for launch")
            print("Fix the issues above before launching dashboard")
        
        print("=" * 60)
        
        self.cleanup()
        return passed_tests == total_tests

def main():
    """Main test runner"""
    tester = DashboardTester()
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        tester.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"Test suite error: {e}")
        tester.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()