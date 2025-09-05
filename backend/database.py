# database.py — FIX FINAL (sem SAWarning e compatível com PT-BR env)
# Mudanças chave:
# - Usa URL_DO_BANCO_DE_DADOS (fallback DATABASE_URL)
# - Par de relacionamentos Tenant.vencimentos <-> Vencimento.tenant com back_populates
# - overlaps nas DUAS pontas (extra seguro)
# - UUID default correto para Postgres/SQLite
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Float, Integer, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timezone
import uuid, os
from typing import Generator

def get_env_any(names, default=None):
    for n in names:
        v = os.environ.get(n)
        if v is not None and str(v).strip() != "":
            return v
    return default

DATABASE_URL = get_env_any(['URL_DO_BANCO_DE_DADOS','DATABASE_URL'])
if not DATABASE_URL:
    raise ValueError("Defina URL_DO_BANCO_DE_DADOS (ou DATABASE_URL)")

is_sqlite = str(DATABASE_URL).startswith('sqlite')

if is_sqlite:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={'check_same_thread': False})
    IdType = String(36)
    default_id = lambda: str(uuid.uuid4())
elif DATABASE_URL.startswith('postgresql://') or DATABASE_URL.startswith('postgresql+psycopg2://'):
    from sqlalchemy.dialects.postgresql import UUID
    if DATABASE_URL.startswith('postgresql://'):
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    IdType = UUID(as_uuid=True)
    default_id = uuid.uuid4
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    IdType = String(36)
    default_id = lambda: str(uuid.uuid4())

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -------------------- MODELOS --------------------
class Tenant(Base):
    __tablename__ = 'tenants'
    id = Column(IdType, primary_key=True, default=default_id)
    subdomain = Column(String(50), unique=True, nullable=False, index=True)
    company_name = Column(String(200), nullable=False)
    cnpj = Column(String(20), unique=True)
    razao_social = Column(String(200))
    nome_fantasia = Column(String(200))
    endereco = Column(Text)
    telefone = Column(String(20))
    email = Column(String(100))
    plan = Column(String(20), default='basic')
    is_active = Column(Boolean, default=True)
    trial_ends_at = Column(DateTime(timezone=True))
    subscription_status = Column(String(20), default='trial')
    stripe_customer_id = Column(String(100))
    usar_certificado = Column(Boolean, default=False)
    certificado_config = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    users = relationship('User', back_populates='tenant', cascade='all, delete-orphan')
    clientes = relationship('Cliente', back_populates='tenant', cascade='all, delete-orphan')
    produtos = relationship('Produto', back_populates='tenant', cascade='all, delete-orphan')
    servicos = relationship('Servico', back_populates='tenant', cascade='all, delete-orphan')
    vendas = relationship('Venda', back_populates='tenant', cascade='all, delete-orphan')
    agendamentos = relationship('Agendamento', back_populates='tenant', cascade='all, delete-orphan')
    # overlaps aqui é extra‑segurança: informa ao ORM que compartilha colunas com Vencimento.tenant
    vencimentos = relationship('Vencimento', back_populates='tenant', cascade='all, delete-orphan', overlaps="tenant")

class User(Base):
    __tablename__ = 'users'
    id = Column(IdType, primary_key=True, default=default_id)
    email = Column(String(100), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default='operador')
    is_active = Column(Boolean, default=True)
    tenant_id = Column(IdType, ForeignKey('tenants.id'), nullable=True)
    reset_token = Column(String(200))
    reset_token_expires = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    tenant = relationship('Tenant', back_populates='users')
    vendas = relationship('Venda', back_populates='vendedor')
    __table_args__ = (Index('idx_user_email_tenant', 'email', 'tenant_id', unique=True),)

class Cliente(Base):
    __tablename__ = 'clientes'
    id = Column(IdType, primary_key=True, default=default_id)
    nome = Column(String(200), nullable=False)
    email = Column(String(100))
    telefone = Column(String(20))
    cpf_cnpj = Column(String(20))
    endereco = Column(Text)
    foto_url = Column(String(500))
    anamnese = Column(Text)
    tenant_id = Column(IdType, ForeignKey('tenants.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    tenant = relationship('Tenant', back_populates='clientes')
    vendas = relationship('Venda', back_populates='cliente')
    agendamentos = relationship('Agendamento', back_populates='cliente')

class Produto(Base):
    __tablename__ = 'produtos'
    id = Column(IdType, primary_key=True, default=default_id)
    codigo = Column(String(50))
    nome = Column(String(200), nullable=False)
    descricao = Column(Text)
    categoria = Column(String(100))
    ncm = Column(String(20))
    custo = Column(Float, default=0.0)
    preco = Column(Float, nullable=False)
    estoque_atual = Column(Integer, default=0)
    estoque_minimo = Column(Integer, default=0)
    tenant_id = Column(IdType, ForeignKey('tenants.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    tenant = relationship('Tenant', back_populates='produtos')

class Servico(Base):
    __tablename__ = 'servicos'
    id = Column(IdType, primary_key=True, default=default_id)
    nome = Column(String(200), nullable=False)
    descricao = Column(Text)
    duracao_minutos = Column(Integer, default=60)
    preco = Column(Float, nullable=False)
    tributacao_iss = Column(Text)
    tenant_id = Column(IdType, ForeignKey('tenants.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    tenant = relationship('Tenant', back_populates='servicos')

class Venda(Base):
    __tablename__ = 'vendas'
    id = Column(IdType, primary_key=True, default=default_id)
    cliente_id = Column(IdType, ForeignKey('clientes.id'))
    cliente_nome = Column(String(200))
    itens = Column(Text, nullable=False)
    subtotal = Column(Float, nullable=False)
    desconto_total = Column(Float, default=0.0)
    total = Column(Float, nullable=False)
    forma_pagamento = Column(String(50), nullable=False)
    emitir_nota = Column(Boolean, default=False)
    status_nota = Column(String(50))
    nota_numero = Column(String(100))
    nota_xml = Column(Text)
    nota_pdf_url = Column(String(500))
    tenant_id = Column(IdType, ForeignKey('tenants.id'), nullable=False)
    vendedor_id = Column(IdType, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    tenant = relationship('Tenant', back_populates='vendas')
    cliente = relationship('Cliente', back_populates='vendas')
    vendedor = relationship('User', back_populates='vendas')

class Agendamento(Base):
    __tablename__ = 'agendamentos'
    id = Column(IdType, primary_key=True, default=default_id)
    cliente_id = Column(IdType, ForeignKey('clientes.id'), nullable=False)
    servico_id = Column(IdType, ForeignKey('servicos.id'), nullable=False)
    data_hora = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default='agendado')
    observacoes = Column(Text)
    tenant_id = Column(IdType, ForeignKey('tenants.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    tenant = relationship('Tenant', back_populates='agendamentos')
    cliente = relationship('Cliente', back_populates='agendamentos')
    servico = relationship('Servico')

class Vencimento(Base):
    __tablename__ = 'vencimentos'
    id = Column(IdType, primary_key=True, default=default_id)
    tenant_id = Column(IdType, ForeignKey('tenants.id'), nullable=False, index=True)
    descricao = Column(String(255))
    valor = Column(Float, default=0.0)
    data_vencimento = Column(DateTime(timezone=True))
    pago = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # back_populates + overlaps = sem SAWarning
    tenant = relationship('Tenant', back_populates='vencimentos', overlaps="vencimentos")

# -------------------- DEPENDÊNCIA & DDL --------------------
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(bind=engine)
