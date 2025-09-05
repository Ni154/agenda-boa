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

# Silencia apenas o ruído de “relationship conflicts”
warnings.filterwarnings(
    "ignore",
    category=SAWarning,
    message=r".*relationship .* conflicts with relationship.*",
)

# ---------------------------------------------------------------------
# IMPORTANTE: NÃO DEIXE MODELOS AQUI!
# Os modelos ficam somente em database.py
# ---------------------------------------------------------------------
try:
    # server.py e database.py no mesmo pacote (ex.: app/server.py, app/database.py)
    from .database import (
        get_db,
        create_tables,
        SessionLocal,
        Tenant,
        User,
        Vencimento,
    )
except Exception:
    # server.py e database.py lado a lado
    from database import (
        get_db,
        create_tables,
        SessionLocal,
        Tenant,
        User,
        Vencimento,
    )

APP_NAME = "Agenda Boa API"
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Variáveis de ambiente
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")

# CORS
frontend_url = os.getenv("FRONTEND_URL", "").strip()
extra_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
CORS_ALLOW_ORIGINS = []
if frontend_url:
    CORS_ALLOW_ORIGINS.append(frontend_url)
CORS_ALLOW_ORIGINS.extend(extra_origins)
if not CORS_ALLOW_ORIGINS:
    # Em último caso, libera tudo para não travar login em produção
    CORS_ALLOW_ORIGINS = ["*"]

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

# ------------------------------ utils --------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

# ------------------------------ schemas ------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    subdomain: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

# ------------------------------ startup ------------------------------
@app.on_event("startup")
def on_startup():
    # Cria tabelas
    create_tables()

    # Garante Super Admin com as envs
    if ADMIN_EMAIL and ADMIN_PASSWORD:
        db = SessionLocal()
        try:
            super_admin = (
                db.query(User)
                .filter(User.email == ADMIN_EMAIL)
                .filter(User.role == "super_admin")
                .first()
            )
            if not super_admin:
                db.add(
                    User(
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
                )
                db.commit()
                logger.info("Super admin created")
            else:
                logger.info("Super admin exists")
        finally:
            db.close()
    else:
        logger.warning("ADMIN_EMAIL/ADMIN_PASSWORD não configurados — pulando criação do Super Admin.")

# ------------------------------ health -------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}

@app.get("/__whoami")
def whoami():
    return {
        "app": APP_NAME,
        "time": datetime.now(timezone.utc).isoformat(),
        "allow_origins": CORS_ALLOW_ORIGINS,
        "has_admin_env": bool(ADMIN_EMAIL and ADMIN_PASSWORD),
    }

# ------------------------------ login --------------------------------
def find_user_for_login(db: Session, email: str, subdomain: Optional[str]) -> Optional[User]:
    q = db.query(User)
    if subdomain and subdomain.strip():
        tenant = db.query(Tenant).filter(Tenant.subdomain == subdomain.strip()).first()
        if not tenant:
            return None
        return q.filter(User.email == email, User.tenant_id == tenant.id).first()
    else:
        return q.filter(
            User.email == email,
            User.role == "super_admin",
            User.tenant_id.is_(None),
        ).first()

@app.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = find_user_for_login(db, payload.email, payload.subdomain)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = f"token-{uuid.uuid4()}"  # placeholder
    user_dict = {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
    }
    return LoginResponse(access_token=token, user=user_dict)
