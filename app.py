
# app_streamlit_completo_v5.txt
# Execute: streamlit run app_streamlit_completo_v5.txt

import streamlit as st
import sqlite3, os, io, base64, urllib.parse, shutil
import pandas as pd
from datetime import datetime, date
from PIL import Image

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Studio - ERP Completo", layout="wide")

# --------------- CONEXÃO / DB ---------------
@st.cache_resource
def get_conn():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

conn = get_conn()
cursor = conn.cursor()

def criar_tabelas():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        senha TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS empresa (
        id INTEGER PRIMARY KEY,
        nome TEXT,
        cnpj TEXT,
        telefone TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        telefone TEXT,
        email TEXT,
        endereco TEXT,
        alergia_flag INTEGER DEFAULT 0,
        alergia_desc TEXT,
        cirurgia_flag INTEGER DEFAULT 0,
        cirurgia_desc TEXT,
        autoriza_imagem INTEGER DEFAULT 0,
        assinatura BLOB,
        foto BLOB
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cod TEXT UNIQUE,
        nome TEXT UNIQUE,
        quantidade INTEGER DEFAULT 0,
        preco_custo REAL DEFAULT 0,
        preco_venda REAL DEFAULT 0,
        unidade TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        valor REAL DEFAULT 0,
        tempo_sessao_min INTEGER DEFAULT 0,
        gera_estoque INTEGER DEFAULT 0,
        estoque_qtd INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agendamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        data TEXT,
        hora TEXT,
        servicos TEXT,
        status TEXT,
        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        data TEXT,
        total REAL,
        cancelada INTEGER DEFAULT 0,
        forma_pagamento TEXT,
        origem TEXT,              -- 'nova' ou 'agendamento:<id>'
        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS venda_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER,
        tipo TEXT,          -- 'produto' ou 'servico'
        item_id INTEGER,
        quantidade INTEGER,
        preco REAL,
        FOREIGN KEY(venda_id) REFERENCES vendas(id)
    )
    """)
    # Despesas + fornecedor e cabeçalho completo
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_nota TEXT,             -- 'Produtos' ou 'Serviços'
        numero_nota TEXT,
        data_compra TEXT,           -- para Produtos
        data_emissao TEXT,          -- para Serviços
        data_entrada TEXT,          -- para Serviços
        fornecedor_nome TEXT,
        fornecedor_cnpj TEXT,
        fornecedor_endereco TEXT,
        fornecedor_telefone TEXT,
        chave_nfe_text TEXT,
        chave_nfe_img BLOB,
        valor_total REAL,
        descricao TEXT              -- campo livre (opcional)
    )
    """)
    # Itens da despesa (produtos)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesa_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        despesa_id INTEGER NOT NULL,
        cod_produto TEXT,
        produto_nome TEXT,
        tipo_produto TEXT,         -- 'Revenda' | 'Uso e consumo' | 'Matéria-prima'
        quantidade INTEGER,
        custo_unit REAL,
        preco_venda REAL,          -- obrigatório se tipo_produto = 'Revenda'
        FOREIGN KEY(despesa_id) REFERENCES despesas(id)
    )
    """)
    # Itens de serviços na nota
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesa_servico_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        despesa_id INTEGER NOT NULL,
        servico_desc TEXT,
        quantidade INTEGER,
        custo_unit REAL,
        FOREIGN KEY(despesa_id) REFERENCES despesas(id)
    )
    """)
    conn.commit()

def upgrade_colunas():
    # garantir colunas novas em bancos antigos
    alters = [
        ("ALTER TABLE produtos ADD COLUMN cod TEXT", "produtos", "cod"),
        ("ALTER TABLE produtos ADD COLUMN preco_custo REAL", "produtos", "preco_custo"),
        ("ALTER TABLE produtos ADD COLUMN unidade TEXT", "produtos", "unidade"),
        ("ALTER TABLE vendas ADD COLUMN origem TEXT", "vendas", "origem"),
        ("ALTER TABLE servicos ADD COLUMN tempo_sessao_min INTEGER", "servicos", "tempo_sessao_min"),
        ("ALTER TABLE servicos ADD COLUMN gera_estoque INTEGER", "servicos", "gera_estoque"),
        ("ALTER TABLE servicos ADD COLUMN estoque_qtd INTEGER", "servicos", "estoque_qtd"),
        ("ALTER TABLE despesas ADD COLUMN tipo_nota TEXT", "despesas", "tipo_nota"),
        ("ALTER TABLE despesas ADD COLUMN numero_nota TEXT", "despesas", "numero_nota"),
        ("ALTER TABLE despesas ADD COLUMN data_compra TEXT", "despesas", "data_compra"),
        ("ALTER TABLE despesas ADD COLUMN data_emissao TEXT", "despesas", "data_emissao"),
        ("ALTER TABLE despesas ADD COLUMN data_entrada TEXT", "despesas", "data_entrada"),
        ("ALTER TABLE despesas ADD COLUMN fornecedor_endereco TEXT", "despesas", "fornecedor_endereco"),
        ("ALTER TABLE despesas ADD COLUMN chave_nfe_text TEXT", "despesas", "chave_nfe_text"),
        ("ALTER TABLE despesas ADD COLUMN chave_nfe_img BLOB", "despesas", "chave_nfe_img"),
        ("ALTER TABLE despesa_itens ADD COLUMN cod_produto TEXT", "despesa_itens", "cod_produto"),
        ("ALTER TABLE despesa_itens ADD COLUMN tipo_produto TEXT", "despesa_itens", "tipo_produto"),
        ("ALTER TABLE despesa_itens ADD COLUMN preco_venda REAL", "despesa_itens", "preco_venda"),
        ("ALTER TABLE empresa ADD COLUMN telefone TEXT", "empresa", "telefone"),
    ]
    for sql, table, col in alters:
        try:
            cursor.execute(f"SELECT {col} FROM {table} LIMIT 1")
        except Exception:
            try:
                cursor.execute(sql); conn.commit()
            except Exception:
                pass

criar_tabelas()
upgrade_colunas()

def criar_usuario_padrao():
    if not cursor.execute("SELECT 1 FROM usuarios WHERE usuario='admin'").fetchone():
        cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES ('admin','admin')")
        conn.commit()
criar_usuario_padrao()

