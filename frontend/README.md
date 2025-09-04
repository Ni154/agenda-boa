# Agenda Boa — Frontend (Netlify) + Backend (Railway)

[![Netlify Status](https://api.netlify.com/api/v1/badges/706a528b-0787-4188-8ef3-1b707ea31d43/deploy-status)](https://app.netlify.com/projects/agenda-boa/deploys)

Guia rápido para desenvolvimento local e deploy em **Netlify** (frontend) e **Railway** (backend). Projeto baseado em Create React App + CRACO.

---

## ⚙️ Variáveis de Ambiente

### Frontend (Netlify / desenvolvimento)
- **`REACT_APP_BACKEND_URL`** → URL base do backend **sem** `/api` no final.  
  - Ex.: Produção (Railway): `https://SEU-BACKEND.up.railway.app`  
  - Ex.: Local: `http://localhost:8000`

> O código já usa `process.env.REACT_APP_BACKEND_URL` e **acrescenta `/api`** internamente:
> ```js
> const BACKEND_URL = process.env.REACT_APP_BACKEND_URL
> const API = `${BACKEND_URL}/api`
> ```

### Backend (Railway)
- **`DATABASE_URL`** → sua conexão Postgres (Railway)  
- **`RESEND_API_KEY`** → sua chave Resend
- **`RESEND_FROM`** → remetente (ex.: `ERP Sistema <seu-email@dominio.com>`)
- **`CORS_ORIGINS`** (ou `CORS_ALLOWED_ORIGINS`) → URL do seu site no Netlify
- **`JWT_SECRET`** → (opcional) segredo do JWT

---

## 🖥️ Desenvolvimento Local

### 1) Backend
Na raiz do projeto:
```bash
uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000
```
- Healthcheck: `GET http://localhost:8000/health`  
- API base: `http://localhost:8000/api`

> Certifique-se de exportar as variáveis do backend ou usar um `.env` em `backend/`.

### 2) Frontend
No diretório `frontend/`:
```bash
npm install
# em seguida:
REACT_APP_BACKEND_URL=http://localhost:8000 npm start
```
App em: http://localhost:3000

---

## 🚀 Deploy

### Netlify (Frontend)
**Opção A (site apontando para `/frontend`)**  
- **Base directory:** `frontend`  
- **Build command:** `npm run build`  
- **Publish directory:** `build`  
- **Env vars:** defina **`REACT_APP_BACKEND_URL`** com a URL pública do seu backend no Railway.

**Opção B (raiz do repositório)**  
- **Build command:** `npm --prefix frontend run build`  
- **Publish directory:** `frontend/build`  
- **Env vars:** `REACT_APP_BACKEND_URL`

**SPA Redirects**  
Adicione (se já não existir) o arquivo `frontend/public/_redirects` com:
```
/* /index.html 200
```

### Railway (Backend)
- Use o **Procfile** (ou comando de start):
  ```
  web: uvicorn backend.server:app --host 0.0.0.0 --port $PORT
  ```
- Tenha `runtime.txt` (ex.: `python-3.12.11`) e `requirements.txt` na raiz (pode referenciar `backend/requirements.txt`).  
- Defina as variáveis de ambiente citadas acima e faça o deploy.

---

## ✅ Pós-deploy: Checklist Rápido
- Acesse `{
'}}BACKEND_URL{{'}
/health` → deve retornar `{"status":"ok"}`.  
- Frontend no Netlify carrega sem erros.  
- Fluxos do sistema (login, CRUDs, POS, agendamentos) **funcionam** usando a API do Railway.  
- Envio de e-mail (Resend) OK. Se houver restrição de domínio/remetente, verifique a **verificação de domínio** no Resend.  
- CORS: se aparecer erro de CORS, confirme `CORS_ORIGINS`/`CORS_ALLOWED_ORIGINS` no Railway com a URL do Netlify.

---

## 🧭 Estrutura (resumo)
```
/
├── backend/
│   ├── server.py          # FastAPI (app = FastAPI(...))
│   ├── database.py
│   ├── requirements.txt
│   ├── __init__.py
│   └── .env.example
├── frontend/
│   ├── public/
│   │   ├── index.html
│   │   └── _redirects
│   ├── src/
│   ├── package.json       # scripts: craco start/build/test
│   └── .env.example       # REACT_APP_BACKEND_URL
├── Procfile
├── runtime.txt
├── requirements.txt       # referencia backend/requirements.txt
└── CHANGELOG.md
```

---

## 🆘 Troubleshooting
- **Tela em branco no Netlify** → verifique `REACT_APP_BACKEND_URL` e o `_redirects`.  
- **CORS** → confirme `CORS_ORIGINS` (ou `CORS_ALLOWED_ORIGINS`) no Railway com a URL exata do Netlify.  
- **401/403** → verifique token JWT no `localStorage` e interceptors do Axios.  
- **E-mail não enviado** → valide `RESEND_API_KEY`/`RESEND_FROM` e a verificação de domínio no Resend.

---

_Atualizado em: 2025-09-04 17:30:29_
