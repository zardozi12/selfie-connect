#!/usr/bin/env python3
"""
Comprehensive PhotoVault Error Checker
Starts the backend and checks for all errors
"""

import asyncio
import subprocess
import sys
import time
import requests
import json
import os
from pathlib import Path

class PhotoVaultErrorChecker:
    def __init__(self):
        self.backend_process = None
        self.errors_found = []
        self.warnings_found = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def check_environment(self):
        """Check if environment is properly set up"""
        self.log("🔍 Checking environment setup...")
        
        # Check if we're in the right directory
        if not Path("app/main.py").exists():
            self.errors_found.append("Not in PhotoVault directory - app/main.py not found")
            return False
            
        # Check if virtual environment is activated
        if not Path(".venv").exists():
            self.warnings_found.append("Virtual environment not found at .venv")
            
        # Check if requirements are installed
        try:
            import fastapi
            import uvicorn
            self.log("✓ Core dependencies available")
        except ImportError as e:
            self.errors_found.append(f"Missing core dependencies: {e}")
            return False
            
        return True
        
    def start_backend(self):
        """Start the backend server"""
        self.log("🚀 Starting backend server...")
        
        # Set environment variables
        env = os.environ.copy()
        env.update({
            "APP_ENV": "development",
            "JWT_SECRET": "dev-secret-key-change-in-production",
            "CSRF_SECRET": "dev-csrf-secret-change-in-production", 
            "MASTER_KEY": "dev-master-key-change-in-production",
            "FORCE_LOCAL_SQLITE": "1"
        })
        
        try:
            # Start uvicorn server
            self.backend_process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "app.main:app", 
                "--host", "127.0.0.1", 
                "--port", "8000",
                "--log-level", "info"
            ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Wait for server to start
            self.log("⏳ Waiting for server to initialize...")
            time.sleep(5)
            
            # Check if process is still running
            if self.backend_process.poll() is not None:
                stdout, stderr = self.backend_process.communicate()
                self.errors_found.append(f"Backend failed to start. STDERR: {stderr}")
                return False
                
            return True
            
        except Exception as e:
            self.errors_found.append(f"Failed to start backend: {e}")
            return False
            
    def check_backend_health(self):
        """Check if backend is responding"""
        self.log("🏥 Checking backend health...")
        
        try:
            response = requests.get("http://127.0.0.1:8000/health", timeout=10)
            if response.status_code == 200:
                self.log("✓ Backend health check passed")
                return True
            else:
                self.errors_found.append(f"Health check failed with status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.errors_found.append(f"Cannot connect to backend: {e}")
            return False
            
    def check_swagger_ui(self):
        """Check if Swagger UI is accessible"""
        self.log("📚 Checking Swagger UI...")
        
        try:
            response = requests.get("http://127.0.0.1:8000/docs", timeout=10)
            if response.status_code == 200:
                self.log("✓ Swagger UI is accessible")
                return True
            else:
                self.errors_found.append(f"Swagger UI failed with status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.errors_found.append(f"Cannot access Swagger UI: {e}")
            return False
            
    def check_routes_count(self):
        """Check how many routes are loaded"""
        self.log("🛣️ Checking loaded routes...")
        
        try:
            response = requests.get("http://127.0.0.1:8000/ops/routes", timeout=10)
            if response.status_code == 200:
                data = response.json()
                route_count = data.get("count", 0)
                self.log(f"✓ Loaded {route_count} routes")
                
                if route_count < 20:
                    self.warnings_found.append(f"Only {route_count} routes loaded - some routers may have failed to import")
                    
                return True
            else:
                self.warnings_found.append(f"Routes endpoint failed with status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.warnings_found.append(f"Cannot check routes: {e}")
            return False
            
    def check_openapi_schema(self):
        """Check OpenAPI schema generation"""
        self.log("📋 Checking OpenAPI schema...")
        
        try:
            response = requests.get("http://127.0.0.1:8000/openapi.json", timeout=10)
            if response.status_code == 200:
                schema = response.json()
                paths_count = len(schema.get("paths", {}))
                self.log(f"✓ OpenAPI schema generated with {paths_count} paths")
                return True
            else:
                self.errors_found.append(f"OpenAPI schema failed with status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.errors_found.append(f"Cannot access OpenAPI schema: {e}")
            return False
            
    def check_database_connection(self):
        """Check database connectivity"""
        self.log("🗄️ Checking database connection...")
        
        try:
            response = requests.get("http://127.0.0.1:8000/ops/db-health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log("✓ Database connection is healthy")
                    return True
                else:
                    self.warnings_found.append(f"Database health check returned: {data}")
                    return False
            else:
                self.warnings_found.append(f"Database health check failed with status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.warnings_found.append(f"Cannot check database health: {e}")
            return False
            
    def get_backend_logs(self):
        """Get backend logs to check for errors"""
        if self.backend_process and self.backend_process.poll() is None:
            try:
                # Get recent output
                self.backend_process.stdout.flush()
                self.backend_process.stderr.flush()
                return "Backend is running - check console for live logs"
            except:
                return "Could not retrieve logs"
        return "Backend process not running"
        
    def cleanup(self):
        """Clean up resources"""
        if self.backend_process:
            self.log("🧹 Stopping backend server...")
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
                
    def run_comprehensive_check(self):
        """Run all error checks"""
        self.log("=" * 60)
        self.log("    PhotoVault Comprehensive Error Check")
        self.log("=" * 60)
        
        try:
            # Step 1: Environment check
            if not self.check_environment():
                return False
                
            # Step 2: Start backend
            if not self.start_backend():
                return False
                
            # Step 3: Health checks
            self.check_backend_health()
            self.check_swagger_ui()
            self.check_routes_count()
            self.check_openapi_schema()
            self.check_database_connection()
            
            # Step 4: Report results
            self.log("=" * 60)
            self.log("    Error Check Results")
            self.log("=" * 60)
            
            if self.errors_found:
                self.log("❌ ERRORS FOUND:")
                for error in self.errors_found:
                    self.log(f"   • {error}", "ERROR")
            else:
                self.log("✅ No critical errors found!")
                
            if self.warnings_found:
                self.log("\n⚠️ WARNINGS:")
                for warning in self.warnings_found:
                    self.log(f"   • {warning}", "WARN")
            else:
                self.log("✅ No warnings found!")
                
            if not self.errors_found and not self.warnings_found:
                self.log("\n🎉 SUCCESS: PhotoVault is running perfectly!")
                self.log("📱 Access your app:")
                self.log("   • Swagger UI: http://127.0.0.1:8000/docs")
                self.log("   • Health Check: http://127.0.0.1:8000/health")
                self.log("   • API Routes: http://127.0.0.1:8000/ops/routes")
                self.log("   • Database Health: http://127.0.0.1:8000/ops/db-health")
                
            return len(self.errors_found) == 0
            
        finally:
            self.cleanup()

def main():
    checker = PhotoVaultErrorChecker()
    success = checker.run_comprehensive_check()
    
    if success:
        print("\n✨ All issues have been resolved!")
        return 0
    else:
        print("\n🔧 Some issues need attention. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())