# ---------------- HELPERS ----------------
def moeda(v):
    try:
        return f"R$ {float(v):,.2f}".replace(\",\", \"X\").replace(\".\", \",\").replace(\"X\", \".\")
    except Exception:
        return "R$ 0,00"

def data_br(s):
    try:
        return datetime.fromisoformat(s).strftime("%d/%m/%Y %H:%M")
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return str(s)

def get_empresa():
    row = cursor.execute("SELECT COALESCE(nome,''), COALESCE(cnpj,''), COALESCE(telefone,'') FROM empresa WHERE id=1").fetchone()
    if row:
        return {"nome":row[0], "cnpj":row[1], "telefone":row[2]}
    else:
        return {"nome":"", "cnpj":"", "telefone":""}

def upsert_produto_estoque_por_codigo(cod, nome, qtd, custo_unit, preco_venda=None):
    # atualiza/adiciona produto no estoque usando COD
    row = cursor.execute("SELECT id, quantidade FROM produtos WHERE cod = ?", (cod,)).fetchone()
    if row:
        cursor.execute("UPDATE produtos SET quantidade = COALESCE(quantidade,0)+?, preco_custo=?, preco_venda=COALESCE(?, preco_venda) WHERE id=?",
                       (int(qtd), float(custo_unit), preco_venda, row[0]))
    else:
        cursor.execute("INSERT INTO produtos (cod, nome, quantidade, preco_custo, preco_venda) VALUES (?,?,?,?,?)",
                       (cod, nome or cod, int(qtd), float(custo_unit), float(preco_venda or 0.0)))
    conn.commit()

def baixar_estoque(item_id, quantidade):
    cursor.execute("UPDATE produtos SET quantidade = MAX(0, COALESCE(quantidade,0)-?) WHERE id=?", (int(quantidade), item_id))
    conn.commit()

def gerar_pdf_venda(venda_id:int):
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
    except Exception as e:
        return None, f"Faltando reportlab ({e})"

    venda = cursor.execute("""
        SELECT v.id, v.data, COALESCE(c.nome,'Cliente'), v.forma_pagamento, v.total
        FROM vendas v LEFT JOIN clientes c ON c.id=v.cliente_id WHERE v.id=?
    """, (venda_id,)).fetchone()
    itens = cursor.execute("""
        SELECT vi.tipo, vi.quantidade, vi.preco,
               CASE WHEN vi.tipo='produto' THEN p.nome ELSE s.nome END AS nome_item
        FROM venda_itens vi
        LEFT JOIN produtos p ON vi.tipo='produto' AND p.id=vi.item_id
        LEFT JOIN servicos s ON vi.tipo='servico' AND s.id=vi.item_id
        WHERE vi.venda_id=?
    """, (venda_id,)).fetchall()
    if not venda:
        return None, "Venda não encontrada."

    emp = get_empresa()

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w,h = A4
    y = h - 20*mm

    # Cabeçalho com Empresa
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20*mm, y, emp.get("nome",""))
    y -= 6*mm
    c.setFont("Helvetica", 9)
    c.drawString(20*mm, y, f"CNPJ: {emp.get('cnpj','')}  |  Tel: {emp.get('telefone','')}")
    y -= 10*mm

    c.setFont("Helvetica-Bold", 14); c.drawString(20*mm, y, "Comprovante de Venda"); y -= 10*mm
    c.setFont("Helvetica", 10)
    c.drawString(20*mm, y, f"Venda #{venda[0]}  |  Data: {data_br(venda[1])}"); y -= 6*mm
    c.drawString(20*mm, y, f"Cliente: {venda[2]}"); y -= 6*mm
    c.drawString(20*mm, y, f"Pagamento: {venda[3]}"); y -= 8*mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(20*mm, y, "Item"); c.drawString(110*mm, y, "Qtd"); c.drawString(130*mm, y, "Preço"); c.drawString(160*mm, y, "Subtotal")
    y -= 5*mm; c.line(20*mm, y, 190*mm, y); y -= 5*mm; c.setFont("Helvetica", 10)
    total = 0.0
    for tipo, qtd, preco, nome_item in itens:
        if y < 30*mm: c.showPage(); y = h - 20*mm; c.setFont("Helvetica", 10)
        subt = (qtd or 0)*(preco or 0.0); total += subt
        c.drawString(20*mm, y, f"{nome_item} ({tipo})")
        c.drawRightString(125*mm, y, str(qtd))
        c.drawRightString(155*mm, y, moeda(preco))
        c.drawRightString(190*mm, y, moeda(subt))
        y -= 6*mm
    y -= 6*mm; c.setFont("Helvetica-Bold", 12); c.drawRightString(190*mm, y, f"TOTAL: {moeda(total)}")
    c.showPage(); c.save()
    return buf.getvalue(), None

