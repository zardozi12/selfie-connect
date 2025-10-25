import requests
import json
import time
import os
from typing import Optional

BASE_URL = "http://127.0.0.1:8000"

class PhotoVaultTester:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.session = requests.Session()
        
    def log(self, message: str, status: str = "INFO"):
        print(f"[{status}] {message}")
        
    def test_endpoint(self, method: str, endpoint: str, data=None, files=None, headers=None):
        """Generic endpoint tester"""
        url = f"{BASE_URL}{endpoint}"
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers)
            elif method.upper() == "POST":
                if files:
                    response = self.session.post(url, files=files, headers=headers)
                else:
                    response = self.session.post(url, json=data, headers=headers)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=headers)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers)
            else:
                self.log(f"Unsupported method: {method}", "ERROR")
                return None
                
            self.log(f"{method} {endpoint} -> {response.status_code}")
            if response.status_code < 400:
                try:
                    return response.json()
                except:
                    return response.text
            else:
                self.log(f"Error: {response.text}", "ERROR")
                return None
        except Exception as e:
            self.log(f"Exception testing {endpoint}: {str(e)}", "ERROR")
            return None
    
    def get_auth_headers(self):
        """Get authorization headers"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}
    
    def test_health_endpoints(self):
        """Test health and system endpoints"""
        self.log("=== TESTING HEALTH ENDPOINTS ===")
        
        # Basic health check
        self.test_endpoint("GET", "/health")
        
        # Metrics endpoint
        self.test_endpoint("GET", "/metrics")
        
        # Database health (if available)
        self.test_endpoint("GET", "/ops/db-health", headers=self.get_auth_headers())
    
    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        self.log("=== TESTING AUTH ENDPOINTS ===")
        
        # Test signup
        signup_data = {
            "email": "autotest@example.com",
            "password": "AutoTest123!",
            "name": "Auto Test User"
        }
        
        result = self.test_endpoint("POST", "/auth/signup", data=signup_data)
        if result and "access_token" in result:
            self.token = result["access_token"]
            self.log("Signup successful, token obtained")
        
        # Test login
        login_data = {
            "email": "autotest@example.com",
            "password": "AutoTest123!"
        }
        
        result = self.test_endpoint("POST", "/auth/login", data=login_data)
        if result and "access_token" in result:
            self.token = result["access_token"]
            self.log("Login successful, token updated")
        
        # Test token verification
        self.test_endpoint("GET", "/auth/verify", headers=self.get_auth_headers())
        
        # Test token info
        self.test_endpoint("GET", "/auth/token-info", headers=self.get_auth_headers())
        
        # Test session endpoints
        if self.user_id:
            self.test_endpoint("POST", "/auth/session-login", data={"user_id": self.user_id})
            self.test_endpoint("POST", "/auth/refresh", data={"session_token": "dummy_token"})
            self.test_endpoint("POST", "/auth/logout", data={"session_token": "dummy_token"})
    
    def test_dashboard_endpoints(self):
        """Test dashboard endpoints"""
        self.log("=== TESTING DASHBOARD ENDPOINTS ===")
        
        headers = self.get_auth_headers()
        
        # Common dashboard endpoints
        self.test_endpoint("GET", "/dashboard", headers=headers)
        self.test_endpoint("GET", "/dashboard/stats", headers=headers)
        self.test_endpoint("GET", "/dashboard/recent", headers=headers)
        self.test_endpoint("GET", "/dashboard/summary", headers=headers)
    
    def test_album_endpoints(self):
        """Test album management endpoints"""
        self.log("=== TESTING ALBUM ENDPOINTS ===")
        
        headers = self.get_auth_headers()
        
        # List albums
        self.test_endpoint("GET", "/albums", headers=headers)
        
        # Create album
        album_data = {
            "name": "Test Album",
            "description": "Auto-generated test album"
        }
        album_result = self.test_endpoint("POST", "/albums", data=album_data, headers=headers)
        
        album_id = None
        if album_result and "id" in album_result:
            album_id = album_result["id"]
            
            # Test album operations with ID
            self.test_endpoint("GET", f"/albums/{album_id}", headers=headers)
            self.test_endpoint("PUT", f"/albums/{album_id}", data={"name": "Updated Album"}, headers=headers)
            self.test_endpoint("DELETE", f"/albums/{album_id}", headers=headers)
    
    def test_image_endpoints(self):
        """Test image management endpoints"""
        self.log("=== TESTING IMAGE ENDPOINTS ===")
        
        headers = self.get_auth_headers()
        
        # List images
        self.test_endpoint("GET", "/images", headers=headers)
        self.test_endpoint("GET", "/images/recent", headers=headers)
        
        # Bulk operations
        self.test_endpoint("GET", "/images/bulk", headers=headers)
        self.test_endpoint("POST", "/images/upload/bulk", headers=headers)
        
        # Search endpoints
        self.test_endpoint("GET", "/search/advanced", headers=headers)
        self.test_endpoint("POST", "/search/advanced", data={"query": "test"}, headers=headers)
    
    def test_admin_endpoints(self):
        """Test admin endpoints"""
        self.log("=== TESTING ADMIN ENDPOINTS ===")
        
        headers = self.get_auth_headers()
        
        # Admin endpoints (may require admin privileges)
        self.test_endpoint("GET", "/admin", headers=headers)
        self.test_endpoint("GET", "/admin/users", headers=headers)
        self.test_endpoint("GET", "/admin/stats", headers=headers)
        self.test_endpoint("GET", "/admin/system", headers=headers)
    
    def test_public_endpoints(self):
        """Test public sharing endpoints"""
        self.log("=== TESTING PUBLIC ENDPOINTS ===")
        
        # Public endpoints (no auth required)
        self.test_endpoint("GET", "/share")
        self.test_endpoint("GET", "/share/public")
        
        # Test with dummy share token
        self.test_endpoint("GET", "/share/dummy-token")
    
    def test_api_endpoints(self):
        """Test general API endpoints"""
        self.log("=== TESTING GENERAL API ENDPOINTS ===")
        
        headers = self.get_auth_headers()
        
        # Common API patterns
        endpoints = [
            "/api/v1/status",
            "/api/users/me",
            "/api/settings",
            "/api/profile",
        ]
        
        for endpoint in endpoints:
            self.test_endpoint("GET", endpoint, headers=headers)
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        self.log("STARTING COMPREHENSIVE API TESTING")
        self.log(f"Testing against: {BASE_URL}")
        
        # Test in logical order
        self.test_health_endpoints()
        self.test_auth_endpoints()
        
        if self.token:
            self.test_dashboard_endpoints()
            self.test_album_endpoints()
            self.test_image_endpoints()
            self.test_admin_endpoints()
            self.test_api_endpoints()
        else:
            self.log("No authentication token available, skipping protected endpoints", "WARNING")
        
        self.test_public_endpoints()
        
        self.log("TESTING COMPLETED")

def main():
    """Main test runner"""
    print("PhotoVault API Comprehensive Tester")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Server is running (Status: {response.status_code})")
    except:
        print("Server is not running!")
        print("Please start the server first:")
        print("cd photovault")
        print("python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8999")
        return
    
    # Run tests
    tester = PhotoVaultTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()