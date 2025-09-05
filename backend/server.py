# server.py — versão enxuta (sem modelos), pronta para Railway
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Any

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select

# Importa APENAS do database.py (os modelos vivem lá)
try:
    from .database import (
        SessionLocal, get_db, create_tables,
        Tenant, User, Cliente, Produto, Servico, Venda, Agendamento, Vencimento
    )
except Exception:
    from database import (
        SessionLocal, get_db, create_tables,
        Tenant, User, Cliente, Produto, Servico, Venda, Agendamento, Vencimento
    )

# ====================== Config ======================
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-please")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://agenda-boa.netlify.app")

DEFAULT_CORS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://agenda-boa.netlify.app",
]
if FRONTEND_URL and FRONTEND_URL not in DEFAULT_CORS:
    DEFAULT_CORS.append(FRONTEND_URL)

# ====================== Segurança ======================
# Usa pbkdf2_sha256 para evitar problemas do backend bcrypt no Railway
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(pwd: str) -> str:
    return pwd_context.hash(pwd)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

# ====================== App ======================
app = FastAPI(title="Agenda Boa API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=DEFAULT_CORS,
    allow_origin_regex=r"https://.*\.netlify\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

log = logging.getLogger("server")
logging.basicConfig(level=logging.INFO)

# ====================== Schemas ======================
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    subdomain: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str
    tenant_id: Optional[str] = None

class ClienteIn(BaseModel):
    nome: str
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    endereco: Optional[str] = None
    foto_url: Optional[str] = None
    anamnese: Optional[str] = None

class ClienteOut(ClienteIn):
    id: str

class ProdutoIn(BaseModel):
    nome: str
    preco: float
    codigo: Optional[str] = None
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    ncm: Optional[str] = None
    custo: Optional[float] = 0.0
    estoque_atual: Optional[int] = 0
    estoque_minimo: Optional[int] = 0

class ProdutoOut(ProdutoIn):
    id: str

class ServicoIn(BaseModel):
    nome: str
    preco: float
    descricao: Optional[str] = None
    duracao_minutos: Optional[int] = 60
    tributacao_iss: Optional[str] = None

class ServicoOut(ServicoIn):
    id: str

class VendaItem(BaseModel):
    produto_id: Optional[str] = None
    servico_id: Optional[str] = None
    nome: str
    quantidade: int
    preco: float
    desconto: float = 0.0

class VendaIn(BaseModel):
    cliente_id: Optional[str] = None
    cliente_nome: Optional[str] = None
    itens: List[VendaItem]
    forma_pagamento: str
    emitir_nota: bool = False

class AgendamentoIn(BaseModel):
    cliente_id: str
    servico_id: str
    data_hora: datetime
    status: Optional[str] = "agendado"
    observacoes: Optional[str] = None

# ====================== Auth helpers ======================
auth_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente")

    try:
        payload = decode_token(creds.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        user = db.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Usuário inválido")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

# ====================== Startup ======================
@app.on_event("startup")
def _startup():
    create_tables()
    db = SessionLocal()
    try:
        if ADMIN_EMAIL and ADMIN_PASSWORD:
            exists = db.execute(
                select(User).where(User.email == ADMIN_EMAIL, User.role == "super_admin")
            ).scalar_one_or_none()
            if not exists:
                sa = User(
                    email=ADMIN_EMAIL,
                    name="Super Admin",
                    role="super_admin",
                    hashed_password=hash_password(ADMIN_PASSWORD),
                )
                db.add(sa)
                db.commit()
                log.info("Super admin criado")
            else:
                log.info("Super admin já existia")
        else:
            log.info("ADMIN_EMAIL/ADMIN_PASSWORD não informados — pulando criação de super admin")
    finally:
        db.close()

# ====================== Health ======================
@app.get("/")
def root():
    return {"status": "ok", "service": "agenda-boa", "time": datetime.now(timezone.utc).isoformat()}

@app.get("/health")
@app.get("/api/health")
def health():
    return {"status": "ok"}

# ====================== Auth ======================
auth = APIRouter(prefix="/auth", tags=["auth"])

@auth.post("/login", response_model=TokenResponse)
def do_login(payload: LoginRequest, db: Session = Depends(get_db)) -> Any:
    stmt = select(User).where(User.email == payload.email)
    if payload.subdomain:
        tenant = db.execute(
            select(Tenant).where(Tenant.subdomain == payload.subdomain.strip())
        ).scalar_one_or_none()
        if not tenant:
            raise HTTPException(400, "Empresa não encontrada")
        stmt = stmt.where(User.tenant_id == tenant.id)
    else:
        stmt = stmt.where(User.role == "super_admin")

    user = db.execute(stmt).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "Credenciais inválidas")

    token = create_access_token({"sub": user.id})
    return TokenResponse(
        access_token=token,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        },
    )