# ---------------- LOGIN (centralizado) ---------------
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.markdown("""
        <style>
        .center-box {display:flex; align-items:center; justify-content:center; height:75vh;}
        .login-card {max-width:420px; width:100%; padding:24px; border:1px solid #eee; border-radius:16px; box-shadow:0 6px 24px rgba(0,0,0,.06); background:white;}
        .login-title {text-align:center; font-size:1.4rem; font-weight:700; margin-bottom:12px;}
        .login-sub {text-align:center; color:#666; margin-bottom:16px;}
        </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="center-box"><div class="login-card">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">🔐 Acesso ao Sistema</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Entre com suas credenciais</div>', unsafe_allow_html=True)
    usuario_input = st.text_input("Usuário")
    senha_input = st.text_input("Senha", type="password")
    c1,c2 = st.columns([1,1])
    if c1.button("Entrar", type="primary"):
        if cursor.execute("SELECT 1 FROM usuarios WHERE usuario=? AND senha=?", (usuario_input, senha_input)).fetchone():
            st.session_state.login = True
            st.session_state["menu"] = "Início"  # começa no Início
            st.experimental_rerun()
        else:
            st.error("Usuário ou senha inválidos")
    if c2.button("Esqueci"):
        st.info("Usuário padrão: admin / Senha: admin")
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.stop()

# --------------- SIDEBAR ---------------
with st.sidebar:
    if "logo_img" in st.session_state:
        st.image(st.session_state["logo_img"], width=150)
    elif os.path.exists("logo_studio.png"):
        with open("logo_studio.png", "rb") as f:
            st.session_state["logo_img"] = f.read()
        st.image(st.session_state["logo_img"], width=150)
    else:
        st.image("https://via.placeholder.com/150x100.png?text=LOGO", width=150)

    st.write("📎 **Importar nova logo:**")
    upl = st.file_uploader("Importar Logo", type=["png","jpg","jpeg"])
    if upl:
        b = upl.read()
        with open("logo_studio.png","wb") as f: f.write(b)
        st.session_state["logo_img"] = b
        st.success("Logo atualizada!")

    menu_opcoes = [
        "Início", "Dashboard", "Cadastro Cliente", "Cadastro Empresa", "Cadastro Produtos",
        "Cadastro Serviços", "Agendamento", "Vendas", "Despesas", "Relatórios", "Backup", "Sair"
    ]
    icones = {"Início":"🏠","Dashboard":"📈","Cadastro Cliente":"🧍","Cadastro Empresa":"🏢","Cadastro Produtos":"📦",
              "Cadastro Serviços":"💆","Agendamento":"📅","Vendas":"💰","Despesas":"💸",
              "Relatórios":"📊","Backup":"💾","Sair":"🔓"}
    for opc in menu_opcoes:
        if st.button(f"{icones.get(opc,'📌')} {opc}"):
            st.session_state["menu"] = opc

menu = st.session_state.get("menu", "Início")
st.title(f"🧭 {menu}")

# --------------- PÁGINAS ---------------
# Início: agendamentos com nome, status e data + link WhatsApp
if menu == "Início":
    st.subheader("📅 Agendamentos do Período")
    data_inicio = st.date_input("De", date.today(), format="DD/MM/YYYY")
    data_fim = st.date_input("Até", date.today(), format="DD/MM/YYYY")
    if data_inicio > data_fim:
        st.error("Data inicial não pode ser maior que a final.")
    else:
        a = data_inicio.strftime("%Y-%m-%d"); b = data_fim.strftime("%Y-%m-%d")
        ags = cursor.execute("""
            SELECT a.id, c.nome, a.data, a.hora, a.servicos, a.status, c.telefone
            FROM agendamentos a JOIN clientes c ON a.cliente_id=c.id
            WHERE a.data BETWEEN ? AND ? ORDER BY a.data, a.hora
        """, (a,b)).fetchall()
        if ags:
            for ag in ags:
                msg = urllib.parse.quote(f"Olá {ag[1]}, confirmando seu agendamento em {data_br(ag[2])} às {ag[3]}.")
                tel = ''.join([d for d in (ag[6] or "") if d.isdigit()])
                wa = f"https://wa.me/55{tel}?text={msg}" if tel else None
                col = st.columns([6,1])
                col[0].info(f"📅 {data_br(ag[2])} 🕒 {ag[3]} | 👤 {ag[1]} | 📌 Status: {ag[5]} | 💼 {ag[4]}")
                if wa:
                    col[1].markdown(f"[WhatsApp](%s)" % wa)
        else:
            st.warning("Nenhum agendamento no período.")

# Dashboard simples
elif menu == "Dashboard":
    st.subheader("📊 Visão Geral")
    total_clientes = cursor.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    total_vendas = cursor.execute("SELECT COUNT(*) FROM vendas WHERE cancelada=0").fetchone()[0]
    total_produtos = cursor.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
    total_servicos = cursor.execute("SELECT COUNT(*) FROM servicos").fetchone()[0]
    total_despesas = cursor.execute("SELECT COALESCE(SUM(valor_total),0) FROM despesas").fetchone()[0]
    total_faturamento = cursor.execute("SELECT COALESCE(SUM(total),0) FROM vendas WHERE cancelada=0").fetchone()[0]
    lucro = total_faturamento - total_despesas

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("👥 Clientes", total_clientes)
    c2.metric("🧾 Vendas", total_vendas)
    c3.metric("📦 Produtos", total_produtos)
    c4.metric("💆 Serviços", total_servicos)
    st.metric("💰 Faturamento", moeda(total_faturamento))
    st.metric("💸 Despesas", moeda(total_despesas))
    st.metric("📈 Lucro", moeda(lucro))

# Cadastro Cliente (reativo)
elif menu == "Cadastro Cliente":
    st.subheader("🧍 Cadastro de Clientes")
    try:
        from streamlit_drawable_canvas import st_canvas
        has_canvas = True
    except Exception:
        has_canvas = False
        st.warning("Para assinatura digital, instale: pip install streamlit-drawable-canvas")

    nome = st.text_input("Nome")
    telefone = st.text_input("Telefone (WhatsApp)")
    email = st.text_input("E-mail")
    endereco = st.text_input("Endereço")
    alergia_flag = st.checkbox("Possui algum tipo de alergia?")
    alergia_desc = st.text_input("Descreva o tipo de alergia", disabled=not alergia_flag)
    cirurgia_flag = st.checkbox("Passou por cirurgia?")
    cirurgia_desc = st.text_input("Descreva a cirurgia", disabled=not cirurgia_flag)
    autoriza_imagem = st.checkbox("Autoriza o uso da imagem?")

    st.markdown("**Assinatura digital** — _“Confirmo as informações acima no cadastro.”_")
    assinatura_bytes = None
    if has_canvas:
        canvas = st_canvas(stroke_width=2, stroke_color="#000000", background_color="#FFFFFF",
                           height=150, width=300, drawing_mode="freedraw", key="canvas_sig_v5")
        if canvas.image_data is not None:
            import numpy as np
            from PIL import Image
            img = Image.fromarray((canvas.image_data).astype("uint8"))
            buf = io.BytesIO(); img.save(buf, format="PNG"); assinatura_bytes = buf.getvalue()

    st.markdown("**Foto 3x4**")
    foto_bytes = None
    modo_foto = st.radio("Origem da foto", ["Nenhuma","Câmera","Galeria"], horizontal=True)
    if modo_foto == "Câmera":
        cam = st.camera_input("Tirar foto (clique para ativar)")
        if cam: foto_bytes = cam.getvalue()
    elif modo_foto == "Galeria":
        up = st.file_uploader("Enviar foto 3x4", type=["png","jpg","jpeg"])
        if up: foto_bytes = up.read()

    if st.button("Salvar Cliente", type="primary"):
        if nome.strip():
            cursor.execute("""
                INSERT INTO clientes (nome, telefone, email, endereco, alergia_flag, alergia_desc, cirurgia_flag, cirurgia_desc, autoriza_imagem, assinatura, foto)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (nome.strip(), telefone.strip(), email.strip(), endereco.strip(),
                  int(alergia_flag), alergia_desc.strip() if alergia_flag else "",
                  int(cirurgia_flag), cirurgia_desc.strip() if cirurgia_flag else "",
                  int(autoriza_imagem), assinatura_bytes, foto_bytes))
            conn.commit()
            st.success("Cliente salvo!")
        else:
            st.error("Informe o nome.")

    dfc = pd.read_sql_query("""
        SELECT id, nome, telefone, email, endereco, 
               CASE alergia_flag WHEN 1 THEN 'Sim' ELSE 'Não' END AS alergia,
               CASE cirurgia_flag WHEN 1 THEN 'Sim' ELSE 'Não' END AS cirurgia,
               CASE autoriza_imagem WHEN 1 THEN 'Sim' ELSE 'Não' END AS autoriza
        FROM clientes ORDER BY id DESC
    """, conn)
    st.dataframe(dfc, use_container_width=True)

