# server.py (PT-BR vars) — ajustado para suas variáveis de ambiente
# Lê nomes PT-BR como:
# - E-MAIL_ADMINISTRATIVO   (ou EMAIL_ADMINISTRATIVO / E_MAIL_ADMINISTRATIVO / ADMIN_EMAIL)
# - SENHA_ADMIN             (ou ADMIN_PASSWORD)
# - CORS_ORIGENS_PERMITIDAS (ou CORS_ALLOWED_ORIGINS)
# - URL_FRONTEND            (ou FRONTEND_URL)
# - REENVIAR_CHAVE_API      (ou RESEND_API_KEY)
# - REENVIAR_DE             (ou RESEND_FROM)
# E no banco:
# - ver database.py (URL_DO_BANCO_DE_DADOS ou DATABASE_URL)
#
# Observação: Alguns provedores não aceitam hífen '-' em nomes de env vars.
# Este arquivo checa variações alternativas automaticamente.

from __future__ import annotations
import os
import json
import uuid
import logging
import secrets
from datetime import datetime, timezone, timedelta, timezone
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from jose import JWTError, jwt

# -------------- helpers --------------
def get_env_any(candidates: list[str], default: str | None = None) -> str | None:
    for name in candidates:
        val = os.environ.get(name)
        if val is not None and str(val).strip() != "":
            return val
    return default

# ------------ database imports (tolerante a layout) ------------
try:
    from .database import (
        get_db, create_tables,
        Tenant, User, Cliente, Produto, Servico, Venda, Agendamento, SessionLocal,
    )
except Exception:
    from database import (
        get_db, create_tables,
        Tenant, User, Cliente, Produto, Servico, Venda, Agendamento, SessionLocal,
    )

# -------------- configuração de ambiente --------------
JWT_SECRET = get_env_any(["JWT_SECRETO", "JWT_SECRET"], "troque-este-segredo")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(get_env_any(["MINUTOS_EXPIRACAO_TOKEN", "ACCESS_TOKEN_EXPIRE_MINUTES"], "1440"))

FRONTEND_URL = get_env_any(["URL_FRONTEND", "FRONTEND_URL"], "https://agenda-boa.netlify.app")
RESEND_API_KEY = get_env_any(["REENVIAR_CHAVE_API", "RESEND_API_KEY"], None)
RESEND_FROM = get_env_any(["REENVIAR_DE", "RESEND_FROM"], "Sistema ERP <noreply@sistema.com>")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(title="ERP SaaS - API", version="2.0.0")
api_router = APIRouter(prefix="/api")

origins_env = get_env_any(["CORS_ORIGENS_PERMITIDAS", "CORS_ALLOWED_ORIGINS"], "*").strip()
origins = [o.strip() for o in origins_env.split(",") if o.strip()]
allow_all = len(origins) == 1 and origins[0] == "*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else origins,
    allow_credentials=not allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Email (Resend) - opcional
try:
    import resend  # type: ignore
    if RESEND_API_KEY:
        resend.api_key = RESEND_API_KEY
except Exception:
    resend = None

# Criar tabelas na subida
try:
    create_tables()
except Exception as e:
    logging.getLogger("server").warning(f"create_tables() falhou/ignorado: {e}")

# -------------- modelos pydantic --------------
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
    tipo: str
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

# -------------- utils --------------
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
    if not RESEND_API_KEY or not resend:
        print(f"[Email SIMULADO] To: {to_email} | Subject: {subject}")
        return True
    try:
        params = {"from": RESEND_FROM, "to": [to_email], "subject": subject, "html": html_content}
        _ = resend.Emails.send(params)  # type: ignore
        return True
    except Exception as e:
        print(f"[Email ERRO] {e}")
        return False

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db=Depends(get_db)) -> User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

async def get_current_tenant(current_user: User = Depends(get_current_user), db=Depends(get_db)) -> Optional[Tenant]:
    if current_user.role == UserRole.SUPER_ADMIN:
        return None
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with any tenant")
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant not found")
    if not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant account suspended")
    return tenant

# -------------- rotas --------------
app_router = APIRouter()

@app_router.get("/health", tags=["Health"])
def health_api():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

