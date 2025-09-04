from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Float, Integer, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
import os
from typing import Generator

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Handle SQLite and PostgreSQL
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"check_same_thread": False})
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subdomain = Column(String(50), unique=True, nullable=False, index=True)
    company_name = Column(String(200), nullable=False)
    cnpj = Column(String(20), unique=True)
    razao_social = Column(String(200))
    nome_fantasia = Column(String(200))
    endereco = Column(Text)
    telefone = Column(String(20))
    email = Column(String(100))
    
    # SaaS Configuration
    plan = Column(String(20), default="basic")  # basic, premium, enterprise
    is_active = Column(Boolean, default=True)
    trial_ends_at = Column(DateTime(timezone=True))
    subscription_status = Column(String(20), default="trial")  # trial, active, suspended, cancelled
    stripe_customer_id = Column(String(100))
    
    # Certificate configuration
    usar_certificado = Column(Boolean, default=False)
    certificado_config = Column(Text)  # JSON string
    
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    clientes = relationship("Cliente", back_populates="tenant", cascade="all, delete-orphan")
    produtos = relationship("Produto", back_populates="tenant", cascade="all, delete-orphan")
    servicos = relationship("Servico", back_populates="tenant", cascade="all, delete-orphan")
    vendas = relationship("Venda", back_populates="tenant", cascade="all, delete-orphan")
    agendamentos = relationship("Agendamento", back_populates="tenant", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(100), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default="operador")  # super_admin, admin_empresa, operador
    is_active = Column(Boolean, default=True)
    
    # Multi-tenant
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)  # Null for super_admin
    
    # Password reset
    reset_token = Column(String(200))
    reset_token_expires = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    vendas = relationship("Venda", back_populates="vendedor")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email_tenant', 'email', 'tenant_id', unique=True),
    )

class Cliente(Base):
    __tablename__ = "clientes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(200), nullable=False)
    email = Column(String(100))
    telefone = Column(String(20))
    cpf_cnpj = Column(String(20))
    endereco = Column(Text)
    foto_url = Column(String(500))
    anamnese = Column(Text)
    
    # Multi-tenant
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship("Tenant", back_populates="clientes")
    vendas = relationship("Venda", back_populates="cliente")
    agendamentos = relationship("Agendamento", back_populates="cliente")

class Produto(Base):
    __tablename__ = "produtos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo = Column(String(50))
    nome = Column(String(200), nullable=False)
    descricao = Column(Text)
    categoria = Column(String(100))
    ncm = Column(String(20))
    custo = Column(Float, default=0.0)
    preco = Column(Float, nullable=False)
    estoque_atual = Column(Integer, default=0)
    estoque_minimo = Column(Integer, default=0)
    
    # Multi-tenant
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship("Tenant", back_populates="produtos")

class Servico(Base):
    __tablename__ = "servicos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(200), nullable=False)
    descricao = Column(Text)
    duracao_minutos = Column(Integer, default=60)
    preco = Column(Float, nullable=False)
    tributacao_iss = Column(Text)  # JSON string
    
    # Multi-tenant
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship("Tenant", back_populates="servicos")

class Venda(Base):
    __tablename__ = "vendas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"))
    cliente_nome = Column(String(200))
    itens = Column(Text, nullable=False)  # JSON string
    subtotal = Column(Float, nullable=False)
    desconto_total = Column(Float, default=0.0)
    total = Column(Float, nullable=False)
    forma_pagamento = Column(String(50), nullable=False)
    emitir_nota = Column(Boolean, default=False)
    status_nota = Column(String(50))
    nota_numero = Column(String(100))
    nota_xml = Column(Text)
    nota_pdf_url = Column(String(500))
    
    # Multi-tenant
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    vendedor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship("Tenant", back_populates="vendas")
    cliente = relationship("Cliente", back_populates="vendas")
    vendedor = relationship("User", back_populates="vendas")

class Agendamento(Base):
    __tablename__ = "agendamentos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False)
    servico_id = Column(UUID(as_uuid=True), ForeignKey("servicos.id"), nullable=False)
    data_hora = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default="agendado")  # agendado, confirmado, realizado, cancelado
    observacoes = Column(Text)
    
    # Multi-tenant
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship("Tenant", back_populates="agendamentos")
    cliente = relationship("Cliente", back_populates="agendamentos")
    servico = relationship("Servico")

# Database dependency
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)