# Cadastro Empresa
elif menu == "Cadastro Empresa":
    st.subheader("🏢 Cadastro da Empresa")
    emp = get_empresa()
    nome = st.text_input("Nome da empresa", value=emp.get("nome",""))
    cnpj = st.text_input("CNPJ", value=emp.get("cnpj",""))
    telefone = st.text_input("Telefone", value=emp.get("telefone",""))
    if st.button("Salvar dados da empresa"):
        if cursor.execute("SELECT 1 FROM empresa WHERE id=1").fetchone():
            cursor.execute("UPDATE empresa SET nome=?, cnpj=?, telefone=? WHERE id=1", (nome, cnpj, telefone))
        else:
            cursor.execute("INSERT INTO empresa (id, nome, cnpj, telefone) VALUES (1, ?, ?, ?)", (nome, cnpj, telefone))
        conn.commit()
        st.success("Empresa salva/atualizada!")

# Cadastro Produtos com histórico + editar/excluir + novos campos
elif menu == "Cadastro Produtos":
    st.subheader("📦 Produtos")
    if "edit_prod_id" not in st.session_state:
        st.session_state.edit_prod_id = None

    col1,col2 = st.columns([1,2])
    with col1:
        cod = st.text_input("Código do produto")
        nome = st.text_input("Nome do produto")
        preco_custo = st.number_input("Preço de custo (R$)", min_value=0.0, step=0.5, format="%.2f")
        preco_venda = st.number_input("Preço de venda (R$)", min_value=0.0, step=0.5, format="%.2f")
        unidade = st.text_input("Unidade (ex: un, cx, kg)")
        quantidade = st.number_input("Quantidade", min_value=0, step=1, value=0)
        if st.button("Salvar/Atualizar Produto"):
            if nome.strip():
                try:
                    cursor.execute("""
                        INSERT INTO produtos (cod, nome, quantidade, preco_custo, preco_venda, unidade)
                        VALUES (?,?,?,?,?,?)
                    """, (cod.strip() or None, nome.strip(), int(quantidade), float(preco_custo), float(preco_venda), unidade.strip() or None))
                except sqlite3.IntegrityError:
                    # update by nome or cod
                    if cod.strip():
                        cursor.execute("""
                            UPDATE produtos SET quantidade=COALESCE(quantidade,0)+?, preco_custo=?, preco_venda=?, unidade=?
                            WHERE cod=?
                        """, (int(quantidade), float(preco_custo), float(preco_venda), unidade.strip() or None, cod.strip()))
                    else:
                        cursor.execute("""
                            UPDATE produtos SET quantidade=COALESCE(quantidade,0)+?, preco_custo=?, preco_venda=?, unidade=?
                            WHERE nome=?
                        """, (int(quantidade), float(preco_custo), float(preco_venda), unidade.strip() or None, nome.strip()))
                conn.commit()
                st.success("Produto salvo/atualizado!")
            else:
                st.error("Informe o nome.")
    with col2:
        st.write("### Histórico de Produtos")
        prods = cursor.execute("SELECT id, cod, nome, quantidade, preco_custo, preco_venda, unidade FROM produtos ORDER BY nome").fetchall()
        if not prods:
            st.info("Nenhum produto cadastrado.")
        else:
            for pid, pcod, pnome, pqtd, pcusto, ppreco, puni in prods:
                c = st.columns([5,2,2,2,1,1])
                c[0].write(f"{pnome}  \n`COD:` {pcod or '-'}  |  `UN:` {puni or '-'}")
                c[1].write(int(pqtd or 0))
                c[2].write(moeda(pcusto or 0))
                c[3].write(moeda(ppreco or 0))
                if c[4].button("✏️", key=f"edit_prod_{pid}"):
                    st.session_state.edit_prod_id = pid
                if c[5].button("❌", key=f"del_prod_{pid}"):
                    cursor.execute("DELETE FROM produtos WHERE id=?", (pid,))
                    conn.commit()
                    st.warning(f"Produto '{pnome}' excluído."); st.rerun()
                if st.session_state.edit_prod_id == pid:
                    with st.expander(f"Editar: {pnome}", expanded=True):
                        novo_cod = st.text_input("Código", value=pcod or "", key=f"ec_{pid}")
                        novo_nome = st.text_input("Nome", value=pnome, key=f"en_{pid}")
                        nova_qtd = st.number_input("Quantidade", min_value=0, step=1, value=int(pqtd or 0), key=f"eq_{pid}")
                        novo_custo = st.number_input("Preço de custo (R$)", min_value=0.0, step=0.5, value=float(pcusto or 0.0), format="%.2f", key=f"ecu_{pid}")
                        novo_preco = st.number_input("Preço de venda (R$)", min_value=0.0, step=0.5, value=float(ppreco or 0.0), format="%.2f", key=f"ep_{pid}")
                        nova_un = st.text_input("Unidade", value=puni or "", key=f"eu_{pid}")
                        cols = st.columns(2)
                        if cols[0].button("Salvar alterações", key=f"save_{pid}"):
                            try:
                                cursor.execute("UPDATE produtos SET cod=?, nome=?, quantidade=?, preco_custo=?, preco_venda=?, unidade=? WHERE id=?",
                                               (novo_cod.strip() or None, novo_nome.strip(), int(nova_qtd), float(novo_custo), float(novo_preco), nova_un.strip() or None, pid))
                                conn.commit(); st.success("Produto atualizado!"); st.session_state.edit_prod_id = None; st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("Código ou Nome já existe. Escolha outro.")
                        if cols[1].button("Cancelar", key=f"cancel_{pid}"):
                            st.session_state.edit_prod_id = None; st.rerun()

