#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for ERP Studio System
Tests all major endpoints including authentication, CRUD operations, and admin functions
"""

import requests
import sys
import json
from datetime import datetime
import uuid

class ERPBackendTester:
    def __init__(self, base_url="http://localhost:8001/api"):
        self.base_url = base_url
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tenant_id = None
        
        print(f"🚀 Starting ERP Backend Tests")
        print(f"📍 Base URL: {self.base_url}")
        print("=" * 60)

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        print(f"   {method} {endpoint}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"   ✅ PASSED - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(response_data) <= 3:
                        print(f"   📄 Response: {response_data}")
                    elif isinstance(response_data, list) and len(response_data) <= 2:
                        print(f"   📄 Response: {len(response_data)} items returned")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"   ❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   📄 Error: {error_data}")
                except:
                    print(f"   📄 Error: {response.text[:200]}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"   ❌ FAILED - Request timeout (30s)")
            return False, {}
        except Exception as e:
            print(f"   ❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_login(self):
        """Test super admin login"""
        print("\n" + "="*50)
        print("🔐 AUTHENTICATION TESTS")
        print("="*50)
        
        success, response = self.run_test(
            "Super Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@sistema.com", "password": "admin123"}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_data = response.get('user', {})
            print(f"   🎯 Token acquired for user: {self.user_data.get('name', 'Unknown')}")
            print(f"   🎯 User role: {self.user_data.get('role', 'Unknown')}")
            return True
        return False

    def test_auth_me(self):
        """Test get current user info"""
        success, response = self.run_test(
            "Get Current User Info",
            "GET", 
            "auth/me",
            200
        )
        return success

    def test_super_admin_dashboard(self):
        """Test super admin dashboard"""
        print("\n" + "="*50)
        print("📊 SUPER ADMIN DASHBOARD TESTS")
        print("="*50)
        
        success, response = self.run_test(
            "Super Admin Dashboard",
            "GET",
            "super-admin/dashboard", 
            200
        )
        
        if success:
            print(f"   📈 Total Tenants: {response.get('total_tenants', 0)}")
            print(f"   📈 Active Tenants: {response.get('active_tenants', 0)}")
            print(f"   📈 Total Users: {response.get('total_users', 0)}")
        
        return success

    def test_tenant_management(self):
        """Test tenant creation and management"""
        print("\n" + "="*50)
        print("🏢 TENANT MANAGEMENT TESTS")
        print("="*50)
        
        # Create a test tenant
        tenant_data = {
            "subdomain": f"test-tenant-{datetime.now().strftime('%H%M%S')}",
            "company_name": "Test Company Ltd",
            "cnpj": "12.345.678/0001-90",
            "razao_social": "Test Company Razao Social",
            "admin_name": "Test Admin",
            "admin_email": f"admin-{datetime.now().strftime('%H%M%S')}@testcompany.com",
            "admin_password": "TestPass123!",
            "plan": "basic"
        }
        
        success, response = self.run_test(
            "Create New Tenant",
            "POST",
            "super-admin/tenants",
            200,
            data=tenant_data
        )
        
        if success:
            self.tenant_id = response.get('id')
            print(f"   🎯 Created tenant ID: {self.tenant_id}")
        
        # List all tenants
        success2, response2 = self.run_test(
            "List All Tenants",
            "GET",
            "super-admin/tenants",
            200
        )
        
        if success2:
            print(f"   📋 Total tenants found: {len(response2)}")
        
        return success and success2

    def test_user_management(self):
        """Test user management operations"""
        print("\n" + "="*50)
        print("👥 USER MANAGEMENT TESTS")
        print("="*50)
        
        # List users
        success1, response1 = self.run_test(
            "List All Users",
            "GET",
            "users",
            200
        )
        
        if success1:
            print(f"   👤 Total users found: {len(response1)}")
        
        # Create a new user (this will fail for super admin without tenant, but let's test)
        user_data = {
            "email": f"testuser-{datetime.now().strftime('%H%M%S')}@test.com",
            "name": "Test User",
            "password": "TestPass123!",
            "role": "operador"
        }
        
        success2, response2 = self.run_test(
            "Create New User (Expected to fail for super admin)",
            "POST",
            "users",
            403,  # Expected to fail since super admin needs tenant context
            data=user_data
        )
        
        return success1 and success2

    def test_dashboard_regular(self):
        """Test regular dashboard (should redirect to super admin dashboard)"""
        print("\n" + "="*50)
        print("📊 REGULAR DASHBOARD TESTS")
        print("="*50)
        
        success, response = self.run_test(
            "Regular Dashboard (Super Admin Context)",
            "GET",
            "dashboard",
            200
        )
        return success

    def test_clientes_api(self):
        """Test clientes (customers) API endpoints"""
        print("\n" + "="*50)
        print("👥 CLIENTES API TESTS")
        print("="*50)
        
        # List clientes (should fail for super admin without tenant)
        success1, response1 = self.run_test(
            "List Clientes (Expected to fail for super admin)",
            "GET",
            "clientes",
            400  # Expected to fail - super admin has no tenant
        )
        
        # Create cliente (should also fail)
        cliente_data = {
            "nome": "Test Cliente",
            "email": "cliente@test.com",
            "telefone": "(11) 99999-9999",
            "cpf_cnpj": "123.456.789-00"
        }
        
        success2, response2 = self.run_test(
            "Create Cliente (Expected to fail for super admin)",
            "POST",
            "clientes",
            400,  # Expected to fail - super admin has no tenant
            data=cliente_data
        )
        
        return success1 and success2

    def test_produtos_api(self):
        """Test produtos (products) API endpoints"""
        print("\n" + "="*50)
        print("📦 PRODUTOS API TESTS")
        print("="*50)
        
        # List produtos (should fail for super admin without tenant)
        success1, response1 = self.run_test(
            "List Produtos (Expected to fail for super admin)",
            "GET",
            "produtos",
            400  # Expected to fail - super admin has no tenant
        )
        
        # Create produto (should also fail)
        produto_data = {
            "nome": "Test Product",
            "descricao": "Test product description",
            "preco": 99.99,
            "estoque_atual": 10,
            "estoque_minimo": 5
        }
        
        success2, response2 = self.run_test(
            "Create Produto (Expected to fail for super admin)",
            "POST",
            "produtos",
            400,  # Expected to fail - super admin has no tenant
            data=produto_data
        )
        
        return success1 and success2

    def test_servicos_api(self):
        """Test servicos (services) API endpoints"""
        print("\n" + "="*50)
        print("🛠️ SERVICOS API TESTS")
        print("="*50)
        
        # List servicos (should fail for super admin without tenant)
        success1, response1 = self.run_test(
            "List Servicos (Expected to fail for super admin)",
            "GET",
            "servicos",
            400  # Expected to fail - super admin has no tenant
        )
        
        # Create servico (should also fail)
        servico_data = {
            "nome": "Test Service",
            "descricao": "Test service description",
            "duracao_minutos": 60,
            "preco": 150.00
        }
        
        success2, response2 = self.run_test(
            "Create Servico (Expected to fail for super admin)",
            "POST",
            "servicos",
            400,  # Expected to fail - super admin has no tenant
            data=servico_data
        )
        
        return success1 and success2

    def test_vencimentos_api(self):
        """Test vencimentos (expiration notifications) API endpoints"""
        print("\n" + "="*50)
        print("⏰ VENCIMENTOS API TESTS")
        print("="*50)
        
        # List vencimentos (should fail for super admin without tenant)
        success1, response1 = self.run_test(
            "List Vencimentos (Expected to fail for super admin)",
            "GET",
            "vencimentos",
            400  # Expected to fail - super admin has no tenant
        )
        
        # List próximos vencimentos (should also fail)
        success2, response2 = self.run_test(
            "List Próximos Vencimentos (Expected to fail for super admin)",
            "GET",
            "vencimentos/proximos",
            400  # Expected to fail - super admin has no tenant
        )
        
        return success1 and success2

    def test_invalid_endpoints(self):
        """Test some invalid endpoints to ensure proper error handling"""
        print("\n" + "="*50)
        print("❌ ERROR HANDLING TESTS")
        print("="*50)
        
        # Test invalid login
        success1, response1 = self.run_test(
            "Invalid Login Credentials",
            "POST",
            "auth/login",
            401,
            data={"email": "invalid@test.com", "password": "wrongpass"}
        )
        
        # Test non-existent endpoint
        success2, response2 = self.run_test(
            "Non-existent Endpoint",
            "GET",
            "nonexistent/endpoint",
            404
        )
        
        # Test unauthorized access (without token)
        old_token = self.token
        self.token = None
        success3, response3 = self.run_test(
            "Unauthorized Access",
            "GET",
            "users",
            401
        )
        self.token = old_token  # Restore token
        
        return success1 and success2 and success3

    def run_all_tests(self):
        """Run all backend tests"""
        print("🧪 ERP BACKEND API COMPREHENSIVE TESTING")
        print("🕒 Started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("=" * 60)
        
        # Test sequence
        tests = [
            ("Authentication", self.test_login),
            ("User Info", self.test_auth_me),
            ("Super Admin Dashboard", self.test_super_admin_dashboard),
            ("Tenant Management", self.test_tenant_management),
            ("User Management", self.test_user_management),
            ("Regular Dashboard", self.test_dashboard_regular),
            ("Clientes API", self.test_clientes_api),
            ("Produtos API", self.test_produtos_api),
            ("Servicos API", self.test_servicos_api),
            ("Vencimentos API", self.test_vencimentos_api),
            ("Error Handling", self.test_invalid_endpoints)
        ]
        
        failed_tests = []
        
        for test_name, test_func in tests:
            try:
                if not test_func():
                    failed_tests.append(test_name)
            except Exception as e:
                print(f"\n❌ CRITICAL ERROR in {test_name}: {str(e)}")
                failed_tests.append(test_name)
        
        # Final results
        print("\n" + "="*60)
        print("📊 FINAL TEST RESULTS")
        print("="*60)
        print(f"✅ Tests Passed: {self.tests_passed}/{self.tests_run}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}/{self.tests_run}")
        
        if failed_tests:
            print(f"\n🚨 Failed Test Categories:")
            for test in failed_tests:
                print(f"   - {test}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 BACKEND TESTS: OVERALL SUCCESS")
            return 0
        else:
            print("⚠️  BACKEND TESTS: NEEDS ATTENTION")
            return 1

def main():
    """Main test execution"""
    tester = ERPBackendTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())