@app.get("/health", tags=["Health"])
def health_root():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    fav = os.getenv("FAVICON_PATH")
    if fav and os.path.exists(fav):
        return FileResponse(fav, media_type="image/x-icon")
    return Response(status_code=204)

# -- [super admin] criar tenant
@api_router.post("/super-admin/tenants", response_model=TenantResponse)
async def create_tenant(tenant_data: TenantCreate, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admin can create tenants")
    existing_tenant = db.query(Tenant).filter(Tenant.subdomain == tenant_data.subdomain).first()
    if existing_tenant:
        raise HTTPException(status_code=400, detail="Subdomain already exists")
    tenant = Tenant(
        subdomain=tenant_data.subdomain,
        company_name=tenant_data.company_name,
        cnpj=tenant_data.cnpj,
        razao_social=tenant_data.razao_social,
        plan=tenant_data.plan,
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(tenant); db.flush()
    hashed_password = get_password_hash(tenant_data.admin_password)
    admin_user = User(
        email=tenant_data.admin_email,
        name=tenant_data.admin_name,
        hashed_password=hashed_password,
        role=UserRole.ADMIN_EMPRESA,
        tenant_id=tenant.id,
    )
    db.add(admin_user); db.commit()
    welcome_html = f"""
        <h1>Bem-vindo ao ERP Sistema!</h1>
        <p>Olá {tenant_data.admin_name},</p>
        <p>Sua conta foi criada com sucesso!</p>
        <p><strong>Subdomínio:</strong> {tenant_data.subdomain}</p>
        <p><strong>Email:</strong> {tenant_data.admin_email}</p>
        <p><strong>URL de acesso:</strong> <a href="{FRONTEND_URL}">{FRONTEND_URL}</a></p>
        <p>Você tem 30 dias de trial.</p>
    """
    send_email(tenant_data.admin_email, "Bem-vindo ao ERP Sistema", welcome_html)
    return TenantResponse(
        id=str(tenant.id), subdomain=tenant.subdomain, company_name=tenant.company_name,
        cnpj=tenant.cnpj, is_active=tenant.is_active, plan=tenant.plan,
        subscription_status=tenant.subscription_status, created_at=tenant.created_at,
    )

@api_router.get("/super-admin/tenants", response_model=List[TenantResponse])
async def get_all_tenants(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admin can view all tenants")
    tenants = db.query(Tenant).all()
    return [
        TenantResponse(
            id=str(t.id), subdomain=t.subdomain, company_name=t.company_name, cnpj=t.cnpj,
            is_active=t.is_active, plan=t.plan, subscription_status=t.subscription_status,
            created_at=t.created_at,
        ) for t in tenants
    ]

@api_router.put("/super-admin/tenants/{tenant_id}/toggle-status")
async def toggle_tenant_status(tenant_id: str, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admin can toggle tenant status")
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.is_active = not tenant.is_active
    tenant.subscription_status = "active" if tenant.is_active else "suspended"
    db.commit()
    return {"message": f"Tenant {'activated' if tenant.is_active else 'suspended'} successfully"}

@api_router.get("/super-admin/dashboard", response_model=SuperAdminDashboard)
async def get_super_admin_dashboard(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admin can view admin dashboard")
    total_tenants = db.query(Tenant).count()
    active_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()  # noqa: E712
    trial_tenants = db.query(Tenant).filter(Tenant.subscription_status == "trial").count()
    suspended_tenants = db.query(Tenant).filter(Tenant.is_active == False).count()  # noqa: E712
    total_users = db.query(User).filter(User.role != UserRole.SUPER_ADMIN).count()
    recent_tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).limit(5).all()
    recent_signups = [
        {"company_name": t.company_name, "subdomain": t.subdomain, "created_at": t.created_at.isoformat(), "plan": t.plan}
        for t in recent_tenants
    ]
    return SuperAdminDashboard(
        total_tenants=total_tenants, active_tenants=active_tenants, trial_tenants=trial_tenants,
        suspended_tenants=suspended_tenants, total_users=total_users, monthly_revenue=0.0,
        recent_signups=recent_signups,
    )

@api_router.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin, db=Depends(get_db)):
    query = db.query(User).filter(User.email == user_credentials.email)
    if user_credentials.subdomain:
        tenant = db.query(Tenant).filter(Tenant.subdomain == user_credentials.subdomain).first()
        if not tenant:
            raise HTTPException(status_code=400, detail="Invalid subdomain")
        query = query.filter(User.tenant_id == tenant.id)
    else:
        query = query.filter(User.tenant_id.is_(None))
    user = query.first()
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    if user.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if not tenant or not tenant.is_active:
            raise HTTPException(status_code=403, detail="Account suspended")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    user_response = UserResponse(
        id=str(user.id), email=user.email, name=user.name, role=user.role,
        tenant_id=str(user.tenant_id) if user.tenant_id else None, is_active=user.is_active,
    )
    return Token(access_token=access_token, token_type="bearer", user=user_response)

@api_router.post("/auth/forgot-password")
async def forgot_password(request: PasswordResetRequest, db=Depends(get_db)):
    query = db.query(User).filter(User.email == request.email)
    if request.subdomain:
        tenant = db.query(Tenant).filter(Tenant.subdomain == request.subdomain).first()
        if tenant:
            query = query.filter(User.tenant_id == tenant.id)
    user = query.first()
    if not user:
        return {"message": "If the email exists, a reset link has been sent"}
    reset_token = generate_reset_token()
    user.reset_token = reset_token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()
    reset_url = f"{FRONTEND_URL}/reset-password?token={reset_token}"
    reset_html = f"""
        <h1>Redefinir Senha</h1>
        <p>Olá {user.name},</p>
        <p><a href="{reset_url}">Clique aqui para redefinir sua senha</a></p>
        <p>Este link expira em 1 hora.</p>
    """
    send_email(user.email, "Redefinir Senha - ERP Sistema", reset_html)
    return {"message": "If the email exists, a reset link has been sent"}

@api_router.post("/auth/reset-password")
async def reset_password(request: PasswordReset, db=Depends(get_db)):
    user = db.query(User).filter(
        User.reset_token == request.token,
        User.reset_token_expires > datetime.now(timezone.utc),
    ).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user.hashed_password = get_password_hash(request.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return {"message": "Password reset successfully"}

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id), email=current_user.email, name=current_user.name,
        role=current_user.role, tenant_id=str(current_user.tenant_id) if current_user.tenant_id else None,
        is_active=current_user.is_active,
    )

@api_router.get("/dashboard", response_model=Dashboard)
async def get_dashboard(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    if current_user.role == UserRole.SUPER_ADMIN:
        total_tenants = db.query(Tenant).count()
        total_users = db.query(User).count()
        vendas_periodo = [{"data":"2024-09-01","valor":1000},{"data":"2024-09-02","valor":1500},{"data":"2024-09-03","valor":2000}]
        top_produtos = [{"nome":"Plano Pro","vendas":12},{"nome":"Plano Basic","vendas":30}]
        return Dashboard(
            total_vendas=float(total_users)*10.0, total_despesas=0.0, lucro=float(total_users)*10.0,
            margem_lucro=100.0, itens_estoque=0, agendamentos_hoje=0, vendas_periodo=vendas_periodo, top_produtos=top_produtos,
        )
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with any tenant")
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant account suspended")
    vendas = db.query(Venda).filter(Venda.tenant_id == tenant.id).all()
    produtos = db.query(Produto).filter(Produto.tenant_id == tenant.id).all()
    total_vendas = sum(v.total for v in vendas)
    total_despesas = 0.0
    lucro = total_vendas - total_despesas
    margem_lucro = (lucro / total_vendas * 100.0) if total_vendas > 0 else 0.0
    itens_estoque = sum(p.estoque_atual for p in produtos)
    agendamentos_hoje = 0
    vendas_periodo = [{"data":"2024-09-01","valor":1000},{"data":"2024-09-02","valor":1500},{"data":"2024-09-03","valor":2000}]
    top_produtos = [{"nome":"Produto A","vendas":50},{"nome":"Produto B","vendas":30},{"nome":"Produto C","vendas":20}]
    return Dashboard(
        total_vendas=total_vendas, total_despesas=total_despesas, lucro=lucro, margem_lucro=margem_lucro,
        itens_estoque=itens_estoque, agendamentos_hoje=agendamentos_hoje, vendas_periodo=vendas_periodo, top_produtos=top_produtos,
    )

# CRUDs resumidos (iguais ao seu)
@api_router.post("/clientes", response_model=ClienteResponse)
async def create_cliente(cliente_data: ClienteCreate, current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db=Depends(get_db)):
    cliente = Cliente(**cliente_data.dict(), tenant_id=tenant.id)
    db.add(cliente); db.commit(); db.refresh(cliente)
    return ClienteResponse(
        id=str(cliente.id), nome=cliente.nome, email=cliente.email, telefone=cliente.telefone,
        cpf_cnpj=cliente.cpf_cnpj, endereco=cliente.endereco, foto_url=cliente.foto_url,
        anamnese=cliente.anamnese, created_at=cliente.created_at,
    )

@api_router.get("/clientes", response_model=List[ClienteResponse])
async def get_clientes(current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db=Depends(get_db)):
    clientes = db.query(Cliente).filter(Cliente.tenant_id == tenant.id).all()
    return [ClienteResponse(
        id=str(c.id), nome=c.nome, email=c.email, telefone=c.telefone, cpf_cnpj=c.cpf_cnpj,
        endereco=c.endereco, foto_url=c.foto_url, anamnese=c.anamnese, created_at=c.created_at,
    ) for c in clientes]

@api_router.post("/produtos", response_model=ProdutoResponse)
async def create_produto(produto_data: ProdutoCreate, current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db=Depends(get_db)):
    produto = Produto(**produto_data.dict(), tenant_id=tenant.id)
    db.add(produto); db.commit(); db.refresh(produto)
    return ProdutoResponse(
        id=str(produto.id), codigo=produto.codigo, nome=produto.nome, descricao=produto.descricao, categoria=produto.categoria,
        ncm=produto.ncm, custo=produto.custo, preco=produto.preco, estoque_atual=produto.estoque_atual,
        estoque_minimo=produto.estoque_minimo, created_at=produto.created_at,
    )

@api_router.get("/produtos", response_model=List[ProdutoResponse])
async def get_produtos(current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db=Depends(get_db)):
    produtos = db.query(Produto).filter(Produto.tenant_id == tenant.id).all()
    return [ProdutoResponse(
        id=str(p.id), codigo=p.codigo, nome=p.nome, descricao=p.descricao, categoria=p.categoria, ncm=p.ncm,
        custo=p.custo, preco=p.preco, estoque_atual=p.estoque_atual, estoque_minimo=p.estoque_minimo, created_at=p.created_at,
    ) for p in produtos]

@api_router.post("/servicos", response_model=ServicoResponse)
async def create_servico(servico_data: ServicoCreate, current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db=Depends(get_db)):
    servico_dict = servico_data.dict()
    if servico_dict.get("tributacao_iss"):
        servico_dict["tributacao_iss"] = json.dumps(servico_dict["tributacao_iss"])
    servico = Servico(**servico_dict, tenant_id=tenant.id)
    db.add(servico); db.commit(); db.refresh(servico)
    tributacao = None
    if servico.tributacao_iss:
        try: tributacao = json.loads(servico.tributacao_iss)
        except Exception: tributacao = None
    return ServicoResponse(
        id=str(servico.id), nome=servico.nome, descricao=servico.descricao, duracao_minutos=servico.duracao_minutos,
        preco=servico.preco, tributacao_iss=tributacao, created_at=servico.created_at,
    )

@api_router.get("/servicos", response_model=List[ServicoResponse])
async def get_servicos(current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db=Depends(get_db)):
    servicos = db.query(Servico).filter(Servico.tenant_id == tenant.id).all()
    result: List[ServicoResponse] = []
    for s in servicos:
        tributacao = None
        if s.tributacao_iss:
            try: tributacao = json.loads(s.tributacao_iss)
            except Exception: tributacao = None
        result.append(ServicoResponse(
            id=str(s.id), nome=s.nome, descricao=s.descricao, duracao_minutos=s.duracao_minutos,
            preco=s.preco, tributacao_iss=tributacao, created_at=s.created_at,
        ))
    return result

@api_router.post("/vendas", response_model=VendaResponse)
async def create_venda(venda_data: VendaCreate, current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db=Depends(get_db)):
    subtotal = sum(item.quantidade * item.preco_unitario - item.desconto for item in venda_data.itens)
    total = subtotal
    venda = Venda(
        cliente_id=venda_data.cliente_id, cliente_nome=venda_data.cliente_nome,
        itens=json.dumps([item.dict() for item in venda_data.itens]), subtotal=subtotal, total=total,
        forma_pagamento=venda_data.forma_pagamento, emitir_nota=venda_data.emitir_nota,
        tenant_id=tenant.id, vendedor_id=current_user.id,
    )
    db.add(venda)
    for item in venda_data.itens:
        if item.tipo == "produto":
            produto = db.query(Produto).filter(Produto.id == item.item_id, Produto.tenant_id == tenant.id).first()
            if produto:
                try: produto.estoque_atual -= int(item.quantidade)
                except Exception: pass
    db.commit(); db.refresh(venda)
    itens_parsed: List[ItemVenda] = []
    try: itens_parsed = [ItemVenda(**i) for i in json.loads(venda.itens)]
    except Exception: pass
    return VendaResponse(
        id=str(venda.id), cliente_id=str(venda.cliente_id) if venda.cliente_id else None, cliente_nome=venda.cliente_nome,
        itens=itens_parsed, subtotal=venda.subtotal, desconto_total=venda.desconto_total, total=venda.total,
        forma_pagamento=venda.forma_pagamento, emitir_nota=venda.emitir_nota, status_nota=venda.status_nota,
        created_at=venda.created_at,
    )

@api_router.get("/vendas", response_model=List[VendaResponse])
async def get_vendas(current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db=Depends(get_db)):
    vendas = db.query(Venda).filter(Venda.tenant_id == tenant.id).all()
    result: List[VendaResponse] = []
    for v in vendas:
        itens_parsed: List[ItemVenda] = []
        try: itens_parsed = [ItemVenda(**i) for i in json.loads(v.itens)]
        except Exception: itens_parsed = []
        result.append(VendaResponse(
            id=str(v.id), cliente_id=str(v.cliente_id) if v.cliente_id else None, cliente_nome=v.cliente_nome,
            itens=itens_parsed, subtotal=v.subtotal, desconto_total=v.desconto_total, total=v.total,
            forma_pagamento=v.forma_pagamento, emitir_nota=v.emitir_nota, status_nota=v.status_nota,
            created_at=v.created_at,
        ))
    return result

app.include_router(api_router)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("server")

# Criação/checagem do super admin no startup
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        admin_email = get_env_any(["E-MAIL_ADMINISTRATIVO", "EMAIL_ADMINISTRATIVO", "E_MAIL_ADMINISTRATIVO", "ADMIN_EMAIL"], "admin@sistema.com")
        admin_password = get_env_any(["SENHA_ADMIN", "ADMIN_PASSWORD"], "admin123")
        super_admin = db.query(User).filter(User.email == admin_email, User.role == UserRole.SUPER_ADMIN).first()
        if not super_admin:
            super_admin = User(
                id=str(uuid.uuid4()), email=admin_email, name="Super Admin",
                hashed_password=get_password_hash(admin_password),
                role=UserRole.SUPER_ADMIN, tenant_id=None, is_active=True,
            )
            db.add(super_admin); db.commit()
            logger.info("Super admin created")
        else:
            logger.info("Super admin already exists")
    finally:
        db.close()
@app.get('/health', include_in_schema=False)
def health_root():
    return {'status': 'ok', 'time': datetime.now(timezone.utc).isoformat()}

@app.get('/api/health', include_in_schema=False)
def health_api():
    return {'status': 'ok', 'time': datetime.now(timezone.utc).isoformat()}

@app.get("/", tags=["Info"])
def root_info():
    return {"app":"ERP SaaS - API","version":"2.0.0","health":"/health","api_health":"/api/health"}