# Cadastro Serviços (com tempo de sessão, estoque, editar/excluir)
elif menu == "Cadastro Serviços":
    st.subheader("💆 Serviços")
    col1,col2 = st.columns([1,2])
    with col1:
        nome = st.text_input("Nome do serviço")
        valor = st.number_input("Valor (R$)", min_value=0.0, step=0.5, format="%.2f")
        tempo = st.number_input("Tempo de sessão (min)", min_value=0, step=5, value=0)
        gera_estoque = st.checkbox("Gerar estoque para este serviço?")
        estoque_qtd = st.number_input("Qtd. inicial de estoque (pacotes/sessões)", min_value=0, step=1, value=0, disabled=not gera_estoque)
        if st.button("Salvar Serviço"):
            if nome.strip():
                cursor.execute("""
                    INSERT INTO servicos (nome, valor, tempo_sessao_min, gera_estoque, estoque_qtd) VALUES (?,?,?,?,?)
                """, (nome.strip(), float(valor), int(tempo), int(gera_estoque), int(estoque_qtd)))
                conn.commit(); st.success("Serviço salvo!")
            else:
                st.error("Informe o nome.")
    with col2:
        st.write("### Serviços cadastrados")
        rows = cursor.execute("SELECT id, nome, valor, tempo_sessao_min, gera_estoque, estoque_qtd FROM servicos ORDER BY nome").fetchall()
        if rows:
            for sid, snome, sval, stempo, sgera, sqtd in rows:
                c = st.columns([5,2,2,2,1,1])
                c[0].write(f"**{snome}**  \nValor: {moeda(sval)}  |  Sessão: {stempo} min  |  Gera estoque: {'Sim' if sgera else 'Não'} ({sqtd})")
                if c[4].button("✏️", key=f"edit_srv_{sid}"):
                    st.session_state["edit_srv"] = sid
                if c[5].button("❌", key=f"del_srv_{sid}"):
                    cursor.execute("DELETE FROM servicos WHERE id=?", (sid,)); conn.commit(); st.warning("Serviço excluído."); st.rerun()
                if st.session_state.get("edit_srv") == sid:
                    with st.expander(f"Editar: {snome}", expanded=True):
                        en = st.text_input("Nome", value=snome, key=f"s_en_{sid}")
                        ev = st.number_input("Valor (R$)", min_value=0.0, step=0.5, value=float(sval or 0.0), format="%.2f", key=f"s_ev_{sid}")
                        et = st.number_input("Tempo de sessão (min)", min_value=0, step=5, value=int(stempo or 0), key=f"s_et_{sid}")
                        eg = st.checkbox("Gerar estoque para este serviço?", value=bool(sgera), key=f"s_eg_{sid}")
                        eq = st.number_input("Qtd. de estoque", min_value=0, step=1, value=int(sqtd or 0), key=f"s_eq_{sid}", disabled=not eg)
                        c2 = st.columns(2)
                        if c2[0].button("Salvar", key=f"s_save_{sid}"):
                            cursor.execute("UPDATE servicos SET nome=?, valor=?, tempo_sessao_min=?, gera_estoque=?, estoque_qtd=? WHERE id=?",
                                           (en.strip(), float(ev), int(et), int(eg), int(eq if eg else 0), sid))
                            conn.commit(); st.success("Serviço atualizado!"); st.session_state["edit_srv"]=None; st.rerun()
                        if c2[1].button("Cancelar", key=f"s_cancel_{sid}"):
                            st.session_state["edit_srv"]=None; st.rerun()
        else:
            st.info("Nenhum serviço cadastrado.")

# Agendamento
elif menu == "Agendamento":
    st.subheader("📅 Agendamentos")
    clientes = cursor.execute("SELECT id, nome FROM clientes ORDER BY nome").fetchall()
    d_cli = {c[1]: c[0] for c in clientes}
    servicos = cursor.execute("SELECT id, nome FROM servicos ORDER BY nome").fetchall()
    nomes_serv = [s[1] for s in servicos]

    col1,col2 = st.columns([1,2])
    with col1:
        cliente_nome = st.selectbox("Cliente", [""] + list(d_cli.keys()))
        data_ag = st.date_input("Data", date.today())
        hora = st.text_input("Hora (ex: 14:30)")
        serv_sel = st.multiselect("Serviços", nomes_serv)
        if st.button("Salvar Agendamento"):
            if not cliente_nome: st.error("Selecione um cliente.")
            elif not hora: st.error("Informe a hora.")
            else:
                cursor.execute("""
                    INSERT INTO agendamentos (cliente_id, data, hora, servicos, status)
                    VALUES (?,?,?,?, 'Agendado')
                """, (d_cli[cliente_nome], data_ag.strftime("%Y-%m-%d"), hora, ", ".join(serv_sel)))
                conn.commit(); st.success("Agendamento salvo!"); st.rerun()
    with col2:
        df_ag = pd.read_sql_query("""
            SELECT a.id, c.nome AS cliente, a.data, a.hora, a.servicos, a.status
            FROM agendamentos a JOIN clientes c ON a.cliente_id=c.id
            ORDER BY a.data, a.hora
        """, conn)
        st.dataframe(df_ag, use_container_width=True)

