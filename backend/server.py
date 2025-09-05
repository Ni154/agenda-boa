# server.py
# FastAPI backend para ERP SaaS (multi-tenant)
# Compatível com o database.py que você enviou (Tenant, User, Cliente, Produto, Servico, Venda, Agendamento)

from __future__ import annotations

import os
import uuid
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Generator, List, Optional

# ----- Dependências FastAPI / Pydantic / Segurança
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

# ----- Autenticação
from jose import JWTError, jwt
from passlib.context import CryptContext

# ----- Variáveis de ambiente (.env local opcional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ----- Banco de dados (import flexível: pacote ou arquivo lado a lado)
try:
    # quando server.py está dentro de um pacote junto com database.py
    from .database import (  # type: ignore
        get_db,
        create_tables,
        SessionLocal,
        Tenant,
        User,
        Cliente,
        Produto,
        Servico,
        Venda,
        Agendamento,
    )
except Exception:
    # quando server.py está na raiz, ao lado de database.py
    from database import (  # type: ignore
        get_db,
        create_tables,
        SessionLocal,
        Tenant,
        User,
        Cliente,
        Produto,
        Servico,
        Venda,
        Agendamento,
    )

# ----- Email (Resend opcional)
try:
    import resend  # type: ignore
except Exception:
    resend = None  # biblioteca ausente é aceitável

# -----------------------------------------------------------------------------
# Configurações
# -----------------------------------------------------------------------------
APP_NAME = "ERP SaaS - Sistema de Gestão Empresarial"

JWT_SECRET = os.environ.get("JWT_SECRET", "troque-esta-chave")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_FROM = os.environ.get("RESEND_FROM", "ERP Sistema <noreply@sistema.com>")

if resend and RESEND_API_KEY:
    try:
        resend.api_key = RESEND_API_KEY
    except Exception:
        pass

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# -----------------------------------------------------------------------------
# Aplicação
# -----------------------------------------------------------------------------
app = FastAPI(title=APP_NAME, version="2.0.0")
api = APIRouter(prefix="/api")

# CORS
_raw_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "*")
if _raw_origins.strip() == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Schemas (Pydantic)
# -----------------------------------------------------------------------------
class UserRole:
    SUPER_ADMIN = "super_admin"
    ADMIN_EMPRESA = "admin_empresa"
    OPERADOR = "operador"


class TenantCreate(BaseModel):
    subdomain: str = Field(..., min_length=3, max_length=50)
    company_name: str = Field(..., min_length=1, max_length=200)
    cnpj: Optional[str] = None
    razao_social: Optional[str] = None
    admin_name: str = Field(..., min_length=1, max_length=100)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=6)
    plan: str = Field(default="basic")


class TenantResponse(BaseModel):
    id: str
    subdomain: str
    company_name: str
    cnpj: Optional[str]
    is_active: bool
    plan: str
    subscription_status: str
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str = UserRole.OPERADOR


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    subdomain: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    tenant_id: Optional[str]
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class PasswordResetRequest(BaseModel):
    email: EmailStr
    subdomain: Optional[str] = None


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


class ClienteCreate(BaseModel):
    nome: str
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    endereco: Optional[str] = None
    anamnese: Optional[str] = None


class ClienteResponse(BaseModel):
    id: str
    nome: str
    email: Optional[str]
    telefone: Optional[str]
    cpf_cnpj: Optional[str]
    endereco: Optional[str]
    foto_url: Optional[str]
    anamnese: Optional[str]
    created_at: datetime


class ProdutoCreate(BaseModel):
    codigo: Optional[str] = None
    nome: str
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    ncm: Optional[str] = None
    custo: float = 0.0
    preco: float
    estoque_atual: int = 0
    estoque_minimo: int = 0


class ProdutoResponse(BaseModel):
    id: str
    codigo: Optional[str]
    nome: str
    descricao: Optional[str]
    categoria: Optional[str]
    ncm: Optional[str]
    custo: float
    preco: float
    estoque_atual: int
    estoque_minimo: int
    created_at: datetime


class ServicoCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    duracao_minutos: int = 60
    preco: float
    tributacao_iss: Optional[Dict[str, Any]] = None


class ServicoResponse(BaseModel):
    id: str
    nome: str
    descricao: Optional[str]
    duracao_minutos: int
    preco: float
    tributacao_iss: Optional[Dict[str, Any]]
    created_at: datetime


class ItemVenda(BaseModel):
    tipo: str  # "produto" ou "servico"
    item_id: str
    nome: str
    quantidade: float
    preco_unitario: float
    desconto: float = 0.0
    total: float


class VendaCreate(BaseModel):
    cliente_id: Optional[str] = None
    cliente_nome: Optional[str] = None
    itens: List[ItemVenda]
    forma_pagamento: str
    emitir_nota: bool = False


class VendaResponse(BaseModel):
    id: str
    cliente_id: Optional[str]
    cliente_nome: Optional[str]
    itens: List[ItemVenda]
    subtotal: float
    desconto_total: float
    total: float
    forma_pagamento: str
    emitir_nota: bool
    status_nota: Optional[str]
    created_at: datetime


class AgendamentoCreate(BaseModel):
    cliente_id: str
    servico_id: str
    data_hora: datetime
    status: str = "agendado"
    observacoes: Optional[str] = None


class AgendamentoResponse(BaseModel):
    id: str
    cliente_id: str
    servico_id: str
    data_hora: datetime
    status: str
    observacoes: Optional[str]
    created_at: datetime


class Dashboard(BaseModel):
    total_vendas: float
    total_despesas: float
    lucro: float
    margem_lucro: float
    itens_estoque: int
    agendamentos_hoje: int
    vendas_periodo: List[Dict[str, Any]]
    top_produtos: List[Dict[str, Any]]


class SuperAdminDashboard(BaseModel):
    total_tenants: int
    active_tenants: int
    trial_tenants: int
    suspended_tenants: int
    total_users: int
    monthly_revenue: float
    recent_signups: List[Dict[str, Any]]

# -----------------------------------------------------------------------------
# Helpers de autenticação
# -----------------------------------------------------------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Envia email via Resend se configurado; caso contrário, simula no log."""
    if not (resend and RESEND_API_KEY):
        logging.info("[EMAIL SIMULADO] To=%s | Subject=%s", to_email, subject)
        return True
    try:
        resend.Emails.send(
            {
                "from": RESEND_FROM,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }
        )
        return True
    except Exception as e:
        logging.exception("Erro enviando email: %s", e)
        return False

# -----------------------------------------------------------------------------
# Dependências
# -----------------------------------------------------------------------------
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuário inativo")
    return user


async def get_current_tenant(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
) -> Optional[Tenant]:
    if current_user.role == UserRole.SUPER_ADMIN:
        return None
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="Usuário sem tenant")
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    if not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant suspenso")
    return tenant

# -----------------------------------------------------------------------------
# Health & favicon
# -----------------------------------------------------------------------------
@app.get("/health")
def health_root():
    return {"status": "ok", "name": APP_NAME}

@api.get("/health")
def health_api():
    return {"status": "ok", "name": APP_NAME}

@app.get("/favicon.ico")
def favicon():
    # evita 404 no favicon
    return Response(status_code=204)

# -----------------------------------------------------------------------------
# Rotas: Autenticação
# -----------------------------------------------------------------------------
@api.post("/auth/login", response_model=Token)
def login(user_credentials: UserLogin, db=Depends(get_db)):
    query = db.query(User).filter(User.email == user_credentials.email)

    if user_credentials.subdomain:
        tenant = db.query(Tenant).filter(Tenant.subdomain == user_credentials.subdomain).first()
        if not tenant:
            raise HTTPException(status_code=400, detail="Subdomínio inválido")
        query = query.filter(User.tenant_id == tenant.id)
    else:
        query = query.filter(User.tenant_id.is_(None))

    user = query.first()
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuário inativo")

    if user.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if not tenant or not tenant.is_active:
            raise HTTPException(status_code=403, detail="Conta suspensa")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)

    user_resp = UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        is_active=user.is_active,
    )
    return Token(access_token=access_token, token_type="bearer", user=user_resp)


