import requests
import sys
from datetime import datetime
import json

class ERPSystemTester:
    def __init__(self, base_url="https://enterprise-hub-50.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.empresa_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_login(self):
        """Test login with provided credentials"""
        print("\n" + "="*50)
        print("TESTING AUTHENTICATION")
        print("="*50)
        
        success, response = self.run_test(
            "Login with admin credentials",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@empresa.com", "password": "admin123"}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_data = response.get('user', {})
            self.empresa_id = self.user_data.get('empresa_id')
            print(f"✅ Login successful! User: {self.user_data.get('name', 'Unknown')}")
            print(f"   Company ID: {self.empresa_id}")
            return True
        else:
            print("❌ Login failed - cannot proceed with other tests")
            return False

    def test_auth_me(self):
        """Test getting current user info"""
        success, response = self.run_test(
            "Get current user info",
            "GET",
            "auth/me",
            200
        )
        return success

    def test_dashboard(self):
        """Test dashboard endpoint"""
        print("\n" + "="*50)
        print("TESTING DASHBOARD")
        print("="*50)
        
        success, response = self.run_test(
            "Get dashboard data",
            "GET",
            "dashboard",
            200
        )
        
        if success:
            print(f"📊 Dashboard KPIs:")
            print(f"   Total Vendas: R$ {response.get('total_vendas', 0):.2f}")
            print(f"   Lucro: R$ {response.get('lucro', 0):.2f}")
            print(f"   Itens Estoque: {response.get('itens_estoque', 0)}")
            print(f"   Margem Lucro: {response.get('margem_lucro', 0):.2f}%")
        
        return success

    def test_clientes(self):
        """Test clients management"""
        print("\n" + "="*50)
        print("TESTING CLIENTS MANAGEMENT")
        print("="*50)
        
        # Get existing clients
        success, clients = self.run_test(
            "Get all clients",
            "GET",
            "clientes",
            200
        )
        
        if success:
            print(f"📋 Found {len(clients)} clients")
            for i, client in enumerate(clients[:3]):  # Show first 3
                print(f"   {i+1}. {client.get('nome', 'Unknown')} - {client.get('email', 'No email')}")
        
        # Test creating a new client
        test_client = {
            "nome": "Cliente Teste API",
            "email": "teste@email.com",
            "telefone": "(11) 99999-9999",
            "cpf_cnpj": "123.456.789-00"
        }
        
        create_success, new_client = self.run_test(
            "Create new client",
            "POST",
            "clientes",
            200,
            data=test_client
        )
        
        return success and create_success

    def test_produtos(self):
        """Test products management"""
        print("\n" + "="*50)
        print("TESTING PRODUCTS MANAGEMENT")
        print("="*50)
        
        # Get existing products
        success, products = self.run_test(
            "Get all products",
            "GET",
            "produtos",
            200
        )
        
        if success:
            print(f"📦 Found {len(products)} products")
            for i, product in enumerate(products[:4]):  # Show first 4
                print(f"   {i+1}. {product.get('nome', 'Unknown')} - R$ {product.get('preco', 0):.2f} (Estoque: {product.get('estoque_atual', 0)})")
        
        # Test creating a new product
        test_product = {
            "nome": "Produto Teste API",
            "descricao": "Produto criado via teste de API",
            "categoria": "Teste",
            "preco": 25.50,
            "custo": 15.00,
            "estoque_atual": 10,
            "estoque_minimo": 5
        }
        
        create_success, new_product = self.run_test(
            "Create new product",
            "POST",
            "produtos",
            200,
            data=test_product
        )
        
        return success and create_success

    def test_servicos(self):
        """Test services management"""
        print("\n" + "="*50)
        print("TESTING SERVICES MANAGEMENT")
        print("="*50)
        
        # Get existing services
        success, services = self.run_test(
            "Get all services",
            "GET",
            "servicos",
            200
        )
        
        if success:
            print(f"💼 Found {len(services)} services")
            for i, service in enumerate(services[:5]):  # Show first 5
                print(f"   {i+1}. {service.get('nome', 'Unknown')} - R$ {service.get('preco', 0):.2f} ({service.get('duracao_minutos', 0)} min)")
        
        # Test creating a new service
        test_service = {
            "nome": "Serviço Teste API",
            "descricao": "Serviço criado via teste de API",
            "duracao_minutos": 45,
            "preco": 80.00
        }
        
        create_success, new_service = self.run_test(
            "Create new service",
            "POST",
            "servicos",
            200,
            data=test_service
        )
        
        return success and create_success

    def test_vendas(self):
        """Test sales management"""
        print("\n" + "="*50)
        print("TESTING SALES MANAGEMENT")
        print("="*50)
        
        # Get existing sales
        success, sales = self.run_test(
            "Get all sales",
            "GET",
            "vendas",
            200
        )
        
        if success:
            print(f"💰 Found {len(sales)} sales")
            total_sales_value = sum(sale.get('total', 0) for sale in sales)
            print(f"   Total sales value: R$ {total_sales_value:.2f}")
        
        # Get products to create a test sale
        products_success, products = self.run_test(
            "Get products for sale test",
            "GET",
            "produtos",
            200
        )
        
        if products_success and products:
            # Create a test sale with first available product
            first_product = products[0]
            test_sale = {
                "cliente_nome": "Cliente Teste Venda",
                "itens": [
                    {
                        "tipo": "produto",
                        "item_id": first_product['id'],
                        "nome": first_product['nome'],
                        "quantidade": 2,
                        "preco_unitario": first_product['preco'],
                        "desconto": 0.0,
                        "total": first_product['preco'] * 2
                    }
                ],
                "forma_pagamento": "dinheiro",
                "emitir_nota": False
            }
            
            create_success, new_sale = self.run_test(
                "Create new sale",
                "POST",
                "vendas",
                200,
                data=test_sale
            )
            
            return success and create_success
        
        return success

    def test_empresas(self):
        """Test companies management"""
        print("\n" + "="*50)
        print("TESTING COMPANIES MANAGEMENT")
        print("="*50)
        
        success, companies = self.run_test(
            "Get companies",
            "GET",
            "empresas",
            200
        )
        
        if success:
            print(f"🏢 Found {len(companies)} companies")
            for i, company in enumerate(companies):
                print(f"   {i+1}. {company.get('nome', 'Unknown')} - {company.get('cnpj', 'No CNPJ')}")
        
        return success

def main():
    print("🚀 Starting ERP System API Tests")
    print("="*60)
    
    tester = ERPSystemTester()
    
    # Test authentication first
    if not tester.test_login():
        print("\n❌ Authentication failed - stopping all tests")
        return 1
    
    # Test auth/me endpoint
    tester.test_auth_me()
    
    # Test all modules
    tester.test_dashboard()
    tester.test_clientes()
    tester.test_produtos()
    tester.test_servicos()
    tester.test_vendas()
    tester.test_empresas()
    
    # Print final results
    print("\n" + "="*60)
    print("📊 FINAL TEST RESULTS")
    print("="*60)
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Tests Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("\n🎉 All tests passed! Backend is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {tester.tests_run - tester.tests_passed} tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())