# Vendas (UI melhorada + pré-venda de agendamento)
elif menu == "Vendas":
    st.subheader("💰 Painel de Vendas")

    st.markdown("""
        <style>
        .card {border:1px solid #eee; border-radius:14px; padding:14px; box-shadow:0 4px 18px rgba(0,0,0,.05);}
        .title {font-weight:700; margin-bottom:8px;}
        </style>
    """, unsafe_allow_html=True)

    if "carrinho" not in st.session_state: st.session_state.carrinho = []

    with st.container():
        colA, colB = st.columns([1,1])
        with colA:
            st.markdown('<div class="card"><div class="title">Origem da venda</div>', unsafe_allow_html=True)
            modo = st.radio("", ["Nova venda", "Carregar de agendamento"], horizontal=True, key="modo_venda_v5")
            st.markdown('</div>', unsafe_allow_html=True)
        with colB:
            clientes = cursor.execute("SELECT id, nome FROM clientes ORDER BY nome").fetchall()
            nomes_cli = ["Selecione..."] + [c[1] for c in clientes]
            idxc = st.selectbox("Cliente", range(len(nomes_cli)), format_func=lambda i: nomes_cli[i], key="cli_venda_v5")
            cliente_id = None if idxc==0 else clientes[idxc-1][0]

    produtos = cursor.execute("SELECT id, cod, nome, preco_venda, quantidade FROM produtos ORDER BY nome").fetchall()
    servicos = cursor.execute("SELECT id, nome, valor FROM servicos ORDER BY nome").fetchall()

    if modo == "Carregar de agendamento":
        ags = cursor.execute("""
            SELECT a.id, c.nome, a.servicos
            FROM agendamentos a JOIN clientes c ON a.cliente_id=c.id
            ORDER BY a.id DESC LIMIT 200
        """).fetchall()
        if ags:
            label_map = {f"#{i[0]} - {i[1]} - {i[2]}": i for i in ags}
            escolha = st.selectbox("Agendamento", list(label_map.keys()))
            if st.button("Carregar pré-venda do agendamento"):
                _, nome_cli, lista_serv = label_map[escolha]
                for s in servicos:
                    if s[1] in (lista_serv or ""):
                        st.session_state.carrinho.append({"tipo":"servico","id":s[0],"nome":s[1],"qtd":1,"preco":float(s[2] or 0.0)})
                st.success("Pré-venda carregada. Complete com produtos se quiser.")
        else:
            st.info("Sem agendamentos.")

    tab_prod, tab_serv = st.tabs(["Produtos", "Serviços"])
    with tab_prod:
        if produtos:
            nomes = [f"{p[2]} (COD: {p[1] or '-'})  |  Estoque: {p[4]}" for p in produtos]
            sel = st.selectbox("Produto", nomes)
            idx = nomes.index(sel); p = produtos[idx]
            qtd = st.number_input("Qtd", min_value=1, step=1, value=1, key="qtdp_v5")
            preco = st.number_input("Preço (R$)", min_value=0.0, step=0.5, value=float(p[3] or 0.0), format="%.2f", key="pp_v5")
            if st.button("Adicionar produto"):
                st.session_state.carrinho.append({"tipo":"produto","id":p[0],"nome":p[2],"qtd":int(qtd),"preco":float(preco)}); st.success("Adicionado.")
        else: st.info("Cadastre produtos.")
    with tab_serv:
        if servicos:
            nomes = [f"{s[1]} (R$ {s[2]:.2f})" for s in servicos]
            sel = st.selectbox("Serviço", nomes)
            idx = nomes.index(sel); s = servicos[idx]
            qtd = st.number_input("Qtd", min_value=1, step=1, value=1, key="qtds_v5")
            preco = st.number_input("Preço (R$)", min_value=0.0, step=0.5, value=float(s[2] or 0.0), format="%.2f", key="ps_v5")
            if st.button("Adicionar serviço"):
                st.session_state.carrinho.append({"tipo":"servico","id":s[0],"nome":s[1],"qtd":int(qtd),"preco":float(preco)}); st.success("Adicionado.")
        else: st.info("Cadastre serviços.")

    st.markdown("### Carrinho")
    if st.session_state.carrinho:
        dfc = pd.DataFrame([{"Tipo":i["tipo"],"Item":i["nome"],"Qtd":i["qtd"],"Preço":i["preco"],"Subtotal":i["qtd"]*i["preco"]} for i in st.session_state.carrinho])
        dfc["Preço"] = dfc["Preço"].apply(moeda); dfc["Subtotal"] = dfc["Subtotal"].apply(moeda)
        st.dataframe(dfc, use_container_width=True)
        total = sum(i["qtd"]*i["preco"] for i in st.session_state.carrinho)
        st.markdown(f"**Total:** {moeda(total)}")

        c1,c2,c3 = st.columns([2,2,1])
        with c2:
            forma = st.selectbox("Forma de pagamento", ["Dinheiro","Pix","Cartão","Outro"])
        with c3:
            if st.button("Finalizar venda", type="primary"):
                if not cliente_id: st.error("Selecione um cliente.")
                else:
                    agora = datetime.now().isoformat()
                    origem = "nova"
                    if modo == "Carregar de agendamento":
                        try:
                            ag_id = int(escolha.split()[0].replace("#",""))
                            origem = f"agendamento:{ag_id}"
                        except Exception:
                            origem = "agendamento"
                    cursor.execute("INSERT INTO vendas (cliente_id, data, total, forma_pagamento, origem) VALUES (?,?,?,?,?)",
                                   (cliente_id, agora, total, forma, origem))
                    venda_id = cursor.lastrowid
                    for it in st.session_state.carrinho:
                        cursor.execute("INSERT INTO venda_itens (venda_id, tipo, item_id, quantidade, preco) VALUES (?,?,?,?,?)",
                                       (venda_id, it["tipo"], it["id"], it["qtd"], it["preco"]))
                        if it["tipo"]=="produto": baixar_estoque(it["id"], it["qtd"])
                    conn.commit()
                    pdf_bytes, err = gerar_pdf_venda(venda_id)
                    if pdf_bytes:
                        st.download_button("Baixar comprovante (PDF)", data=pdf_bytes, file_name=f"comprovante_venda_{venda_id}.pdf", mime="application/pdf", key=f"pdf_{venda_id}")
                    else:
                        st.warning(f"PDF não gerado: {err}")
                    st.success(f"Venda #{venda_id} finalizada!"); st.session_state.carrinho = []

    st.markdown("---")
    st.subheader("Histórico de Vendas com Filtro e Cancelamento")
    colf = st.columns(3)
    data_de = colf[0].date_input("De", date.today())
    data_ate = colf[1].date_input("Até", date.today())
    if data_de > data_ate:
        st.error("Data inicial maior que final.")
    else:
        de = data_de.strftime("%Y-%m-%d"); ate = data_ate.strftime("%Y-%m-%d")
        vendas = cursor.execute("""
            SELECT v.id, v.data, COALESCE(c.nome,'Cliente'), v.forma_pagamento, v.total
            FROM vendas v LEFT JOIN clientes c ON c.id=v.cliente_id
            WHERE v.cancelada=0 AND date(v.data) BETWEEN ? AND ?
            ORDER BY v.id DESC
        """, (de, ate)).fetchall()
        if not vendas:
            st.info("Sem vendas no período.")
        else:
            for v in vendas:
                cols = st.columns([8,1])
                with cols[0].expander(f"Venda #{v[0]} - {data_br(v[1])} - {v[2]} - Total: {moeda(v[4])}"):
                    itens = cursor.execute("""
                        SELECT vi.tipo, vi.quantidade, vi.preco,
                               CASE WHEN vi.tipo='produto' THEN p.nome ELSE s.nome END AS nome_item
                        FROM venda_itens vi
                        LEFT JOIN produtos p ON vi.tipo='produto' AND p.id=vi.item_id
                        LEFT JOIN servicos s ON vi.tipo='servico' AND s.id=vi.item_id
                        WHERE vi.venda_id=?
                    """, (v[0],)).fetchall()
                    dfi = pd.DataFrame([{"Item":i[3],"Tipo":i[0],"Qtd":i[1],"Preço":i[2],"Subtotal":(i[1] or 0)*(i[2] or 0.0)} for i in itens])
                    if not dfi.empty:
                        dfi["Preço"] = dfi["Preço"].apply(moeda); dfi["Subtotal"] = dfi["Subtotal"].apply(moeda)
                        st.dataframe(dfi, use_container_width=True)
                    pdf_bytes, err = gerar_pdf_venda(v[0])
                    if pdf_bytes:
                        st.download_button("Baixar comprovante (PDF)", data=pdf_bytes, file_name=f"comprovante_venda_{v[0]}.pdf", mime="application/pdf", key=f"pdf_hist_{v[0]}")
                    else:
                        st.caption(f"PDF indisponível: {err}")
                if cols[1].button("❌ Cancelar", key=f"cx_{v[0]}"):
                    cursor.execute("UPDATE vendas SET cancelada=1 WHERE id=?", (v[0],))
                    conn.commit(); st.warning(f"Venda #{v[0]} cancelada."); st.rerun()