@api.post("/auth/forgot-password")
def forgot_password(req: PasswordResetRequest, db=Depends(get_db)):
    query = db.query(User).filter(User.email == req.email)
    if req.subdomain:
        tenant = db.query(Tenant).filter(Tenant.subdomain == req.subdomain).first()
        if tenant:
            query = query.filter(User.tenant_id == tenant.id)

    user = query.first()
    if not user:
        # não revela existência
        return {"message": "Se o email existir, enviaremos um link de redefinição"}

    token = generate_reset_token()
    user.reset_token = token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()

    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    html = f"""
        <h1>Redefinição de senha</h1>
        <p>Olá {user.name},</p>
        <p><a href="{reset_url}">Clique aqui para redefinir sua senha</a></p>
        <p>Link expira em 1 hora.</p>
    """
    send_email(user.email, "Redefinir senha - ERP Sistema", html)
    return {"message": "Se o email existir, enviaremos um link de redefinição"}


@api.post("/auth/reset-password")
def reset_password(req: PasswordReset, db=Depends(get_db)):
    user = (
        db.query(User)
        .filter(
            User.reset_token == req.token,
            User.reset_token_expires > datetime.now(timezone.utc),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
    user.hashed_password = get_password_hash(req.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return {"message": "Senha alterada com sucesso"}


@api.get("/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        tenant_id=str(current_user.tenant_id) if current_user.tenant_id else None,
        is_active=current_user.is_active,
    )

# -----------------------------------------------------------------------------
# Rotas: Super Admin - Tenants
# -----------------------------------------------------------------------------
@api.post("/super-admin/tenants", response_model=TenantResponse)
def create_tenant_endpoint(
    tenant_data: TenantCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Apenas super admin")

    if db.query(Tenant).filter(Tenant.subdomain == tenant_data.subdomain).first():
        raise HTTPException(status_code=400, detail="Subdomínio já existe")

    tenant = Tenant(
        subdomain=tenant_data.subdomain,
        company_name=tenant_data.company_name,
        cnpj=tenant_data.cnpj,
        razao_social=tenant_data.razao_social,
        plan=tenant_data.plan,
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(tenant)
    db.flush()

    admin_user = User(
        email=tenant_data.admin_email,
        name=tenant_data.admin_name,
        hashed_password=get_password_hash(tenant_data.admin_password),
        role=UserRole.ADMIN_EMPRESA,
        tenant_id=tenant.id,
    )
    db.add(admin_user)
    db.commit()

    # Email de boas-vindas (opcional)
    html = f"""
        <h1>Bem-vindo ao ERP Sistema!</h1>
        <p>Subdomínio: <b>{tenant_data.subdomain}</b></p>
        <p>Email: <b>{tenant_data.admin_email}</b></p>
        <p>Acesse: <a href="{FRONTEND_URL}">{FRONTEND_URL}</a></p>
        <p>Seu trial expira em 30 dias.</p>
    """
    send_email(tenant_data.admin_email, "Bem-vindo ao ERP Sistema", html)

    return TenantResponse(
        id=str(tenant.id),
        subdomain=tenant.subdomain,
        company_name=tenant.company_name,
        cnpj=tenant.cnpj,
        is_active=tenant.is_active,
        plan=tenant.plan,
        subscription_status=tenant.subscription_status,
        created_at=tenant.created_at,
    )


@api.get("/super-admin/tenants", response_model=List[TenantResponse])
def list_tenants(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Apenas super admin")
    tenants = db.query(Tenant).all()
    return [
        TenantResponse(
            id=str(t.id),
            subdomain=t.subdomain,
            company_name=t.company_name,
            cnpj=t.cnpj,
            is_active=t.is_active,
            plan=t.plan,
            subscription_status=t.subscription_status,
            created_at=t.created_at,
        )
        for t in tenants
    ]


@api.put("/super-admin/tenants/{tenant_id}/toggle-status")
def toggle_tenant(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Apenas super admin")
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    tenant.is_active = not tenant.is_active
    tenant.subscription_status = "active" if tenant.is_active else "suspended"
    db.commit()
    return {"message": f"Tenant {'ativado' if tenant.is_active else 'suspenso'} com sucesso"}

# -----------------------------------------------------------------------------
# Rotas: Dashboard
# -----------------------------------------------------------------------------
@api.get("/dashboard", response_model=Dashboard)
def dashboard(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    if current_user.role == UserRole.SUPER_ADMIN:
        # Super Admin recebe agregados fictícios ou implementar sua própria agregação
        total_tenants = db.query(Tenant).count()
        active_tenants = db.query(Tenant).filter(Tenant.is_active.is_(True)).count()
        trial_tenants = db.query(Tenant).filter(Tenant.subscription_status == "trial").count()
        suspended_tenants = db.query(Tenant).filter(Tenant.is_active.is_(False)).count()
        total_users = db.query(User).filter(User.role != UserRole.SUPER_ADMIN).count()
        recent = (
            db.query(Tenant)
            .order_by(Tenant.created_at.desc())
            .limit(5)
            .all()
        )
        recent_signups = [
            {
                "company_name": t.company_name,
                "subdomain": t.subdomain,
                "created_at": t.created_at.isoformat(),
                "plan": t.plan,
            }
            for t in recent
        ]
        # converte para o modelo Dashboard para reaproveitar front (valores placeholders)
        return Dashboard(
            total_vendas=float(total_tenants),
            total_despesas=0.0,
            lucro=float(active_tenants),
            margem_lucro=0.0,
            itens_estoque=total_users,
            agendamentos_hoje=trial_tenants + suspended_tenants,
            vendas_periodo=[],
            top_produtos=[],
        )

    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="Usuário sem tenant")

    tenant_id = current_user.tenant_id
    vendas = db.query(Venda).filter(Venda.tenant_id == tenant_id).all()
    produtos = db.query(Produto).filter(Produto.tenant_id == tenant_id).all()

    total_vendas = float(sum(v.total for v in vendas))
    total_despesas = 0.0
    lucro = total_vendas - total_despesas
    margem = (lucro / total_vendas * 100.0) if total_vendas > 0 else 0.0
    itens_estoque = int(sum(p.estoque_atual for p in produtos))

    # dados de exemplo
    vendas_periodo = [
        {"data": "2024-09-01", "valor": 1000},
        {"data": "2024-09-02", "valor": 1500},
        {"data": "2024-09-03", "valor": 2000},
    ]
    top_produtos = [
        {"nome": "Produto A", "vendas": 50},
        {"nome": "Produto B", "vendas": 30},
        {"nome": "Produto C", "vendas": 20},
    ]

    return Dashboard(
        total_vendas=total_vendas,
        total_despesas=total_despesas,
        lucro=lucro,
        margem_lucro=margem,
        itens_estoque=itens_estoque,
        agendamentos_hoje=0,
        vendas_periodo=vendas_periodo,
        top_produtos=top_produtos,
    )

# -----------------------------------------------------------------------------
# Rotas: Clientes
# -----------------------------------------------------------------------------
@api.post("/clientes", response_model=ClienteResponse)
def create_cliente(
    payload: ClienteCreate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db=Depends(get_db),
):
    cliente = Cliente(**payload.dict(), tenant_id=tenant.id)
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return ClienteResponse(
        id=str(cliente.id),
        nome=cliente.nome,
        email=cliente.email,
        telefone=cliente.telefone,
        cpf_cnpj=cliente.cpf_cnpj,
        endereco=cliente.endereco,
        foto_url=cliente.foto_url,
        anamnese=cliente.anamnese,
        created_at=cliente.created_at,
    )


@api.get("/clientes", response_model=List[ClienteResponse])
def list_clientes(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db=Depends(get_db),
):
    items = db.query(Cliente).filter(Cliente.tenant_id == tenant.id).all()
    return [
        ClienteResponse(
            id=str(c.id),
            nome=c.nome,
            email=c.email,
            telefone=c.telefone,
            cpf_cnpj=c.cpf_cnpj,
            endereco=c.endereco,
            foto_url=c.foto_url,
            anamnese=c.anamnese,
            created_at=c.created_at,
        )
        for c in items
    ]

# -----------------------------------------------------------------------------
# Rotas: Produtos
# -----------------------------------------------------------------------------
@api.post("/produtos", response_model=ProdutoResponse)
def create_produto(
    payload: ProdutoCreate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db=Depends(get_db),
):
    produto = Produto(**payload.dict(), tenant_id=tenant.id)
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return ProdutoResponse(
        id=str(produto.id),
        codigo=produto.codigo,
        nome=produto.nome,
        descricao=produto.descricao,
        categoria=produto.categoria,
        ncm=produto.ncm,
        custo=produto.custo,
        preco=produto.preco,
        estoque_atual=produto.estoque_atual,
        estoque_minimo=produto.estoque_minimo,
        created_at=produto.created_at,
    )


@api.get("/produtos", response_model=List[ProdutoResponse])
def list_produtos(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db=Depends(get_db),
):
    items = db.query(Produto).filter(Produto.tenant_id == tenant.id).all()
    return [
        ProdutoResponse(
            id=str(p.id),
            codigo=p.codigo,
            nome=p.nome,
            descricao=p.descricao,
            categoria=p.categoria,
            ncm=p.ncm,
            custo=p.custo,
            preco=p.preco,
            estoque_atual=p.estoque_atual,
            estoque_minimo=p.estoque_minimo,
            created_at=p.created_at,
        )
        for p in items
    ]

# -----------------------------------------------------------------------------
# Rotas: Serviços
# -----------------------------------------------------------------------------
@api.post("/servicos", response_model=ServicoResponse)
def create_servico(
    payload: ServicoCreate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db=Depends(get_db),
):
    data = payload.dict()
    if data.get("tributacao_iss") is not None:
        data["tributacao_iss"] = json.dumps(data["tributacao_iss"])
    servico = Servico(**data, tenant_id=tenant.id)
    db.add(servico)
    db.commit()
    db.refresh(servico)

    tributacao = None
    if servico.tributacao_iss:
        try:
            tributacao = json.loads(servico.tributacao_iss)
        except Exception:
            pass

    return ServicoResponse(
        id=str(servico.id),
        nome=servico.nome,
        descricao=servico.descricao,
        duracao_minutos=servico.duracao_minutos,
        preco=servico.preco,
        tributacao_iss=tributacao,
        created_at=servico.created_at,
    )


@api.get("/servicos", response_model=List[ServicoResponse])
def list_servicos(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db=Depends(get_db),
):
    items = db.query(Servico).filter(Servico.tenant_id == tenant.id).all()
    result: List[ServicoResponse] = []
    for s in items:
        tributacao = None
        if s.tributacao_iss:
            try:
                tributacao = json.loads(s.tributacao_iss)
            except Exception:
                pass
        result.append(
            ServicoResponse(
                id=str(s.id),
                nome=s.nome,
                descricao=s.descricao,
                duracao_minutos=s.duracao_minutos,
                preco=s.preco,
                tributacao_iss=tributacao,
                created_at=s.created_at,
            )
        )
    return result

# -----------------------------------------------------------------------------
# Rotas: Vendas
# -----------------------------------------------------------------------------
@api.post("/vendas", response_model=VendaResponse)
def create_venda(
    payload: VendaCreate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db=Depends(get_db),
):
    subtotal = sum(i.quantidade * i.preco_unitario - i.desconto for i in payload.itens)
    total = subtotal

    venda = Venda(
        cliente_id=payload.cliente_id,
        cliente_nome=payload.cliente_nome,
        itens=json.dumps([i.dict() for i in payload.itens]),
        subtotal=subtotal,
        total=total,
        forma_pagamento=payload.forma_pagamento,
        emitir_nota=payload.emitir_nota,
        tenant_id=tenant.id,
        vendedor_id=current_user.id,
    )
    db.add(venda)

    # baixa de estoque para produtos
    for i in payload.itens:
        if i.tipo == "produto":
            p = (
                db.query(Produto)
                .filter(Produto.id == i.item_id, Produto.tenant_id == tenant.id)
                .first()
            )
            if p:
                try:
                    p.estoque_atual -= int(i.quantidade)
                except Exception:
                    pass

    db.commit()
    db.refresh(venda)

    parsed: List[ItemVenda] = []
    try:
        data = json.loads(venda.itens)
        parsed = [ItemVenda(**x) for x in data]
    except Exception:
        pass

    return VendaResponse(
        id=str(venda.id),
        cliente_id=str(venda.cliente_id) if venda.cliente_id else None,
        cliente_nome=venda.cliente_nome,
        itens=parsed,
        subtotal=venda.subtotal,
        desconto_total=venda.desconto_total,
        total=venda.total,
        forma_pagamento=venda.forma_pagamento,
        emitir_nota=venda.emitir_nota,
        status_nota=venda.status_nota,
        created_at=venda.created_at,
    )


@api.get("/vendas", response_model=List[VendaResponse])
def list_vendas(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db=Depends(get_db),
):
    vendas = db.query(Venda).filter(Venda.tenant_id == tenant.id).all()
    result: List[VendaResponse] = []
    for v in vendas:
        parsed: List[ItemVenda] = []
        try:
            data = json.loads(v.itens)
            parsed = [ItemVenda(**x) for x in data]
        except Exception:
            pass
        result.append(
            VendaResponse(
                id=str(v.id),
                cliente_id=str(v.cliente_id) if v.cliente_id else None,
                cliente_nome=v.cliente_nome,
                itens=parsed,
                subtotal=v.subtotal,
                desconto_total=v.desconto_total,
                total=v.total,
                forma_pagamento=v.forma_pagamento,
                emitir_nota=v.emitir_nota,
                status_nota=v.status_nota,
                created_at=v.created_at,
            )
        )
    return result

# -----------------------------------------------------------------------------
# Rotas: Agendamentos
# -----------------------------------------------------------------------------
@api.post("/agendamentos", response_model=AgendamentoResponse)
def create_agendamento(
    payload: AgendamentoCreate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db=Depends(get_db),
):
    ag = Agendamento(**payload.dict(), tenant_id=tenant.id)
    db.add(ag)
    db.commit()
    db.refresh(ag)
    return AgendamentoResponse(
        id=str(ag.id),
        cliente_id=str(ag.cliente_id),
        servico_id=str(ag.servico_id),
        data_hora=ag.data_hora,
        status=ag.status,
        observacoes=ag.observacoes,
        created_at=ag.created_at,
    )


@api.get("/agendamentos", response_model=List[AgendamentoResponse])
def list_agendamentos(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db=Depends(get_db),
):
    items = db.query(Agendamento).filter(Agendamento.tenant_id == tenant.id).all()
    return [
        AgendamentoResponse(
            id=str(a.id),
            cliente_id=str(a.cliente_id),
            servico_id=str(a.servico_id),
            data_hora=a.data_hora,
            status=a.status,
            observacoes=a.observacoes,
            created_at=a.created_at,
        )
        for a in items
    ]

# -----------------------------------------------------------------------------
# Registrar Router e inicialização
# -----------------------------------------------------------------------------
app.include_router(api)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("server")

# cria tabelas ao iniciar (safe idempotent)
create_tables()


@app.on_event("startup")
def ensure_super_admin():
    """Cria o usuário SUPER ADMIN se não existir (sem tenant)."""
    db = SessionLocal()
    try:
        email = os.environ.get("ADMIN_EMAIL", "admin@sistema.com")
        password = os.environ.get("ADMIN_PASSWORD", "admin123")

        existing = (
            db.query(User)
            .filter(User.email == email, User.tenant_id.is_(None), User.role == UserRole.SUPER_ADMIN)
            .first()
        )
        if not existing:
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                name="Super Admin",
                hashed_password=get_password_hash(password),
                role=UserRole.SUPER_ADMIN,
                tenant_id=None,
            )
            db.add(user)
            db.commit()
            logger.info("Super admin criado")
        else:
            logger.info("Super admin já existe")
    finally:
        db.close()
