from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import os
import logging
import uuid
import secrets
import json
import resend
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables FIRST
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import database AFTER loading env vars
from sqlalchemy.orm import Session
from .database import get_db, create_tables, Tenant, User, Cliente, Produto, Servico, Venda, Agendamento, SessionLocal

# Create tables
create_tables()

# Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-here')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
RESEND_FROM = os.environ.get('RESEND_FROM', 'noreply@sistema.com')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Setup Resend
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(title="ERP SaaS - Sistema de Gestão Empresarial", version="2.0.0")


@app.get('/health')
def health():
    return {'status': 'ok'}
api_router = APIRouter(prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
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

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def generate_reset_token():
    return secrets.token_urlsafe(32)

def send_email(to_email: str, subject: str, html_content: str):
    if not RESEND_API_KEY:
        print(f"Email simulation - To: {to_email}, Subject: {subject}")
        return True
    
    try:
        params = {
            "from": RESEND_FROM,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        email = resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
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

# Dependency to get current tenant
async def get_current_tenant(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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

# Super Admin Routes
@api_router.post("/super-admin/tenants", response_model=TenantResponse)
async def create_tenant(tenant_data: TenantCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admin can create tenants")
    
    # Check if subdomain exists
    existing_tenant = db.query(Tenant).filter(Tenant.subdomain == tenant_data.subdomain).first()
    if existing_tenant:
        raise HTTPException(status_code=400, detail="Subdomain already exists")
    
    # Create tenant
    tenant = Tenant(
        subdomain=tenant_data.subdomain,
        company_name=tenant_data.company_name,
        cnpj=tenant_data.cnpj,
        razao_social=tenant_data.razao_social,
        plan=tenant_data.plan,
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(tenant)
    db.flush()
    
    # Create admin user
    hashed_password = get_password_hash(tenant_data.admin_password)
    admin_user = User(
        email=tenant_data.admin_email,
        name=tenant_data.admin_name,
        hashed_password=hashed_password,
        role=UserRole.ADMIN_EMPRESA,
        tenant_id=tenant.id
    )
    db.add(admin_user)
    db.commit()
    
    # Send welcome email
    welcome_html = f"""
    <h1>Bem-vindo ao ERP Sistema!</h1>
    <p>Olá {tenant_data.admin_name},</p>
    <p>Sua conta foi criada com sucesso!</p>
    <p><strong>Subdomínio:</strong> {tenant_data.subdomain}</p>
    <p><strong>Email:</strong> {tenant_data.admin_email}</p>
    <p><strong>URL de acesso:</strong> <a href="{FRONTEND_URL}">{FRONTEND_URL}</a></p>
    <p>Você tem 30 dias de trial gratuito para testar todas as funcionalidades.</p>
    """
    send_email(tenant_data.admin_email, "Bem-vindo ao ERP Sistema", welcome_html)
    
    return TenantResponse(
        id=str(tenant.id),
        subdomain=tenant.subdomain,
        company_name=tenant.company_name,
        cnpj=tenant.cnpj,
        is_active=tenant.is_active,
        plan=tenant.plan,
        subscription_status=tenant.subscription_status,
        created_at=tenant.created_at
    )

@api_router.get("/super-admin/tenants", response_model=List[TenantResponse])
async def get_all_tenants(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admin can view all tenants")
    
    tenants = db.query(Tenant).all()
    return [TenantResponse(
        id=str(tenant.id),
        subdomain=tenant.subdomain,
        company_name=tenant.company_name,
        cnpj=tenant.cnpj,
        is_active=tenant.is_active,
        plan=tenant.plan,
        subscription_status=tenant.subscription_status,
        created_at=tenant.created_at
    ) for tenant in tenants]

@api_router.put("/super-admin/tenants/{tenant_id}/toggle-status")
async def toggle_tenant_status(tenant_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
async def get_super_admin_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admin can view admin dashboard")
    
    total_tenants = db.query(Tenant).count()
    active_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
    trial_tenants = db.query(Tenant).filter(Tenant.subscription_status == "trial").count()
    suspended_tenants = db.query(Tenant).filter(Tenant.is_active == False).count()
    total_users = db.query(User).filter(User.role != UserRole.SUPER_ADMIN).count()
    
    recent_tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).limit(5).all()
    recent_signups = [
        {
            "company_name": tenant.company_name,
            "subdomain": tenant.subdomain,
            "created_at": tenant.created_at.isoformat(),
            "plan": tenant.plan
        }
        for tenant in recent_tenants
    ]
    
    return SuperAdminDashboard(
        total_tenants=total_tenants,
        active_tenants=active_tenants,
        trial_tenants=trial_tenants,
        suspended_tenants=suspended_tenants,
        total_users=total_users,
        monthly_revenue=0.0,  # TODO: Calculate from Stripe
        recent_signups=recent_signups
    )

# Authentication Routes
@api_router.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    # Find user by email (and optionally subdomain for tenant users)
    query = db.query(User).filter(User.email == user_credentials.email)
    
    if user_credentials.subdomain:
        # Login for tenant user
        tenant = db.query(Tenant).filter(Tenant.subdomain == user_credentials.subdomain).first()
        if not tenant:
            raise HTTPException(status_code=400, detail="Invalid subdomain")
        query = query.filter(User.tenant_id == tenant.id)
    else:
        # Login for super admin (no tenant)
        query = query.filter(User.tenant_id.is_(None))
    
    user = query.first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Check tenant status
    if user.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if not tenant or not tenant.is_active:
            raise HTTPException(status_code=403, detail="Account suspended")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        is_active=user.is_active
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user_response)

@api_router.post("/auth/forgot-password")
async def forgot_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    query = db.query(User).filter(User.email == request.email)
    
    if request.subdomain:
        tenant = db.query(Tenant).filter(Tenant.subdomain == request.subdomain).first()
        if tenant:
            query = query.filter(User.tenant_id == tenant.id)
    
    user = query.first()
    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    reset_token = generate_reset_token()
    user.reset_token = reset_token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()
    
    # Send reset email
    reset_url = f"{FRONTEND_URL}/reset-password?token={reset_token}"
    reset_html = f"""
    <h1>Redefinir Senha</h1>
    <p>Olá {user.name},</p>
    <p>Você solicitou a redefinição de sua senha.</p>
    <p><a href="{reset_url}">Clique aqui para redefinir sua senha</a></p>
    <p>Este link expira em 1 hora.</p>
    <p>Se você não solicitou esta redefinição, ignore este email.</p>
    """
    send_email(user.email, "Redefinir Senha - ERP Sistema", reset_html)
    
    return {"message": "If the email exists, a reset link has been sent"}

@api_router.post("/auth/reset-password")
async def reset_password(request: PasswordReset, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.reset_token == request.token,
        User.reset_token_expires > datetime.now(timezone.utc)
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
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        tenant_id=str(current_user.tenant_id) if current_user.tenant_id else None,
        is_active=current_user.is_active
    )

# Dashboard Routes
@api_router.get("/dashboard", response_model=Dashboard)
async def get_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Super admin gets different dashboard
    if current_user.role == UserRole.SUPER_ADMIN:
        # Redirect to super admin dashboard
        return await get_super_admin_dashboard(current_user, db)
    
    # Get tenant for regular users
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User not associated with any tenant")
    
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant account suspended")
    
    # Calculate metrics for the tenant
    vendas = db.query(Venda).filter(Venda.tenant_id == tenant.id).all()
    produtos = db.query(Produto).filter(Produto.tenant_id == tenant.id).all()
    
    total_vendas = sum(venda.total for venda in vendas)
    total_despesas = 0  # TODO: implement despesas
    lucro = total_vendas - total_despesas
    margem_lucro = (lucro / total_vendas * 100) if total_vendas > 0 else 0
    itens_estoque = sum(produto.estoque_atual for produto in produtos)
    agendamentos_hoje = 0  # TODO: implement agendamentos count
    
    # Sample data for charts
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
        margem_lucro=margem_lucro,
        itens_estoque=itens_estoque,
        agendamentos_hoje=agendamentos_hoje,
        vendas_periodo=vendas_periodo,
        top_produtos=top_produtos
    )

# Cliente Routes
@api_router.post("/clientes", response_model=ClienteResponse)
async def create_cliente(cliente_data: ClienteCreate, current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    cliente = Cliente(**cliente_data.dict(), tenant_id=tenant.id)
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
        created_at=cliente.created_at
    )

@api_router.get("/clientes", response_model=List[ClienteResponse])
async def get_clientes(current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    clientes = db.query(Cliente).filter(Cliente.tenant_id == tenant.id).all()
    return [ClienteResponse(
        id=str(cliente.id),
        nome=cliente.nome,
        email=cliente.email,
        telefone=cliente.telefone,
        cpf_cnpj=cliente.cpf_cnpj,
        endereco=cliente.endereco,
        foto_url=cliente.foto_url,
        anamnese=cliente.anamnese,
        created_at=cliente.created_at
    ) for cliente in clientes]

# Produto Routes
@api_router.post("/produtos", response_model=ProdutoResponse)
async def create_produto(produto_data: ProdutoCreate, current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    produto = Produto(**produto_data.dict(), tenant_id=tenant.id)
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
        created_at=produto.created_at
    )

@api_router.get("/produtos", response_model=List[ProdutoResponse])
async def get_produtos(current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    produtos = db.query(Produto).filter(Produto.tenant_id == tenant.id).all()
    return [ProdutoResponse(
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
        created_at=produto.created_at
    ) for produto in produtos]

# Servico Routes
@api_router.post("/servicos", response_model=ServicoResponse)
async def create_servico(servico_data: ServicoCreate, current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    servico_dict = servico_data.dict()
    if servico_dict['tributacao_iss']:
        servico_dict['tributacao_iss'] = json.dumps(servico_dict['tributacao_iss'])
    
    servico = Servico(**servico_dict, tenant_id=tenant.id)
    db.add(servico)
    db.commit()
    db.refresh(servico)
    
    tributacao_iss = None
    if servico.tributacao_iss:
        try:
            tributacao_iss = json.loads(servico.tributacao_iss)
        except:
            pass
    
    return ServicoResponse(
        id=str(servico.id),
        nome=servico.nome,
        descricao=servico.descricao,
        duracao_minutos=servico.duracao_minutos,
        preco=servico.preco,
        tributacao_iss=tributacao_iss,
        created_at=servico.created_at
    )

@api_router.get("/servicos", response_model=List[ServicoResponse])
async def get_servicos(current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    servicos = db.query(Servico).filter(Servico.tenant_id == tenant.id).all()
    result = []
    for servico in servicos:
        tributacao_iss = None
        if servico.tributacao_iss:
            try:
                tributacao_iss = json.loads(servico.tributacao_iss)
            except:
                pass
        
        result.append(ServicoResponse(
            id=str(servico.id),
            nome=servico.nome,
            descricao=servico.descricao,
            duracao_minutos=servico.duracao_minutos,
            preco=servico.preco,
            tributacao_iss=tributacao_iss,
            created_at=servico.created_at
        ))
    return result

# Venda Routes
@api_router.post("/vendas", response_model=VendaResponse)
async def create_venda(venda_data: VendaCreate, current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    # Calculate totals
    subtotal = sum(item.quantidade * item.preco_unitario - item.desconto for item in venda_data.itens)
    total = subtotal
    
    venda = Venda(
        cliente_id=venda_data.cliente_id,
        cliente_nome=venda_data.cliente_nome,
        itens=json.dumps([item.dict() for item in venda_data.itens]),
        subtotal=subtotal,
        total=total,
        forma_pagamento=venda_data.forma_pagamento,
        emitir_nota=venda_data.emitir_nota,
        tenant_id=tenant.id,
        vendedor_id=current_user.id
    )
    db.add(venda)
    
    # Update product stock
    for item in venda_data.itens:
        if item.tipo == "produto":
            produto = db.query(Produto).filter(
                Produto.id == item.item_id,
                Produto.tenant_id == tenant.id
            ).first()
            if produto:
                produto.estoque_atual -= int(item.quantidade)
    
    db.commit()
    db.refresh(venda)
    
    # Parse items back for response
    itens_parsed = []
    try:
        itens_data = json.loads(venda.itens)
        itens_parsed = [ItemVenda(**item) for item in itens_data]
    except:
        pass
    
    return VendaResponse(
        id=str(venda.id),
        cliente_id=str(venda.cliente_id) if venda.cliente_id else None,
        cliente_nome=venda.cliente_nome,
        itens=itens_parsed,
        subtotal=venda.subtotal,
        desconto_total=venda.desconto_total,
        total=venda.total,
        forma_pagamento=venda.forma_pagamento,
        emitir_nota=venda.emitir_nota,
        status_nota=venda.status_nota,
        created_at=venda.created_at
    )

@api_router.get("/vendas", response_model=List[VendaResponse])
async def get_vendas(current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    vendas = db.query(Venda).filter(Venda.tenant_id == tenant.id).all()
    result = []
    for venda in vendas:
        itens_parsed = []
        try:
            itens_data = json.loads(venda.itens)
            itens_parsed = [ItemVenda(**item) for item in itens_data]
        except:
            pass
        
        result.append(VendaResponse(
            id=str(venda.id),
            cliente_id=str(venda.cliente_id) if venda.cliente_id else None,
            cliente_nome=venda.cliente_nome,
            itens=itens_parsed,
            subtotal=venda.subtotal,
            desconto_total=venda.desconto_total,
            total=venda.total,
            forma_pagamento=venda.forma_pagamento,
            emitir_nota=venda.emitir_nota,
            status_nota=venda.status_nota,
            created_at=venda.created_at
        ))
    return result

# Agendamento Routes
@api_router.post("/agendamentos", response_model=AgendamentoResponse)
async def create_agendamento(agendamento_data: AgendamentoCreate, current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    agendamento = Agendamento(**agendamento_data.dict(), tenant_id=tenant.id)
    db.add(agendamento)
    db.commit()
    db.refresh(agendamento)
    
    return AgendamentoResponse(
        id=str(agendamento.id),
        cliente_id=str(agendamento.cliente_id),
        servico_id=str(agendamento.servico_id),
        data_hora=agendamento.data_hora,
        status=agendamento.status,
        observacoes=agendamento.observacoes,
        created_at=agendamento.created_at
    )

@api_router.get("/agendamentos", response_model=List[AgendamentoResponse])
async def get_agendamentos(current_user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    agendamentos = db.query(Agendamento).filter(Agendamento.tenant_id == tenant.id).all()
    return [AgendamentoResponse(
        id=str(agendamento.id),
        cliente_id=str(agendamento.cliente_id),
        servico_id=str(agendamento.servico_id),
        data_hora=agendamento.data_hora,
        status=agendamento.status,
        observacoes=agendamento.observacoes,
        created_at=agendamento.created_at
    ) for agendamento in agendamentos]

# Include router
app.include_router(api_router)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Startup event to create super admin
@app.on_event("startup")
async def startup_event():
    # Create super admin if not exists
    db = SessionLocal()
    try:
        super_admin = db.query(User).filter(
            User.email == os.environ.get('ADMIN_EMAIL', 'admin@sistema.com'),
            User.role == UserRole.SUPER_ADMIN
        ).first()
        
        if not super_admin:
            super_admin = User(
                id=str(uuid.uuid4()),
                email=os.environ.get('ADMIN_EMAIL', 'admin@sistema.com'),
                name="Super Admin",
                hashed_password=get_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin123')),
                role=UserRole.SUPER_ADMIN,
                tenant_id=None
            )
            db.add(super_admin)
            db.commit()
            logger.info("Super admin created")
    finally:
        db.close()