# Despesas: Nota de Produtos e Nota de Serviços (cabeçalho completo + histórico)
elif menu == "Despesas":
    st.subheader("💸 Despesas / Notas de Entrada")
    aba_prod, aba_serv = st.tabs(["Nota de Produtos", "Nota de Serviços"])

    # ---------------- Nota de Produtos ----------------
    with aba_prod:
        if "despesa_itens" not in st.session_state:
            st.session_state.despesa_itens = []

        st.markdown("#### Cabeçalho")
        c0 = st.columns(5)
        numero_nota = c0[0].text_input("Número da nota")
        data_compra = c0[1].date_input("Data da compra", value=date.today())
        fornecedor_nome = c0[2].text_input("Fornecedor - Nome")
        fornecedor_cnpj = c0[3].text_input("CNPJ")
        fornecedor_telefone = c0[4].text_input("Telefone")
        c1 = st.columns(2)
        fornecedor_endereco = c1[0].text_input("Endereço")
        chave_nfe_text = c1[1].text_input("Chave NFe (se preferir digitar)")
        st.write("Anexar imagem do QR-Code / chave da nota (opcional)")
        chave_img = st.camera_input("Escanear com a câmera (opcional)")  # guardamos a imagem, não decodificamos
        if not chave_img:
            chave_img = st.file_uploader("Ou enviar a imagem", type=["png","jpg","jpeg"])
        chave_img_bytes = chave_img.getvalue() if chave_img else None

        st.markdown("#### Itens da Nota (Produtos)")
        cols = st.columns([2,3,1,2,2,2])
        with cols[0]: cod_prod = st.text_input("COD produto", key="dx_cod")
        with cols[1]: prod_nome = st.text_input("Nome do produto", key="dx_nome")
        with cols[2]: qtd = st.number_input("Qtd", min_value=1, step=1, value=1, key="dx_qtd")
        with cols[3]: custo_unit = st.number_input("Custo unit (R$)", min_value=0.0, step=0.01, value=0.0, format="%.2f", key="dx_custo")
        with cols[4]: tipo_produto = st.selectbox("Tipo produto", ["Revenda","Uso e consumo","Matéria-prima"], key="dx_tipo")
        with cols[5]: pv = st.number_input("Preço de venda (se Revenda)", min_value=0.0, step=0.01, value=0.0, format="%.2f", key="dx_pv", disabled=(tipo_produto!="Revenda"))
        if st.button("+ Adicionar item (produto)"):
            if not cod_prod.strip():
                st.error("Informe o código do produto.")
            else:
                st.session_state.despesa_itens.append({
                    "cod_produto": cod_prod.strip(),
                    "produto_nome": prod_nome.strip(),
                    "quantidade": int(qtd),
                    "custo_unit": float(custo_unit),
                    "tipo_produto": tipo_produto,
                    "preco_venda": float(pv if tipo_produto=="Revenda" else 0.0)
                })
                st.success("Item adicionado.")

        if st.session_state.despesa_itens:
            dfi = pd.DataFrame(st.session_state.despesa_itens)
            dfi["Subtotal"] = dfi["quantidade"] * dfi["custo_unit"]
            view = dfi.copy()
            view["custo_unit"] = view["custo_unit"].apply(moeda)
            view["Subtotal"] = view["Subtotal"].apply(moeda)
            st.dataframe(view.rename(columns={"cod_produto":"COD","produto_nome":"Produto","quantidade":"Qtd","custo_unit":"Custo","tipo_produto":"Tipo","preco_venda":"Preço venda"}), use_container_width=True)
            total_desp = float(dfi["Subtotal"].sum())
            st.markdown(f"**Total:** {moeda(total_desp)}")

            if st.button("Salvar Nota de Produtos", type="primary"):
                if not fornecedor_nome.strip():
                    st.error("Informe o nome do fornecedor.")
                elif not numero_nota.strip():
                    st.error("Informe o número da nota.")
                else:
                    agora = datetime.now().isoformat()
                    cursor.execute("""
                        INSERT INTO despesas (tipo_nota, numero_nota, data_compra, fornecedor_nome, fornecedor_cnpj, fornecedor_endereco, fornecedor_telefone, chave_nfe_text, chave_nfe_img, valor_total)
                        VALUES ('Produtos',?,?,?,?,?,?,?,?,?)
                    """, (numero_nota.strip(), data_compra.strftime("%Y-%m-%d"),
                          fornecedor_nome.strip(), fornecedor_cnpj.strip(), fornecedor_endereco.strip(), fornecedor_telefone.strip(),
                          chave_nfe_text.strip(), chave_img_bytes, total_desp))
                    desp_id = cursor.lastrowid
                    for it in st.session_state.despesa_itens:
                        cursor.execute("""
                            INSERT INTO despesa_itens (despesa_id, cod_produto, produto_nome, tipo_produto, quantidade, custo_unit, preco_venda)
                            VALUES (?,?,?,?,?,?,?)
                        """, (desp_id, it["cod_produto"], it["produto_nome"], it["tipo_produto"], it["quantidade"], it["custo_unit"], it["preco_venda"]))
                        if it["tipo_produto"] == "Revenda":
                            upsert_produto_estoque_por_codigo(it["cod_produto"], it["produto_nome"], it["quantidade"], it["custo_unit"], it["preco_venda"] or 0.0)
                    conn.commit()
                    st.session_state.despesa_itens = []
                    st.success(f"Nota de Produtos #{numero_nota} salva. Estoque atualizado para itens de Revenda.")

        st.markdown("----")
        st.write("### Histórico de Notas (Produtos)")
        df_hist = pd.read_sql_query("""
            SELECT id, numero_nota, data_compra AS data, fornecedor_nome, valor_total
            FROM despesas WHERE tipo_nota='Produtos' ORDER BY id DESC
        """, conn)
        if not df_hist.empty:
            df_hist["data"] = df_hist["data"].apply(data_br)
            df_hist["valor_total"] = df_hist["valor_total"].apply(moeda)
            st.dataframe(df_hist, use_container_width=True)
        else:
            st.info("Sem notas de produtos cadastradas.")

    # ---------------- Nota de Serviços ----------------
    with aba_serv:
        if "despesa_serv_itens" not in st.session_state:
            st.session_state.despesa_serv_itens = []

        st.markdown("#### Cabeçalho")
        c0 = st.columns(5)
        numero_nota_s = c0[0].text_input("Número da nota")
        fornecedor_nome_s = c0[1].text_input("Prestador - Nome")
        fornecedor_cnpj_s = c0[2].text_input("CNPJ/CPF")
        data_emissao = c0[3].date_input("Data de emissão", value=date.today())
        data_entrada = c0[4].date_input("Data de entrada", value=date.today())
        st.write("Descrição geral (opcional):")
        desc_geral = st.text_area("Descrição do serviço prestado (geral)", placeholder="Ex.: Serviços de manutenção ...")

        st.markdown("#### Itens (Serviços)")
        cols2 = st.columns([4,1,2])
        with cols2[0]: serv_desc = st.text_input("Descrição do serviço", key="sx_desc")
        with cols2[1]: s_qtd = st.number_input("Qtd", min_value=1, step=1, value=1, key="sx_qtd")
        with cols2[2]: s_custo = st.number_input("Valor (R$)", min_value=0.0, step=0.01, value=0.0, format="%.2f", key="sx_val")
        if st.button("+ Adicionar serviço (nota)"):
            if not serv_desc.strip():
                st.error("Informe a descrição do serviço.")
            else:
                st.session_state.despesa_serv_itens.append({
                    "servico_desc": serv_desc.strip(),
                    "quantidade": int(s_qtd),
                    "custo_unit": float(s_custo)
                })
                st.success("Serviço adicionado.")

        if st.session_state.despesa_serv_itens:
            dfs = pd.DataFrame(st.session_state.despesa_serv_itens)
            dfs["Subtotal"] = dfs["quantidade"] * dfs["custo_unit"]
            view2 = dfs.copy()
            view2["custo_unit"] = view2["custo_unit"].apply(moeda)
            view2["Subtotal"] = view2["Subtotal"].apply(moeda)
            st.dataframe(view2.rename(columns={"servico_desc":"Serviço","quantidade":"Qtd","custo_unit":"Valor"}), use_container_width=True)
            total2 = float(dfs["Subtotal"].sum())
            st.markdown(f"**Total:** {moeda(total2)}")

            if st.button("Salvar Nota de Serviços", type="primary"):
                if not fornecedor_nome_s.strip():
                    st.error("Informe o prestador.")
                elif not numero_nota_s.strip():
                    st.error("Informe o número da nota.")
                else:
                    cursor.execute("""
                        INSERT INTO despesas (tipo_nota, numero_nota, data_emissao, data_entrada, fornecedor_nome, fornecedor_cnpj, valor_total, descricao)
                        VALUES ('Serviços',?,?,?,?,?,?,?)
                    """, (numero_nota_s.strip(), data_emissao.strftime("%Y-%m-%d"), data_entrada.strftime("%Y-%m-%d"),
                          fornecedor_nome_s.strip(), fornecedor_cnpj_s.strip(), total2, desc_geral.strip()))
                    desp_id = cursor.lastrowid
                    for it in st.session_state.despesa_serv_itens:
                        cursor.execute("""
                            INSERT INTO despesa_servico_itens (despesa_id, servico_desc, quantidade, custo_unit)
                            VALUES (?,?,?,?)
                        """, (desp_id, it["servico_desc"], it["quantidade"], it["custo_unit"]))
                    conn.commit()
                    st.session_state.despesa_serv_itens = []
                    st.success(f"Nota de Serviços #{numero_nota_s} salva.")

        st.markdown("----")
        st.write("### Histórico de Notas (Serviços)")
        df_hist2 = pd.read_sql_query("""
            SELECT id, numero_nota, data_emissao AS data, fornecedor_nome, valor_total
            FROM despesas WHERE tipo_nota='Serviços' ORDER BY id DESC
        """, conn)
        if not df_hist2.empty:
            df_hist2["data"] = df_hist2["data"].apply(data_br)
            df_hist2["valor_total"] = df_hist2["valor_total"].apply(moeda)
            st.dataframe(df_hist2, use_container_width=True)
        else:
            st.info("Sem notas de serviços cadastradas.")

