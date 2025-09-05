# backend_test.py (PT-BR vars) — lê E-MAIL_ADMINISTRATIVO/SENHA_ADMIN
import os, sys, json
from datetime import datetime
import requests

def get_env_any(names, default=None):
    for n in names:
        v = os.getenv(n)
        if v and str(v).strip():
            return v
    return default

API_BASE_URL = get_env_any(["API_BASE_URL"], "http://localhost:8080/api")

ADMIN_EMAIL = get_env_any(["E-MAIL_ADMINISTRATIVO","EMAIL_ADMINISTRATIVO","E_MAIL_ADMINISTRATIVO","ADMIN_EMAIL"], "admin@sistema.com")
ADMIN_PASSWORD = get_env_any(["SENHA_ADMIN","ADMIN_PASSWORD"], "admin123")

TENANT_ADMIN_PASSWORD = get_env_any(["TENANT_ADMIN_PASSWORD"], "tenant123")
TEST_SUBDOMAIN = get_env_any(["TEST_SUBDOMAIN"], f"qa-{datetime.now().strftime('%Y%m%d%H%M%S')}")
TENANT_ADMIN_EMAIL = get_env_any(["TENANT_ADMIN_EMAIL"], f"admin+{TEST_SUBDOMAIN}@empresa.com")

def headers(token=None):
    h = {"Content-Type":"application/json","Accept":"application/json"}
    if token: h["Authorization"] = f"Bearer {token}"
    return h

def url(ep): return f"{API_BASE_URL}/{ep.lstrip('/')}"

def post(ep, data, token=None, expect=200):
    r = requests.post(url(ep), headers=headers(token), json=data, timeout=30)
    ok = r.status_code==expect
    return ok, (r.json() if ok else {"status":r.status_code, "text":r.text[:300]})

def get(ep, token=None, expect=200):
    r = requests.get(url(ep), headers=headers(token), timeout=30)
    ok = r.status_code==expect
    return ok, (r.json() if ok else {"status":r.status_code, "text":r.text[:300]})

def main():
    print("API_BASE_URL:", API_BASE_URL)

    # 1) login super admin
    ok, j = post("auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, expect=200)
    if not ok: print("Falha login super admin", j); return 1
    super_token = j["access_token"]; print("✔ super admin logado")

    # 2) tenants list ou create
    ok, tenants = get("super-admin/tenants", token=super_token)
    if not ok: print("Falha listar tenants", tenants); return 1
    exists = any(t.get("subdomain")==TEST_SUBDOMAIN for t in tenants) if isinstance(tenants, list) else False
    if not exists:
        payload = {
            "subdomain": TEST_SUBDOMAIN,
            "company_name": "Empresa QA",
            "admin_name": "Admin QA",
            "admin_email": TENANT_ADMIN_EMAIL,
            "admin_password": TENANT_ADMIN_PASSWORD,
            "plan": "basic"
        }
        ok, created = post("super-admin/tenants", payload, token=super_token)
        if not ok: print("Falha criar tenant", created); return 1
        print("✔ tenant criado:", TEST_SUBDOMAIN)
    else:
        print("✔ tenant já existe:", TEST_SUBDOMAIN)

    # 3) login admin tenant
    ok, j = post("auth/login", {"email": TENANT_ADMIN_EMAIL, "password": TENANT_ADMIN_PASSWORD, "subdomain": TEST_SUBDOMAIN})
    if not ok: print("Falha login tenant admin", j); return 1
    tenant_token = j["access_token"]; print("✔ tenant admin logado")

    # 4) testes básicos
    for name, fn in [
        ("auth/me", lambda: get("auth/me", token=tenant_token)),
        ("dashboard", lambda: get("dashboard", token=tenant_token)),
        ("clientes (list)", lambda: get("clientes", token=tenant_token)),
        ("produtos (list)", lambda: get("produtos", token=tenant_token)),
        ("servicos (list)", lambda: get("servicos", token=tenant_token)),
    ]:
        ok, resp = fn()
        print("✔" if ok else "✖", name, "→", (resp if ok else resp))

    # 5) criar cliente/produto/serviço rapidamente
    ok, _ = post("clientes", {"nome":"Cliente Teste","email":"teste@ex.com"}, token=tenant_token)
    ok2, _ = post("produtos", {"nome":"Produto Teste","preco":9.9}, token=tenant_token)
    ok3, _ = post("servicos", {"nome":"Serviço Teste","preco":49.9}, token=tenant_token)
    print("Create ->", "clientes" if ok else "", "produtos" if ok2 else "", "servicos" if ok3 else "")

    return 0

if __name__ == "__main__":
    sys.exit(main())
