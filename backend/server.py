from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import os
import logging
import uuid

from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-here')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(title="Sistema de Gestão Empresarial", version="1.0.0")
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
    ADMIN_SISTEMA = "admin_sistema"
    ADMIN_EMPRESA = "admin_empresa"
    OPERADOR = "operador"

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    role: str
    empresa_id: Optional[str] = None
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str = UserRole.OPERADOR
    empresa_id: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class Empresa(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nome: str
    cnpj: str
    razao_social: str
    nome_fantasia: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    usar_certificado: bool = False
    certificado_config: Optional[Dict[str, Any]] = None
    ativa: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmpresaCreate(BaseModel):
    nome: str
    cnpj: str
    razao_social: str
    nome_fantasia: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    usar_certificado: bool = False
    admin_email: EmailStr
    admin_name: str
    admin_password: str

class Cliente(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nome: str
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    endereco: Optional[str] = None
    foto_url: Optional[str] = None
    anamnese: Optional[str] = None
    empresa_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ClienteCreate(BaseModel):
    nome: str
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    endereco: Optional[str] = None
    anamnese: Optional[str] = None

class Produto(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    codigo: Optional[str] = None
    nome: str
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    ncm: Optional[str] = None
    custo: float = 0.0
    preco: float = 0.0
    estoque_atual: int = 0
    estoque_minimo: int = 0
    empresa_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProdutoCreate(BaseModel):
    codigo: Optional[str] = None
    nome: str
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    ncm: Optional[str] = None
    custo: float = 0.0
    preco: float = 0.0
    estoque_atual: int = 0
    estoque_minimo: int = 0

class Servico(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nome: str
    descricao: Optional[str] = None
    duracao_minutos: int = 60
    preco: float = 0.0
    tributacao_iss: Optional[Dict[str, Any]] = None
    empresa_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ServicoCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    duracao_minutos: int = 60
    preco: float = 0.0
    tributacao_iss: Optional[Dict[str, Any]] = None

class ItemVenda(BaseModel):
    tipo: str  # "produto" ou "servico"
    item_id: str
    nome: str
    quantidade: float
    preco_unitario: float
    desconto: float = 0.0
    total: float

class Venda(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cliente_id: Optional[str] = None
    cliente_nome: Optional[str] = None
    itens: List[ItemVenda]
    subtotal: float
    desconto_total: float = 0.0
    total: float
    forma_pagamento: str
    emitir_nota: bool = False
    status_nota: Optional[str] = None
    nota_numero: Optional[str] = None
    nota_xml: Optional[str] = None
    nota_pdf_url: Optional[str] = None
    empresa_id: str
    vendedor_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VendaCreate(BaseModel):
    cliente_id: Optional[str] = None
    cliente_nome: Optional[str] = None
    itens: List[ItemVenda]
    forma_pagamento: str
    emitir_nota: bool = False

class Dashboard(BaseModel):
    total_vendas: float
    total_despesas: float
    lucro: float
    margem_lucro: float
    itens_estoque: int
    agendamentos_hoje: int
    vendas_periodo: List[Dict[str, Any]]
    top_produtos: List[Dict[str, Any]]

# Auth functions
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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
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
    
    user = await db.users.find_one({"email": email})
    if user is None:
        raise credentials_exception
    return User(**user)

# Routes
@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user
    user_dict = user_data.dict()
    user_dict.pop('password')
    user_dict['hashed_password'] = hashed_password
    user_obj = User(**user_dict)
    
    await db.users.insert_one(user_obj.dict())
    return user_obj

@api_router.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin):
    user = await db.users.find_one({"email": user_credentials.email})
    if not user or not verify_password(user_credentials.password, user.get('hashed_password')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['email']}, expires_delta=access_token_expires
    )
    
    user_obj = User(**user)
    return {"access_token": access_token, "token_type": "bearer", "user": user_obj}

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# Empresa routes
@api_router.post("/empresas", response_model=Empresa)
async def create_empresa(empresa_data: EmpresaCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN_SISTEMA:
        raise HTTPException(status_code=403, detail="Only system admin can create companies")
    
    # Create company
    empresa_dict = empresa_data.dict()
    admin_email = empresa_dict.pop('admin_email')
    admin_name = empresa_dict.pop('admin_name')
    admin_password = empresa_dict.pop('admin_password')
    
    empresa_obj = Empresa(**empresa_dict)
    await db.empresas.insert_one(empresa_obj.dict())
    
    # Create admin user for company
    admin_user = UserCreate(
        email=admin_email,
        name=admin_name,
        password=admin_password,
        role=UserRole.ADMIN_EMPRESA,
        empresa_id=empresa_obj.id
    )
    
    hashed_password = get_password_hash(admin_user.password)
    admin_dict = admin_user.dict()
    admin_dict.pop('password')
    admin_dict['hashed_password'] = hashed_password
    admin_user_obj = User(**admin_dict)
    
    await db.users.insert_one(admin_user_obj.dict())
    
    return empresa_obj

@api_router.get("/empresas", response_model=List[Empresa])
async def get_empresas(current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.ADMIN_SISTEMA:
        empresas = await db.empresas.find().to_list(1000)
    else:
        empresas = await db.empresas.find({"id": current_user.empresa_id}).to_list(1000)
    return [Empresa(**empresa) for empresa in empresas]

# Cliente routes
@api_router.post("/clientes", response_model=Cliente)
async def create_cliente(cliente_data: ClienteCreate, current_user: User = Depends(get_current_user)):
    cliente_dict = cliente_data.dict()
    cliente_dict['empresa_id'] = current_user.empresa_id
    cliente_obj = Cliente(**cliente_dict)
    await db.clientes.insert_one(cliente_obj.dict())
    return cliente_obj

@api_router.get("/clientes", response_model=List[Cliente])
async def get_clientes(current_user: User = Depends(get_current_user)):
    clientes = await db.clientes.find({"empresa_id": current_user.empresa_id}).to_list(1000)
    return [Cliente(**cliente) for cliente in clientes]

# Produto routes
@api_router.post("/produtos", response_model=Produto)
async def create_produto(produto_data: ProdutoCreate, current_user: User = Depends(get_current_user)):
    produto_dict = produto_data.dict()
    produto_dict['empresa_id'] = current_user.empresa_id
    produto_obj = Produto(**produto_dict)
    await db.produtos.insert_one(produto_obj.dict())
    return produto_obj

@api_router.get("/produtos", response_model=List[Produto])
async def get_produtos(current_user: User = Depends(get_current_user)):
    produtos = await db.produtos.find({"empresa_id": current_user.empresa_id}).to_list(1000)
    return [Produto(**produto) for produto in produtos]

# Servico routes
@api_router.post("/servicos", response_model=Servico)
async def create_servico(servico_data: ServicoCreate, current_user: User = Depends(get_current_user)):
    servico_dict = servico_data.dict()
    servico_dict['empresa_id'] = current_user.empresa_id
    servico_obj = Servico(**servico_dict)
    await db.servicos.insert_one(servico_obj.dict())
    return servico_obj

@api_router.get("/servicos", response_model=List[Servico])
async def get_servicos(current_user: User = Depends(get_current_user)):
    servicos = await db.servicos.find({"empresa_id": current_user.empresa_id}).to_list(1000)
    return [Servico(**servico) for servico in servicos]

# Venda routes
@api_router.post("/vendas", response_model=Venda)
async def create_venda(venda_data: VendaCreate, current_user: User = Depends(get_current_user)):
    # Calculate totals
    subtotal = sum(item.quantidade * item.preco_unitario - item.desconto for item in venda_data.itens)
    total = subtotal
    
    venda_dict = venda_data.dict()
    venda_dict.update({
        'empresa_id': current_user.empresa_id,
        'vendedor_id': current_user.id,
        'subtotal': subtotal,
        'total': total
    })
    
    venda_obj = Venda(**venda_dict)
    await db.vendas.insert_one(venda_obj.dict())
    
    # Update stock for products
    for item in venda_data.itens:
        if item.tipo == "produto":
            await db.produtos.update_one(
                {"id": item.item_id, "empresa_id": current_user.empresa_id},
                {"$inc": {"estoque_atual": -item.quantidade}}
            )
    
    return venda_obj

@api_router.get("/vendas", response_model=List[Venda])
async def get_vendas(current_user: User = Depends(get_current_user)):
    vendas = await db.vendas.find({"empresa_id": current_user.empresa_id}).to_list(1000)
    return [Venda(**venda) for venda in vendas]

# Dashboard
@api_router.get("/dashboard", response_model=Dashboard)
async def get_dashboard(current_user: User = Depends(get_current_user)):
    # Calculate metrics
    vendas = await db.vendas.find({"empresa_id": current_user.empresa_id}).to_list(1000)
    produtos = await db.produtos.find({"empresa_id": current_user.empresa_id}).to_list(1000)
    
    total_vendas = sum(venda['total'] for venda in vendas)
    total_despesas = 0  # TODO: implement despesas
    lucro = total_vendas - total_despesas
    margem_lucro = (lucro / total_vendas * 100) if total_vendas > 0 else 0
    itens_estoque = sum(prod['estoque_atual'] for prod in produtos)
    agendamentos_hoje = 0  # TODO: implement agendamentos
    
    # Sample data for charts
    vendas_periodo = [
        {"data": "2024-01-01", "valor": 1000},
        {"data": "2024-01-02", "valor": 1500},
        {"data": "2024-01-03", "valor": 2000},
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

# Include router
app.include_router(api_router)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()