# Relatórios (funcional): filtros + export CSV
elif menu == "Relatórios":
    st.subheader("📊 Relatórios")
    emp = get_empresa()
    st.caption(f"Empresa: {emp.get('nome','')} | CNPJ: {emp.get('cnpj','')} | Tel: {emp.get('telefone','')}")

    tipo = st.selectbox("Tipo de relatório", ["Vendas", "Despesas", "Produtos"])

    if tipo == "Vendas":
        de = st.date_input("De", date.today())
        ate = st.date_input("Até", date.today())
        if de > ate:
            st.error("Data inicial maior que final.")
        else:
            df = pd.read_sql_query(f"""
                SELECT v.id, v.data, c.nome AS cliente, v.forma_pagamento, v.total, v.cancelada
                FROM vendas v LEFT JOIN clientes c ON c.id=v.cliente_id
                WHERE date(v.data) BETWEEN '{de:%Y-%m-%d}' AND '{ate:%Y-%m-%d}'
                ORDER BY v.data DESC
            """, conn)
            if df.empty:
                st.info("Sem dados.")
            else:
                df["data"] = df["data"].apply(data_br)
                df["total"] = df["total"].apply(moeda)
                st.dataframe(df, use_container_width=True)
                st.download_button("Exportar CSV", data=df.to_csv(index=False).encode("utf-8"), file_name="relatorio_vendas.csv", mime="text/csv")

    elif tipo == "Despesas":
        de = st.date_input("De", date.today(), key="d1")
        ate = st.date_input("Até", date.today(), key="d2")
        if de > ate:
            st.error("Data inicial maior que final.")
        else:
            df = pd.read_sql_query(f"""
                SELECT id, tipo_nota, numero_nota,
                       COALESCE(data_compra, COALESCE(data_emissao, data_entrada)) AS data,
                       fornecedor_nome, valor_total
                FROM despesas
                WHERE date(COALESCE(data_compra, COALESCE(data_emissao, data_entrada))) BETWEEN '{de:%Y-%m-%d}' AND '{ate:%Y-%m-%d}'
                ORDER BY id DESC
            """, conn)
            if df.empty:
                st.info("Sem dados.")
            else:
                df["data"] = df["data"].apply(data_br)
                df["valor_total"] = df["valor_total"].apply(moeda)
                st.dataframe(df, use_container_width=True)
                st.download_button("Exportar CSV", data=df.to_csv(index=False).encode("utf-8"), file_name="relatorio_despesas.csv", mime="text/csv")

    elif tipo == "Produtos":
        df = pd.read_sql_query("SELECT id, cod, nome, quantidade, preco_custo, preco_venda, unidade FROM produtos ORDER BY nome", conn)
        if not df.empty:
            df["preco_custo"] = df["preco_custo"].apply(moeda)
            df["preco_venda"] = df["preco_venda"].apply(moeda)
        st.dataframe(df, use_container_width=True)
        st.download_button("Exportar CSV", data=df.to_csv(index=False).encode("utf-8"), file_name="relatorio_produtos.csv", mime="text/csv")

# Backup (download e importar)
elif menu == "Backup":
    st.subheader("💾 Backup")
    c1,c2 = st.columns(2)
    with c1:
        st.write("**Exportar**")
        if os.path.exists("database.db"):
            with open("database.db","rb") as f:
                st.download_button("Baixar database.db", data=f.read(), file_name="database.db")
        else:
            st.info("Banco ainda não foi criado.")

    with c2:
        st.write("**Importar**")
        updb = st.file_uploader("Selecione um arquivo database.db exportado pelo sistema", type=["db","sqlite","sqlite3"])
        if updb and st.button("Importar backup (substituir banco atual)"):
            data = updb.read()
            try:
                # salva como database.db (substitui)
                with open("database.db","wb") as f:
                    f.write(data)
                st.success("Backup importado com sucesso. Reinicie o app para aplicar.")
            except Exception as e:
                st.error(f"Falha ao importar: {e}")

# Sair
elif menu == "Sair":
    st.session_state.clear()
    st.success("Sessão encerrada.")
    st.stop()
