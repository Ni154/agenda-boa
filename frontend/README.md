# Agenda Boa — Guia de Deploy (corrigido)

> Este README substitui o anterior e elimina as causas de **502 / 405** (redirecionamento de POST→GET, health 404 e base da API errada).

## O que estava induzindo erro
- Início do servidor diferente do seu layout (ex.: `uvicorn backend.server:app`). O seu arquivo é **server.py** na raiz.
- Base da API no front inconsistente: usar `http://…` ou URL errada provoca **301 → 405** (POST vira GET).
- Healthcheck apontando para rota que **não existia** mantinha o serviço “unhealthy” (502).
- DB com URL “interna” fora do mesmo projeto → timeout no login (502).

---

## Produção — Railway (Backend)

**Start command**
```
uvicorn server:app --host 0.0.0.0 --port $PORT
```

**Healthcheck**
- Recomendo **`/health`** (e manter `/api/health` no código). O importante é retornar **200**.

**Variáveis do backend (use exatamente esses nomes):**
```
URL_DO_BANCO_DE_DADOS=${{ Postgres.DATABASE_URL }}   # conexão interna do Postgres (mesmo projeto)
CORS_ORIGENS_PERMITIDAS=https://agenda-boa.netlify.app
URL_FRONTEND=https://agenda-boa.netlify.app
E-MAIL_ADMINISTRATIVO=nsautomacaoolinda@gmail.com
SENHA_ADMIN=AgendaBoa!2025

# opcionais (email)
REENVIAR_CHAVE_API=Bm7kn19W_9ZSWGeMdPyRg2VguUFMHz8DS
REENVIAR_DE=Sistema ERP <nsautomacaoolinda@gmail.com>

# JWT (opcional; já há default)
JWT_SECRETO=Bm7kn19W_9ZSWGeMdPyRg2VguUFMHz8DS
MINUTOS_EXPIRACAO_TOKEN=1440
```

> **Importante:** deixe **apenas UMA** variável de DB. Não mantenha `DATABASE_URL` paralelo com outro valor.

---

## Produção — Netlify (Frontend)

**Build (site dentro de `/frontend`)**
- Base directory: `frontend`
- Build command: `yarn install --frozen-lockfile || yarn install && yarn build`
- Publish directory: `frontend/build`

**Variáveis do front**
```
REACT_APP_API_BASE_URL=/api
```
> Assim todas as chamadas usam o **proxy** do Netlify via **HTTPS** (evita 301 e 405).

**`frontend/netlify.toml`**
```toml
[build]
  command = "yarn install --frozen-lockfile || yarn install && yarn build"
  publish = "build"

# Proxy de /api para o backend em HTTPS
[[redirects]]
  from = "/api/*"
  to = "https://agenda-boa-production.up.railway.app/api/:splat"
  status = 200
  force = true

# SPA fallback
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

**Alternativa (SPA redirects sem toml)**
Crie `frontend/public/_redirects`:
```
/* /index.html 200
```

---

## Desenvolvimento Local

**Backend**
```
uvicorn server:app --reload --host 0.0.0.0 --port 8000
# Health: http://localhost:8000/health  (200)
# API:    http://localhost:8000/api
```

**Frontend**
```
cd frontend
yarn
REACT_APP_API_BASE_URL=http://localhost:8000/api yarn start
# App: http://localhost:3000
```

---

## Como validar (checklist em 60s)
1. Abra `https://agenda-boa-production.up.railway.app/health` → **200**  
   (se o Healthcheck configurado for `/api/health`, teste esse também).  
2. Na página do Netlify (F12 → Console):
   ```js
   fetch('/api/health').then(r=>r.text()).then(console.log)
   ```
   Deve imprimir JSON.  
3. Clique **Entrar**. Agora o login responde **200/401**, nunca mais **502/405**.  
   - **Se 405 surgir**: o Network mostrará **301** anterior. Ajuste a base (sempre `https://…` **ou** `/api`).  
   - **Se 502 surgir**: revise a `URL_DO_BANCO_DE_DADOS` (placeholder interno **exatamente** como acima e no mesmo projeto do Postgres).

---

## Resumo
- Front: **`REACT_APP_API_BASE_URL=/api`** + proxy para **HTTPS**.
- Backend: **`uvicorn server:app --port $PORT`**, health **existe** e DB via **`${{ Postgres.DATABASE_URL }}`**.
- Evite `http://` em produção; sem barra extra nas rotas (`/api/auth/login`, sem `/` final).
