import os
import uuid
import logging
import warnings
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.exc import SAWarning
from passlib.context import CryptContext

# -----------------------------------------------------------------------------
# Ignora SAWarning de conflito de relacionamentos (ruído nos logs)
# -----------------------------------------------------------------------------
warnings.filterwarnings(
    "ignore",
    category=SAWarning,
    message=r".*relationship .* conflicts with relationship.*",
)

# -----------------------------------------------------------------------------
# Imports dos modelos e utilitários de DB
# OBS: server.py e database.py estão no MESMO pacote/pasta.
# -----------------------------------------------------------------------------
try:
    # se estiver dentro de um pacote (ex.: app/server.py e app/database.py)
    from .database import (
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
        Vencimento,
    )
except Exception:
    # se estiverem lado a lado (server.py e database.py na mesma pasta)
    from database import (
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
        Vencimento,
    )

# -----------------------------------------------------------------------------
# Configurações e utilitários
# -----------------------------------------------------------------------------
APP_NAME = "Agenda Boa API"
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")  # placeholder (não validamos JWT aqui)

# CORS
frontend_url = os.getenv("FRONTEND_URL", "").strip()
extra_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

CORS_ALLOW_ORIGINS = []
if frontend_url:
    CORS_ALLOW_ORIGINS.append(frontend_url)
CORS_ALLOW_ORIGINS.extend(extra_origins)
if not CORS_ALLOW_ORIGINS:
    # fallback seguro para testes
    CORS_ALLOW_ORIGINS = ["*"]

# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------
app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

# -----------------------------------------------------------------------------
# Helpers de senha
# -----------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    subdomain: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

# -----------------------------------------------------------------------------
# Startup: cria tabelas e Super Admin
# -----------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    create_tables()
    if ADMIN_EMAIL and ADMIN_PASSWORD:
        db = SessionLocal()
        try:
            # procura por super admin com e-mail configurado
            super_admin = (
                db.query(User)
                .filter(User.email == ADMIN_EMAIL)
                .filter(User.role == "super_admin")
                .first()
            )
            if not super_admin:
                sa = User(
                    id=str(uuid.uuid4()),
                    email=ADMIN_EMAIL,
                    name="Super Admin",
                    hashed_password=hash_password(ADMIN_PASSWORD),
                    role="super_admin",
                    is_active=True,
                    tenant_id=None,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(sa)
                db.commit()
                logger.info("Super admin created")
            else:
                logger.info("Super admin exists")
        finally:
            db.close()
    else:
        logger.warning("ADMIN_EMAIL/ADMIN_PASSWORD não configurados — pulando criação do Super Admin.")

# -----------------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}

# -----------------------------------------------------------------------------
# Aux: busca usuário (super admin ou por subdomínio)
# -----------------------------------------------------------------------------
def find_user_for_login(db: Session, email: str, subdomain: Optional[str]) -> Optional[User]:
    q = db.query(User)
    if subdomain and subdomain.strip():
        # login empresarial: filtra por tenant (subdomínio)
        tenant = db.query(Tenant).filter(Tenant.subdomain == subdomain.strip()).first()
        if not tenant:
            return None
        return q.filter(User.email == email, User.tenant_id == tenant.id).first()
    else:
        # login como Super Admin
        return q.filter(User.email == email, User.role == "super_admin", User.tenant_id.is_(None)).first()

# -----------------------------------------------------------------------------
# Login
# -----------------------------------------------------------------------------
@app.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = find_user_for_login(db, payload.email, payload.subdomain)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    # token simples para o front (se quiser JWT real, adicionar python-jose e assinar)
    token = f"token-{uuid.uuid4()}"
    user_dict = {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
    }
    return LoginResponse(access_token=token, user=user_dict)

# -----------------------------------------------------------------------------
# Rota utilitária para verificar qual build está rodando
# -----------------------------------------------------------------------------
@app.get("/__whoami")
def whoami():
    return {
        "app": APP_NAME,
        "time": datetime.now(timezone.utc).isoformat(),
        "allow_origins": CORS_ALLOW_ORIGINS,
        "has_admin_env": bool(ADMIN_EMAIL and ADMIN_PASSWORD),
    }