# ====================== Clientes ======================
clientes = APIRouter(prefix="/clientes", tags=["clientes"])

@clientes.get("", response_model=List[ClienteOut])
def list_clientes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(Cliente)
    if user.role != "super_admin":
        q = q.where(Cliente.tenant_id == user.tenant_id)
    rows = db.execute(q).scalars().all()
    return [ClienteOut(
        id=str(r.id), nome=r.nome, email=r.email, telefone=r.telefone, cpf_cnpj=r.cpf_cnpj,
        endereco=r.endereco, foto_url=r.foto_url, anamnese=r.anamnese
    ) for r in rows]

@clientes.post("", response_model=ClienteOut)
def create_cliente(payload: ClienteIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "super_admin" and not user.tenant_id:
        raise HTTPException(400, "Super admin não possui tenant para criar clientes")
    obj = Cliente(tenant_id=user.tenant_id, **payload.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return ClienteOut(**payload.dict(), id=str(obj.id))

# ====================== Produtos ======================
produtos = APIRouter(prefix="/produtos", tags=["produtos"])

@produtos.get("", response_model=List[ProdutoOut])
def list_produtos(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(Produto)
    if user.role != "super_admin":
        q = q.where(Produto.tenant_id == user.tenant_id)
    rows = db.execute(q).scalars().all()
    return [ProdutoOut(
        id=str(r.id), nome=r.nome, preco=r.preco, codigo=r.codigo, descricao=r.descricao,
        categoria=r.categoria, ncm=r.ncm, custo=r.custo, estoque_atual=r.estoque_atual, estoque_minimo=r.estoque_minimo
    ) for r in rows]

@produtos.post("", response_model=ProdutoOut)
def create_produto(payload: ProdutoIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "super_admin" and not user.tenant_id:
        raise HTTPException(400, "Super admin não possui tenant para criar produtos")
    obj = Produto(tenant_id=user.tenant_id, **payload.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return ProdutoOut(**payload.dict(), id=str(obj.id))

# ====================== Serviços ======================
servicos = APIRouter(prefix="/servicos", tags=["servicos"])

@servicos.get("", response_model=List[ServicoOut])
def list_servicos(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(Servico)
    if user.role != "super_admin":
        q = q.where(Servico.tenant_id == user.tenant_id)
    rows = db.execute(q).scalars().all()
    return [ServicoOut(
        id=str(r.id), nome=r.nome, preco=r.preco, descricao=r.descricao,
        duracao_minutos=r.duracao_minutos, tributacao_iss=r.tributacao_iss
    ) for r in rows]

@servicos.post("", response_model=ServicoOut)
def create_servico(payload: ServicoIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "super_admin" and not user.tenant_id:
        raise HTTPException(400, "Super admin não possui tenant para criar serviços")
    obj = Servico(tenant_id=user.tenant_id, **payload.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return ServicoOut(**payload.dict(), id=str(obj.id))

# ====================== Vendas ======================
vendas = APIRouter(prefix="/vendas", tags=["vendas"])

@vendas.post("")
def create_venda(payload: VendaIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    itens_json = [i.dict() for i in payload.itens]
    subtotal = sum(i["preco"] * i["quantidade"] for i in itens_json)
    desconto_total = sum(i.get("desconto", 0.0) for i in itens_json)
    total = subtotal - desconto_total

    obj = Venda(
        cliente_id=payload.cliente_id,
        cliente_nome=payload.cliente_nome,
        itens=str(itens_json),
        subtotal=subtotal,
        desconto_total=desconto_total,
        total=total,
        forma_pagamento=payload.forma_pagamento,
        emitir_nota=payload.emitir_nota,
        tenant_id=user.tenant_id,
        vendedor_id=user.id,
    )
    db.add(obj)
    db.commit()
    return {"id": str(obj.id), "total": total}

# ====================== Agendamentos ======================
agendamentos = APIRouter(prefix="/agendamentos", tags=["agendamentos"])

@agendamentos.post("")
def create_agendamento(payload: AgendamentoIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = Agendamento(
        cliente_id=payload.cliente_id,
        servico_id=payload.servico_id,
        data_hora=payload.data_hora,
        status=payload.status,
        observacoes=payload.observacoes,
        tenant_id=user.tenant_id,
    )
    db.add(obj)
    db.commit()
    return {"id": str(obj.id)}

# ====================== Montagem das rotas ======================
api = APIRouter(prefix="/api")
api.include_router(auth)
api.include_router(clientes)
api.include_router(produtos)
api.include_router(servicos)
api.include_router(vendas)
api.include_router(agendamentos)

app.include_router(api)     # /api/...
app.include_router(auth)    # /auth/login (fallback)
