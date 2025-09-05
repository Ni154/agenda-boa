from sqlalchemy import (
    create_engine, Column, String, DateTime, Boolean, Float, Integer, Text,
    ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timezone
import uuid
import os
from typing import Generator

# -------------------------------------------------------------------
# Config DB
# -------------------------------------------------------------------
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Detecta SQLite x Postgres
is_sqlite = DATABASE_URL.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False}
    )
    IdType = String(36)  # SQLite não tem UUID nativo
elif DATABASE_URL.startswith("postgresql://"):
    from sqlalchemy.dialects.postgresql import UUID
    # força driver psycopg2 (Railway costuma usar)
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    IdType = UUID(as_uuid=True)
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    IdType = String(36)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def gen_id():
    # usando string funciona para ambos (Postgres aceita cast implícito)
    return str(uuid.uuid4())


# -------------------------------------------------------------------
# MODELOS
# -------------------------------------------------------------------
class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(IdType, primary_key=True, default=gen_id)
    subdomain = Column(String(50), unique=True, nullable=False, index=True)
    company_name = Column(String(200), nullable=False)
    cnpj = Column(String(20), unique=True)
    razao_social = Column(String(200))
    nome_fantasia = Column(String(200))
    endereco = Column(Text)
    telefone = Column(String(20))
    email = Column(String(100))

    # SaaS
    plan = Column(String(20), default="basic")  # basic, premium, enterprise
    is_active = Column(Boolean, default=True)
    trial_ends_at = Column(DateTime(timezone=True))
    subscription_status = Column(String(20), default="trial")  # trial, active, suspended, cancelled
    stripe_customer_id = Column(String(100))

    # Certificado
    usar_certificado = Column(Boolean, default=False)
    certificado_config = Column(Text)  # JSON string

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relacionamentos
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    clientes = relationship("Cliente", back_populates="tenant", cascade="all, delete-orphan")
    produtos = relationship("Produto", back_populates="tenant", cascade="all, delete-orphan")
    servicos = relationship("Servico", back_populates="tenant", cascade="all, delete-orphan")
    vendas = relationship("Venda", back_populates="tenant", cascade="all, delete-orphan")
    agendamentos = relationship("Agendamento", back_populates="tenant", cascade="all, delete-orphan")

    # Pareado com Vencimento.tenant
    vencimentos = relationship("Vencimento", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(IdType, primary_key=True, default=gen_id)
    email = Column(String(100), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default="operador")  # super_admin, admin_empresa, operador
    is_active = Column(Boolean, default=True)

    tenant_id = Column(IdType, ForeignKey("tenants.id"), nullable=True)  # Null para super_admin

    reset_token = Column(String(200))
    reset_token_expires = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="users")
    vendas = relationship("Venda", back_populates="vendedor")

    __table_args__ = (
        Index('idx_user_email_tenant', 'email', 'tenant_id', unique=True),
    )


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(IdType, primary_key=True, default=gen_id)
    nome = Column(String(200), nullable=False)
    email = Column(String(100))
    telefone = Column(String(20))
    cpf_cnpj = Column(String(20))
    endereco = Column(Text)
    foto_url = Column(String(500))
    anamnese = Column(Text)

    tenant_id = Column(IdType, ForeignKey("tenants.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="clientes")
    vendas = relationship("Venda", back_populates="cliente")
    agendamentos = relationship("Agendamento", back_populates="cliente")


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(IdType, primary_key=True, default=gen_id)
    codigo = Column(String(50))
    nome = Column(String(200), nullable=False)
    descricao = Column(Text)
    categoria = Column(String(100))
    ncm = Column(String(20))
    custo = Column(Float, default=0.0)
    preco = Column(Float, nullable=False)
    estoque_atual = Column(Integer, default=0)
    estoque_minimo = Column(Integer, default=0)

    tenant_id = Column(IdType, ForeignKey("tenants.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="produtos")


class Servico(Base):
    __tablename__ = "servicos"

    id = Column(IdType, primary_key=True, default=gen_id)
    nome = Column(String(200), nullable=False)
    descricao = Column(Text)
    duracao_minutos = Column(Integer, default=60)
    preco = Column(Float, nullable=False)
    tributacao_iss = Column(Text)  # JSON string

    tenant_id = Column(IdType, ForeignKey("tenants.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="servicos")


class Venda(Base):
    __tablename__ = "vendas"

    id = Column(IdType, primary_key=True, default=gen_id)
    cliente_id = Column(IdType, ForeignKey("clientes.id"))
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

    tenant_id = Column(IdType, ForeignKey("tenants.id"), nullable=False)
    vendedor_id = Column(IdType, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="vendas")
    cliente = relationship("Cliente", back_populates="vendas")
    vendedor = relationship("User", back_populates="vendas")


class Agendamento(Base):
    __tablename__ = "agendamentos"

    id = Column(IdType, primary_key=True, default=gen_id)
    cliente_id = Column(IdType, ForeignKey("clientes.id"), nullable=False)
    servico_id = Column(IdType, ForeignKey("servicos.id"), nullable=False)
    data_hora = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default="agendado")  # agendado, confirmado, realizado, cancelado
    observacoes = Column(Text)

    tenant_id = Column(IdType, ForeignKey("tenants.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="agendamentos")
    cliente = relationship("Cliente", back_populates="agendamentos")
    servico = relationship("Servico")


# 👇 Modelo Vencimento com pareamento e overlaps para silenciar o warning
class Vencimento(Base):
    __tablename__ = "vencimentos"

    id = Column(IdType, primary_key=True, default=gen_id)
    tenant_id = Column(IdType, ForeignKey("tenants.id"), nullable=False, index=True)

    descricao = Column(String(255))
    valor = Column(Float, default=0.0)
    data_vencimento = Column(DateTime(timezone=True))
    pago = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # O log pede para colocar overlaps="vencimentos" AQUI
    tenant = relationship(
        "Tenant",
        back_populates="vencimentos",
        overlaps="vencimentos"
    )


# -------------------------------------------------------------------
# Dependência DB
# -------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------------------------
# Create tables
# -------------------------------------------------------------------
def create_tables():
    Base.metadata.create_all(bind=engine)
