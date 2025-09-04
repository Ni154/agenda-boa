#!/usr/bin/env python3
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime, timezone
import uuid

# Configuration
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "erp_sistema"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_test_data():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("🚀 Criando dados de teste...")
    
    # Create test company
    empresa_id = str(uuid.uuid4())
    empresa = {
        "id": empresa_id,
        "nome": "Empresa Teste",
        "cnpj": "12.345.678/0001-90",
        "razao_social": "Empresa Teste LTDA",
        "nome_fantasia": "Empresa Teste",
        "endereco": "Rua Teste, 123 - São Paulo, SP",
        "telefone": "(11) 99999-9999",
        "email": "contato@empresateste.com",
        "usar_certificado": False,
        "ativa": True,
        "created_at": datetime.now(timezone.utc)
    }
    await db.empresas.insert_one(empresa)
    print(f"✅ Empresa criada: {empresa['nome']}")
    
    # Create test admin user
    admin_user = {
        "id": str(uuid.uuid4()),
        "email": "admin@empresa.com",
        "name": "Administrador",
        "role": "admin_empresa",
        "empresa_id": empresa_id,
        "active": True,
        "hashed_password": pwd_context.hash("admin123"),
        "created_at": datetime.now(timezone.utc)
    }
    await db.users.insert_one(admin_user)
    print(f"✅ Usuário admin criado: {admin_user['email']} / admin123")
    
    # Create test clients
    clientes = [
        {
            "id": str(uuid.uuid4()),
            "nome": "João Silva",
            "email": "joao@email.com",
            "telefone": "(11) 99999-1111",
            "cpf_cnpj": "123.456.789-01",
            "endereco": "Rua A, 123 - São Paulo, SP",
            "empresa_id": empresa_id,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "nome": "Maria Santos",
            "email": "maria@email.com",
            "telefone": "(11) 99999-2222",
            "cpf_cnpj": "987.654.321-09",
            "endereco": "Rua B, 456 - São Paulo, SP",
            "empresa_id": empresa_id,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "nome": "Pedro Costa",
            "email": "pedro@email.com",
            "telefone": "(11) 99999-3333",
            "cpf_cnpj": "456.789.123-45",
            "endereco": "Rua C, 789 - São Paulo, SP",
            "empresa_id": empresa_id,
            "created_at": datetime.now(timezone.utc)
        }
    ]
    await db.clientes.insert_many(clientes)
    print(f"✅ {len(clientes)} clientes criados")
    
    # Create test products
    produtos = [
        {
            "id": str(uuid.uuid4()),
            "codigo": "PROD001",
            "nome": "Shampoo Premium",
            "descricao": "Shampoo hidratante para todos os tipos de cabelo",
            "categoria": "Cabelo",
            "ncm": "33051000",
            "custo": 15.50,
            "preco": 35.00,
            "estoque_atual": 50,
            "estoque_minimo": 10,
            "empresa_id": empresa_id,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "codigo": "PROD002",
            "nome": "Condicionador Nutritivo",
            "descricao": "Condicionador nutritivo para cabelos ressecados",
            "categoria": "Cabelo",
            "ncm": "33051000",
            "custo": 18.00,
            "preco": 42.00,
            "estoque_atual": 30,
            "estoque_minimo": 8,
            "empresa_id": empresa_id,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "codigo": "PROD003",
            "nome": "Creme para Mãos",
            "descricao": "Creme hidratante para mãos e corpo",
            "categoria": "Corpo",
            "ncm": "33049900",
            "custo": 8.50,
            "preco": 22.00,
            "estoque_atual": 25,
            "estoque_minimo": 5,
            "empresa_id": empresa_id,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "codigo": "PROD004",
            "nome": "Máscara Facial",
            "descricao": "Máscara facial hidratante e revitalizante",
            "categoria": "Rosto",
            "ncm": "33049900",
            "custo": 25.00,
            "preco": 65.00,
            "estoque_atual": 15,
            "estoque_minimo": 3,
            "empresa_id": empresa_id,
            "created_at": datetime.now(timezone.utc)
        }
    ]
    await db.produtos.insert_many(produtos)
    print(f"✅ {len(produtos)} produtos criados")
    
    # Create test services
    servicos = [
        {
            "id": str(uuid.uuid4()),
            "nome": "Corte de Cabelo Feminino",
            "descricao": "Corte profissional para cabelos femininos",
            "duracao_minutos": 60,
            "preco": 80.00,
            "tributacao_iss": {
                "aliquota": 2.0,
                "codigo_servico_municipal": "14.01"
            },
            "empresa_id": empresa_id,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "nome": "Corte de Cabelo Masculino",
            "descricao": "Corte profissional para cabelos masculinos",
            "duracao_minutos": 45,
            "preco": 50.00,
            "tributacao_iss": {
                "aliquota": 2.0,
                "codigo_servico_municipal": "14.01"
            },
            "empresa_id": empresa_id,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "nome": "Hidratação Capilar",
            "descricao": "Tratamento de hidratação profunda para cabelos",
            "duracao_minutos": 90,
            "preco": 120.00,
            "tributacao_iss": {
                "aliquota": 2.0,
                "codigo_servico_municipal": "14.01"
            },
            "empresa_id": empresa_id,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "nome": "Manicure e Pedicure",
            "descricao": "Cuidados completos para unhas das mãos e pés",
            "duracao_minutos": 75,
            "preco": 60.00,
            "tributacao_iss": {
                "aliquota": 2.0,
                "codigo_servico_municipal": "14.01"
            },
            "empresa_id": empresa_id,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "nome": "Limpeza de Pele",
            "descricao": "Limpeza facial profunda e hidratação",
            "duracao_minutos": 120,
            "preco": 150.00,
            "tributacao_iss": {
                "aliquota": 2.0,
                "codigo_servico_municipal": "14.01"
            },
            "empresa_id": empresa_id,
            "created_at": datetime.now(timezone.utc)
        }
    ]
    await db.servicos.insert_many(servicos)
    print(f"✅ {len(servicos)} serviços criados")
    
    # Create sample sales
    vendas = [
        {
            "id": str(uuid.uuid4()),
            "cliente_id": clientes[0]["id"],
            "cliente_nome": clientes[0]["nome"],
            "itens": [
                {
                    "tipo": "servico",
                    "item_id": servicos[0]["id"],
                    "nome": servicos[0]["nome"],
                    "quantidade": 1,
                    "preco_unitario": servicos[0]["preco"],
                    "desconto": 0,
                    "total": servicos[0]["preco"]
                }
            ],
            "subtotal": servicos[0]["preco"],
            "desconto_total": 0,
            "total": servicos[0]["preco"],
            "forma_pagamento": "cartao_credito",
            "emitir_nota": False,
            "empresa_id": empresa_id,
            "vendedor_id": admin_user["id"],
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "cliente_id": clientes[1]["id"],
            "cliente_nome": clientes[1]["nome"],
            "itens": [
                {
                    "tipo": "produto",
                    "item_id": produtos[0]["id"],
                    "nome": produtos[0]["nome"],
                    "quantidade": 2,
                    "preco_unitario": produtos[0]["preco"],
                    "desconto": 0,
                    "total": produtos[0]["preco"] * 2
                }
            ],
            "subtotal": produtos[0]["preco"] * 2,
            "desconto_total": 0,
            "total": produtos[0]["preco"] * 2,
            "forma_pagamento": "dinheiro",
            "emitir_nota": False,
            "empresa_id": empresa_id,
            "vendedor_id": admin_user["id"],
            "created_at": datetime.now(timezone.utc)
        }
    ]
    await db.vendas.insert_many(vendas)
    print(f"✅ {len(vendas)} vendas de exemplo criadas")
    
    client.close()
    print("\n🎉 Dados de teste criados com sucesso!")
    print("\n📋 Credenciais de acesso:")
    print("Email: admin@empresa.com")
    print("Senha: admin123")
    print("\n🌐 Acesse: https://enterprise-hub-50.preview.emergentagent.com")

if __name__ == "__main__":
    asyncio.run(create_test_data())