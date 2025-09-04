#!/usr/bin/env python3
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from passlib.context import CryptContext
import json

# Add backend to path
sys.path.append('/app/backend')

from database import Base, Tenant, User, Cliente, Produto, Servico, Venda

# Configuration
DATABASE_URL = os.environ.get('DATABASE_URL', "sqlite:///./erp_saas.db")
# Handle SQLite and PostgreSQL
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(DATABASE_URL)
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_saas_data():
    """Create SaaS multi-tenant data"""
    print("🚀 Criando sistema SaaS multi-tenant...")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas PostgreSQL criadas")
    
    db = SessionLocal()
    
    try:
        # 1. Create Super Admin
        super_admin = db.query(User).filter(
            User.email == "admin@sistema.com",
            User.role == "super_admin"
        ).first()
        
        if not super_admin:
            super_admin = User(
                id=str(uuid.uuid4()),
                email="admin@sistema.com",
                name="Super Administrador",
                hashed_password=pwd_context.hash("admin123"),
                role="super_admin",
                tenant_id=None,
                is_active=True
            )
            db.add(super_admin)
            print("✅ Super Admin criado: admin@sistema.com / admin123")
        
        # 2. Create Demo Tenant 1 - Salão de Beleza
        tenant1_id = str(uuid.uuid4())
        tenant1 = Tenant(
            id=tenant1_id,
            subdomain="salao-bella",
            company_name="Salão Bella Vista",
            cnpj="12.345.678/0001-90",
            razao_social="Salão Bella Vista LTDA",
            nome_fantasia="Bella Vista",
            endereco="Rua das Flores, 123 - São Paulo, SP",
            telefone="(11) 99999-1111",
            email="contato@salaobella.com",
            plan="premium",
            is_active=True,
            subscription_status="active",
            trial_ends_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        db.add(tenant1)
        
        # Admin user for tenant 1
        admin1 = User(
            id=str(uuid.uuid4()),
            email="admin@salaobella.com",
            name="Maria Silva",
            hashed_password=pwd_context.hash("bella123"),
            role="admin_empresa",
            tenant_id=tenant1_id,
            is_active=True
        )
        db.add(admin1)
        print("✅ Tenant 1 - Salão Bella: admin@salaobella.com / bella123")
        
        # 3. Create Demo Tenant 2 - Clínica Médica
        tenant2_id = str(uuid.uuid4())
        tenant2 = Tenant(
            id=tenant2_id,
            subdomain="clinica-vida",
            company_name="Clínica Vida e Saúde",
            cnpj="98.765.432/0001-10",
            razao_social="Clínica Vida e Saúde LTDA",
            nome_fantasia="Vida e Saúde",
            endereco="Av. Saúde, 456 - Rio de Janeiro, RJ",
            telefone="(21) 88888-2222",
            email="contato@clinicavida.com",
            plan="basic",
            is_active=True,
            subscription_status="trial",
            trial_ends_at=datetime.now(timezone.utc) + timedelta(days=15)
        )
        db.add(tenant2)
        
        # Admin user for tenant 2
        admin2 = User(
            id=str(uuid.uuid4()),
            email="admin@clinicavida.com",
            name="Dr. João Santos",
            hashed_password=pwd_context.hash("vida123"),
            role="admin_empresa",
            tenant_id=tenant2_id,
            is_active=True
        )
        db.add(admin2)
        print("✅ Tenant 2 - Clínica Vida: admin@clinicavida.com / vida123")
        
        # 4. Create Demo Tenant 3 - Suspended (for testing)
        tenant3_id = str(uuid.uuid4())
        tenant3 = Tenant(
            id=tenant3_id,
            subdomain="loja-suspensa",
            company_name="Loja Suspensa LTDA",
            cnpj="11.222.333/0001-44",
            razao_social="Loja Suspensa LTDA",
            plan="basic",
            is_active=False,
            subscription_status="suspended"
        )
        db.add(tenant3)
        
        admin3 = User(
            id=str(uuid.uuid4()),
            email="admin@suspensa.com",
            name="Admin Suspenso",
            hashed_password=pwd_context.hash("suspensa123"),
            role="admin_empresa",
            tenant_id=tenant3_id,
            is_active=False
        )
        db.add(admin3)
        print("✅ Tenant 3 - Loja Suspensa (para teste): admin@suspensa.com / suspensa123")
        
        db.commit()
        
        # 5. Populate Tenant 1 (Salão Bella) with data
        print("\n📊 Populando dados do Salão Bella...")
        
        # Clientes for Tenant 1
        clientes_t1 = [
            Cliente(
                id=str(uuid.uuid4()),
                nome="Ana Costa",
                email="ana@email.com",
                telefone="(11) 99999-1111",
                cpf_cnpj="123.456.789-01",
                endereco="Rua A, 123",
                tenant_id=tenant1_id
            ),
            Cliente(
                id=str(uuid.uuid4()),
                nome="Beatriz Lima",
                email="beatriz@email.com",
                telefone="(11) 99999-2222",
                cpf_cnpj="987.654.321-09",
                endereco="Rua B, 456",
                tenant_id=tenant1_id
            ),
            Cliente(
                id=str(uuid.uuid4()),
                nome="Carlos Mendes",
                email="carlos@email.com",
                telefone="(11) 99999-3333",
                cpf_cnpj="456.789.123-45",
                endereco="Rua C, 789",
                tenant_id=tenant1_id
            )
        ]
        db.add_all(clientes_t1)
        
        # Produtos for Tenant 1
        produtos_t1 = [
            Produto(
                id=uuid.uuid4(),
                codigo="SHAMP001",
                nome="Shampoo Anti-Idade",
                descricao="Shampoo premium para cabelos maduros",
                categoria="Cabelo",
                ncm="33051000",
                custo=18.50,
                preco=45.00,
                estoque_atual=25,
                estoque_minimo=5,
                tenant_id=tenant1_id
            ),
            Produto(
                id=uuid.uuid4(),
                codigo="COND001", 
                nome="Condicionador Hidratante",
                descricao="Condicionador para cabelos ressecados",
                categoria="Cabelo",
                ncm="33051000",
                custo=22.00,
                preco=52.00,
                estoque_atual=18,
                estoque_minimo=4,
                tenant_id=tenant1_id
            ),
            Produto(
                id=uuid.uuid4(),
                codigo="MASC001",
                nome="Máscara de Tratamento",
                descricao="Máscara intensiva para cabelos danificados",
                categoria="Cabelo",
                ncm="33051000",
                custo=35.00,
                preco=89.00,
                estoque_atual=12,
                estoque_minimo=3,
                tenant_id=tenant1_id
            )
        ]
        db.add_all(produtos_t1)
        
        # Serviços for Tenant 1
        servicos_t1 = [
            Servico(
                id=uuid.uuid4(),
                nome="Corte Feminino Premium",
                descricao="Corte personalizado com styling",
                duracao_minutos=90,
                preco=120.00,
                tributacao_iss=json.dumps({"aliquota": 2.0, "codigo_servico_municipal": "14.01"}),
                tenant_id=tenant1_id
            ),
            Servico(
                id=uuid.uuid4(),
                nome="Coloração Completa",
                descricao="Coloração profissional com produtos premium",
                duracao_minutos=180,
                preco=280.00,
                tributacao_iss=json.dumps({"aliquota": 2.0, "codigo_servico_municipal": "14.01"}),
                tenant_id=tenant1_id
            ),
            Servico(
                id=uuid.uuid4(),
                nome="Hidratação Intensiva",
                descricao="Tratamento de hidratação profunda",
                duracao_minutos=120,
                preco=150.00,
                tributacao_iss=json.dumps({"aliquota": 2.0, "codigo_servico_municipal": "14.01"}),
                tenant_id=tenant1_id
            ),
            Servico(
                id=uuid.uuid4(),
                nome="Manicure e Pedicure Spa",
                descricao="Tratamento completo de unhas com relaxamento",
                duracao_minutos=90,
                preco=85.00,
                tributacao_iss=json.dumps({"aliquota": 2.0, "codigo_servico_municipal": "14.01"}),
                tenant_id=tenant1_id
            )
        ]
        db.add_all(servicos_t1)
        
        db.commit()
        
        # Sample sales for Tenant 1
        vendas_t1 = [
            Venda(
                id=uuid.uuid4(),
                cliente_id=clientes_t1[0].id,
                cliente_nome=clientes_t1[0].nome,
                itens=json.dumps([{
                    "tipo": "servico",
                    "item_id": str(servicos_t1[0].id),
                    "nome": servicos_t1[0].nome,
                    "quantidade": 1,
                    "preco_unitario": servicos_t1[0].preco,
                    "desconto": 0,
                    "total": servicos_t1[0].preco
                }]),
                subtotal=servicos_t1[0].preco,
                total=servicos_t1[0].preco,
                forma_pagamento="cartao_credito",
                emitir_nota=False,
                tenant_id=tenant1_id,
                vendedor_id=admin1.id
            ),
            Venda(
                id=uuid.uuid4(),
                cliente_id=clientes_t1[1].id,
                cliente_nome=clientes_t1[1].nome,
                itens=json.dumps([{
                    "tipo": "produto",
                    "item_id": str(produtos_t1[0].id),
                    "nome": produtos_t1[0].nome,
                    "quantidade": 2,
                    "preco_unitario": produtos_t1[0].preco,
                    "desconto": 0,
                    "total": produtos_t1[0].preco * 2
                }]),
                subtotal=produtos_t1[0].preco * 2,
                total=produtos_t1[0].preco * 2,
                forma_pagamento="dinheiro",
                emitir_nota=True,
                tenant_id=tenant1_id,
                vendedor_id=admin1.id
            )
        ]
        db.add_all(vendas_t1)
        
        # 6. Populate Tenant 2 (Clínica Vida) with different data
        print("📊 Populando dados da Clínica Vida...")
        
        # Clientes for Tenant 2 (Different from Tenant 1)
        clientes_t2 = [
            Cliente(
                id=uuid.uuid4(),
                nome="Pedro Oliveira",
                email="pedro@email.com",
                telefone="(21) 88888-1111",
                cpf_cnpj="111.222.333-44",
                endereco="Rua D, 321 - Rio de Janeiro",
                tenant_id=tenant2_id
            ),
            Cliente(
                id=uuid.uuid4(),
                nome="Lucia Fernandes",
                email="lucia@email.com",
                telefone="(21) 88888-2222",
                cpf_cnpj="555.666.777-88",
                endereco="Rua E, 654 - Rio de Janeiro",
                tenant_id=tenant2_id
            )
        ]
        db.add_all(clientes_t2)
        
        # Produtos for Tenant 2 (Medical supplies)
        produtos_t2 = [
            Produto(
                id=uuid.uuid4(),
                codigo="MED001",
                nome="Termômetro Digital",
                descricao="Termômetro digital de precisão",
                categoria="Equipamentos",
                preco=45.00,
                custo=25.00,
                estoque_atual=10,
                estoque_minimo=2,
                tenant_id=tenant2_id
            ),
            Produto(
                id=uuid.uuid4(),
                codigo="MED002",
                nome="Estetoscópio",
                descricao="Estetoscópio profissional",
                categoria="Equipamentos",
                preco=180.00,
                custo=95.00,
                estoque_atual=5,
                estoque_minimo=1,
                tenant_id=tenant2_id
            )
        ]
        db.add_all(produtos_t2)
        
        # Serviços for Tenant 2 (Medical services)
        servicos_t2 = [
            Servico(
                id=uuid.uuid4(),
                nome="Consulta Clínica Geral",
                descricao="Consulta médica completa",
                duracao_minutos=30,
                preco=150.00,
                tributacao_iss=json.dumps({"aliquota": 2.0, "codigo_servico_municipal": "04.01"}),
                tenant_id=tenant2_id
            ),
            Servico(
                id=uuid.uuid4(),
                nome="Exame de Rotina",
                descricao="Exames laboratoriais básicos",
                duracao_minutos=15,
                preco=80.00,
                tributacao_iss=json.dumps({"aliquota": 2.0, "codigo_servico_municipal": "04.02"}),
                tenant_id=tenant2_id
            )
        ]
        db.add_all(servicos_t2)
        
        db.commit()
        print("✅ Dados populados para ambos os tenants")
        
        print("\n🎉 Sistema SaaS Multi-tenant criado com sucesso!")
        print("\n📋 CREDENCIAIS DE ACESSO:")
        print("\n🔧 SUPER ADMIN (Gerencia todo o sistema):")
        print("   Email: admin@sistema.com")
        print("   Senha: admin123")
        print("   Pode ver todos os tenants e suspender contas")
        
        print("\n🏢 TENANT 1 - SALÃO BELLA (Ativo - Premium):")
        print("   Subdomínio: salao-bella")
        print("   Email: admin@salaobella.com")
        print("   Senha: bella123")
        print("   Status: Ativo com plano Premium")
        
        print("\n🏥 TENANT 2 - CLÍNICA VIDA (Trial - Basic):")
        print("   Subdomínio: clinica-vida")
        print("   Email: admin@clinicavida.com")
        print("   Senha: vida123")
        print("   Status: Trial (15 dias restantes)")
        
        print("\n❌ TENANT 3 - LOJA SUSPENSA (Inativo):")
        print("   Subdomínio: loja-suspensa")
        print("   Email: admin@suspensa.com")
        print("   Senha: suspensa123")
        print("   Status: Conta Suspensa (para teste)")
        
        print("\n🌐 URL de Acesso: https://enterprise-hub-50.preview.emergentagent.com")
        print("\n💡 FUNCIONALIDADES TESTÁVEIS:")
        print("   ✅ Isolamento total entre tenants")
        print("   ✅ Super admin pode gerenciar todos")
        print("   ✅ Sistema de trial e planos")
        print("   ✅ Suspensão de contas")
        print("   ✅ Email de boas-vindas e reset senha")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_saas_data()