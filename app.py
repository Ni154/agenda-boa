# app_streamlit_completo.txt
# Execute: streamlit run app_streamlit_completo.txt

import streamlit as st
import sqlite3, os, io, base64
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
        email TEXT,
        telefone TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        telefone TEXT,
        email TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE,
        quantidade INTEGER DEFAULT 0,
        preco_venda REAL DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        unidade TEXT,
        quantidade INTEGER DEFAULT 0,
        valor REAL DEFAULT 0
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
    # Despesas + fornecedor
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        descricao TEXT,
        valor REAL,                       -- compatibilidade antiga
        fornecedor_nome TEXT,
        fornecedor_cnpj TEXT,
        fornecedor_endereco TEXT,
        fornecedor_telefone TEXT,
        valor_total REAL
    )
    """)
    # Itens da despesa
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesa_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        despesa_id INTEGER NOT NULL,
        produto_nome TEXT NOT NULL,
        categoria TEXT,
        tipo_item TEXT,         -- 'Uso e consumo' ou 'Revenda'
        quantidade INTEGER NOT NULL,
        custo_unit REAL NOT NULL,
        FOREIGN KEY(despesa_id) REFERENCES despesas(id)
    )
    """)
    conn.commit()

def criar_usuario_padrao():
    if not cursor.execute("SELECT 1 FROM usuarios WHERE usuario='admin'").fetchone():
        cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES ('admin','admin')")
        conn.commit()

criar_tabelas()
criar_usuario_padrao()

# ---------------- HELPERS ----------------
def moeda(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
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

def upsert_produto_estoque(nome, quantidade):
    row = cursor.execute("SELECT id FROM produtos WHERE nome=?", (nome,)).fetchone()
    if row:
        cursor.execute("UPDATE produtos SET quantidade = COALESCE(quantidade,0)+? WHERE id=?", (int(quantidade), row[0]))
    else:
        cursor.execute("INSERT INTO produtos (nome, quantidade, preco_venda) VALUES (?, ?, 0.0)", (nome, int(quantidade)))
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
        return None, f"Falta reportlab ({e})"

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

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w,h = A4
    y = h - 20*mm
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

# --------------- LOGIN ---------------
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("🔐 Login")
    usuario_input = st.text_input("Usuário")
    senha_input = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if cursor.execute("SELECT 1 FROM usuarios WHERE usuario=? AND senha=?", (usuario_input, senha_input)).fetchone():
            st.session_state.login = True
            st.session_state["menu"] = "Cadastro Cliente"  # começa em Cadastro Cliente
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
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
        "Cadastro Serviços", "Agendamento", "Vendas", "Cancelar Vendas", "Despesas", "Relatórios", "Backup", "Sair"
    ]
    icones = {"Início":"🏠","Dashboard":"📈","Cadastro Cliente":"🧍","Cadastro Empresa":"🏢","Cadastro Produtos":"📦",
              "Cadastro Serviços":"💆","Agendamento":"📅","Vendas":"💰","Cancelar Vendas":"🚫","Despesas":"💸",
              "Relatórios":"📊","Backup":"💾","Sair":"🔓"}
    for opc in menu_opcoes:
        if st.button(f"{icones.get(opc,'📌')} {opc}"):
            st.session_state["menu"] = opc

menu = st.session_state.get("menu", "Início")
st.title(f"🧭 {menu}")

# --------------- PÁGINAS ---------------
# Início: manter agendamentos com nome, status e data
if menu == "Início":
    st.subheader("👋 Bem-vindo(a)!")
    data_inicio = st.date_input("De", date.today(), format="DD/MM/YYYY")
    data_fim = st.date_input("Até", date.today(), format="DD/MM/YYYY")
    if data_inicio > data_fim:
        st.error("Data inicial não pode ser maior que a final.")
    else:
        a = data_inicio.strftime("%Y-%m-%d"); b = data_fim.strftime("%Y-%m-%d")
        ags = cursor.execute("""
            SELECT a.id, c.nome, a.data, a.hora, a.servicos, a.status
            FROM agendamentos a JOIN clientes c ON a.cliente_id=c.id
            WHERE a.data BETWEEN ? AND ? ORDER BY a.data, a.hora
        """, (a,b)).fetchall()
        if ags:
            for ag in ags:
                st.info(f"📅 {data_br(ag[2])} 🕒 {ag[3]} | 👤 {ag[1]} | 📌 Status: {ag[5]} | 💼 {ag[4]}")
        else:
            st.warning("Nenhum agendamento no período.")

# Dashboard simples
elif menu == "Dashboard":
    st.subheader("📊 Visão Geral")
    total_clientes = cursor.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    total_vendas = cursor.execute("SELECT COUNT(*) FROM vendas WHERE cancelada=0").fetchone()[0]
    total_produtos = cursor.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
    total_servicos = cursor.execute("SELECT COUNT(*) FROM servicos").fetchone()[0]
    total_despesas = cursor.execute("SELECT COALESCE(SUM(COALESCE(valor_total, valor)),0) FROM despesas").fetchone()[0]
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

# Cadastro Cliente
elif menu == "Cadastro Cliente":
    st.subheader("🧍 Clientes")
    col1,col2 = st.columns([1,2])
    with col1:
        with st.form("form_cliente", clear_on_submit=True):
            nome = st.text_input("Nome")
            telefone = st.text_input("Telefone")
            email = st.text_input("E-mail")
            if st.form_submit_button("Salvar Cliente"):
                if nome.strip():
                    cursor.execute("INSERT INTO clientes (nome, telefone, email) VALUES (?,?,?)",
                                   (nome.strip(), telefone.strip(), email.strip()))
                    conn.commit()
                    st.success("Cliente salvo!")
                else:
                    st.error("Informe o nome.")
    with col2:
        dfc = pd.read_sql_query("SELECT id, nome, telefone, email FROM clientes ORDER BY nome", conn)
        st.dataframe(dfc, use_container_width=True)

# Cadastro Empresa (placeholder)
elif menu == "Cadastro Empresa":
    st.subheader("🏢 Cadastro da Empresa")
    st.info("Inclua aqui os campos da sua empresa (CNPJ, IE, endereço, etc.).")

# Cadastro Produtos com histórico + ícones editar/excluir
elif menu == "Cadastro Produtos":
    st.subheader("📦 Produtos")
    if "edit_prod_id" not in st.session_state:
        st.session_state.edit_prod_id = None

    col1,col2 = st.columns([1,2])
    with col1:
        with st.form("form_produto", clear_on_submit=True):
            nome = st.text_input("Nome do produto")
            qtd = st.number_input("Quantidade", min_value=0, step=1, value=0)
            preco = st.number_input("Preço de venda (R$)", min_value=0.0, step=1.0, format="%.2f")
            if st.form_submit_button("Salvar"):
                if nome.strip():
                    try:
                        cursor.execute("INSERT INTO produtos (nome, quantidade, preco_venda) VALUES (?,?,?)",
                                       (nome.strip(), int(qtd), float(preco)))
                    except sqlite3.IntegrityError:
                        cursor.execute("UPDATE produtos SET quantidade=COALESCE(quantidade,0)+?, preco_venda=? WHERE nome=?",
                                       (int(qtd), float(preco), nome.strip()))
                    conn.commit()
                    st.success("Produto salvo/atualizado!")
                else:
                    st.error("Informe o nome.")
    with col2:
        st.write("### Histórico de Produtos")
        prods = cursor.execute("SELECT id, nome, quantidade, preco_venda FROM produtos ORDER BY nome").fetchall()
        if not prods:
            st.info("Nenhum produto cadastrado.")
        else:
            for pid, pnome, pqtd, ppreco in prods:
                c = st.columns([4,2,2,1,1])
                c[0].write(pnome)
                c[1].write(int(pqtd or 0))
                c[2].write(moeda(ppreco or 0))
                if c[3].button("✏️", key=f"edit_prod_{pid}"):
                    st.session_state.edit_prod_id = pid
                if c[4].button("❌", key=f"del_prod_{pid}"):
                    cursor.execute("DELETE FROM produtos WHERE id=?", (pid,))
                    conn.commit()
                    st.warning(f"Produto '{pnome}' excluído.")
                    st.rerun()
                if st.session_state.edit_prod_id == pid:
                    with st.expander(f"Editar: {pnome}", expanded=True):
                        novo_nome = st.text_input("Nome", value=pnome, key=f"en_{pid}")
                        nova_qtd = st.number_input("Quantidade", min_value=0, step=1, value=int(pqtd or 0), key=f"eq_{pid}")
                        novo_preco = st.number_input("Preço de venda (R$)", min_value=0.0, step=1.0, value=float(ppreco or 0.0), format="%.2f", key=f"ep_{pid}")
                        cols = st.columns(2)
                        if cols[0].button("Salvar alterações", key=f"save_{pid}"):
                            try:
                                cursor.execute("UPDATE produtos SET nome=?, quantidade=?, preco_venda=? WHERE id=?",
                                               (novo_nome.strip(), int(nova_qtd), float(novo_preco), pid))
                                conn.commit()
                                st.success("Produto atualizado!")
                                st.session_state.edit_prod_id = None
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("Nome de produto já existe. Escolha outro.")
                        if cols[1].button("Cancelar", key=f"cancel_{pid}"):
                            st.session_state.edit_prod_id = None
                            st.rerun()

# Cadastro Serviços
elif menu == "Cadastro Serviços":
    st.subheader("💆 Serviços")
    col1,col2 = st.columns([1,2])
    with col1:
        with st.form("form_servico", clear_on_submit=True):
            nome = st.text_input("Nome")
            unidade = st.text_input("Unidade (ex: sessão)")
            quantidade = st.number_input("Quantidade", min_value=0, step=1, value=0)
            valor = st.number_input("Valor (R$)", min_value=0.0, step=1.0, format="%.2f")
            if st.form_submit_button("Salvar"):
                if nome.strip():
                    cursor.execute("INSERT INTO servicos (nome, unidade, quantidade, valor) VALUES (?,?,?,?)",
                                   (nome.strip(), unidade.strip(), int(quantidade), float(valor)))
                    conn.commit()
                    st.success("Serviço salvo!")
                else:
                    st.error("Informe o nome.")
    with col2:
        dfs = pd.read_sql_query("SELECT id, nome, unidade, quantidade, valor FROM servicos ORDER BY nome", conn)
        if not dfs.empty:
            dfs["valor"] = dfs["valor"].apply(moeda)
        st.dataframe(dfs, use_container_width=True)

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

# Vendas
elif menu == "Vendas":
    st.subheader("💰 Painel de Vendas")
    if "carrinho" not in st.session_state: st.session_state.carrinho = []
    clientes = cursor.execute("SELECT id, nome FROM clientes ORDER BY nome").fetchall()
    produtos = cursor.execute("SELECT id, nome, preco_venda, quantidade FROM produtos ORDER BY nome").fetchall()
    servicos = cursor.execute("SELECT id, nome, valor FROM servicos ORDER BY nome").fetchall()

    tab_prod, tab_serv = st.tabs(["Produtos", "Serviços"])
    with tab_prod:
        if produtos:
            nomes = [f"{p[1]} (Estoque: {p[3]})" for p in produtos]
            sel = st.selectbox("Produto", nomes)
            idx = nomes.index(sel); p = produtos[idx]
            qtd = st.number_input("Qtd", min_value=1, step=1, value=1, key="qtdp")
            preco = st.number_input("Preço (R$)", min_value=0.0, step=1.0, value=float(p[2] or 0.0), format="%.2f", key="pp")
            if st.button("Adicionar produto"):
                st.session_state.carrinho.append({"tipo":"produto","id":p[0],"nome":p[1],"qtd":int(qtd),"preco":float(preco)}); st.success("Adicionado.")
        else: st.info("Cadastre produtos.")
    with tab_serv:
        if servicos:
            nomes = [f"{s[1]} (R$ {s[2]:.2f})" for s in servicos]
            sel = st.selectbox("Serviço", nomes)
            idx = nomes.index(sel); s = servicos[idx]
            qtd = st.number_input("Qtd", min_value=1, step=1, value=1, key="qtds")
            preco = st.number_input("Preço (R$)", min_value=0.0, step=1.0, value=float(s[2] or 0.0), format="%.2f", key="ps")
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
        with c1:
            nomes_cli = ["Selecione..."] + [c[1] for c in clientes]
            idxc = st.selectbox("Cliente", range(len(nomes_cli)), format_func=lambda i: nomes_cli[i])
            cliente_id = None if idxc==0 else clientes[idxc-1][0]
        with c2:
            forma = st.selectbox("Forma de pagamento", ["Dinheiro","Pix","Cartão","Outro"])
        with c3:
            if st.button("Finalizar venda", type="primary"):
                if not cliente_id: st.error("Selecione um cliente.")
                else:
                    agora = datetime.now().isoformat()
                    cursor.execute("INSERT INTO vendas (cliente_id, data, total, forma_pagamento) VALUES (?,?,?,?)",
                                   (cliente_id, agora, total, forma))
                    venda_id = cursor.lastrowid
                    for it in st.session_state.carrinho:
                        cursor.execute("INSERT INTO venda_itens (venda_id, tipo, item_id, quantidade, preco) VALUES (?,?,?,?,?)",
                                       (venda_id, it["tipo"], it["id"], it["qtd"], it["preco"]))
                        if it["tipo"]=="produto": baixar_estoque(it["id"], it["qtd"])
                    conn.commit()
                    pdf_bytes, err = gerar_pdf_venda(venda_id)
                    if pdf_bytes:
                        st.download_button("Baixar comprovante (PDF)", data=pdf_bytes, file_name=f"comprovante_venda_{venda_id}.pdf", mime="application/pdf")
                    else:
                        st.warning(f"PDF não gerado: {err}")
                    st.success(f"Venda #{venda_id} finalizada!"); st.session_state.carrinho = []

    st.markdown("---")
    st.subheader("Histórico de Vendas")
    vendas = cursor.execute("""
        SELECT v.id, v.data, COALESCE(c.nome,'Cliente'), v.forma_pagamento, v.total
        FROM vendas v LEFT JOIN clientes c ON c.id=v.cliente_id
        WHERE v.cancelada=0 ORDER BY v.id DESC LIMIT 100
    """).fetchall()
    for v in vendas:
        with st.expander(f"Venda #{v[0]} - {data_br(v[1])} - {v[2]} - Total: {moeda(v[4])}"):
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
                st.download_button("Baixar comprovante (PDF)", data=pdf_bytes, file_name=f"comprovante_venda_{v[0]}.pdf", mime="application/pdf", key=f"pdf_{v[0]}")
            else:
                st.caption(f"PDF indisponível: {err}")

# Cancelar Vendas
elif menu == "Cancelar Vendas":
    st.subheader("🚫 Cancelar Vendas")
    vendas = cursor.execute("""
        SELECT v.id, COALESCE(c.nome,'Cliente'), v.data, v.total
        FROM vendas v LEFT JOIN clientes c ON c.id=v.cliente_id
        WHERE v.cancelada=0 ORDER BY v.id DESC LIMIT 100
    """).fetchall()
    if not vendas:
        st.info("Sem vendas para cancelar.")
    else:
        opcoes = {f"#{v[0]} - {v[1]} - {data_br(v[2])} - {moeda(v[3])}": v[0] for v in vendas}
        sel = st.selectbox("Selecione a venda", list(opcoes.keys()))
        if st.button("Cancelar venda selecionada"):
            cursor.execute("UPDATE vendas SET cancelada=1 WHERE id=?", (opcoes[sel],))
            conn.commit(); st.success("Venda cancelada."); st.rerun()

# Despesas com fornecedor + itens (com Revenda entrando no estoque)
elif menu == "Despesas":
    st.subheader("💸 Despesas com Fornecedor")

    if "despesa_itens" not in st.session_state:
        st.session_state.despesa_itens = []

    with st.form("form_despesa"):
        cfor = st.columns(4)
        with cfor[0]: fornecedor_nome = st.text_input("Fornecedor - Nome")
        with cfor[1]: fornecedor_cnpj = st.text_input("CNPJ (opcional)")
        with cfor[2]: fornecedor_endereco = st.text_input("Endereço (opcional)")
        with cfor[3]: fornecedor_telefone = st.text_input("Telefone (opcional)")
        descricao = st.text_input("Descrição")

        st.markdown("### Itens")
        cols = st.columns([3,1,2,2,2])
        with cols[0]: produto_nome = st.text_input("Produto/Item")
        with cols[1]: quantidade = st.number_input("Qtd", min_value=1, step=1, value=1)
        with cols[2]: categoria = st.selectbox("Categoria", ["Sem categoria","Geral","Insumo","Embalagem","Higiene","Outro"])
        with cols[3]: tipo_item = st.selectbox("Tipo", ["Uso e consumo","Revenda"])
        with cols[4]: custo_unit = st.number_input("Custo unit (R$)", min_value=0.0, step=0.5, format="%.2f")

        add = st.form_submit_button("+ Adicionar item")
        if add and produto_nome.strip():
            st.session_state.despesa_itens.append({
                "produto_nome": produto_nome.strip(),
                "quantidade": int(quantidade),
                "categoria": categoria,
                "tipo_item": tipo_item,
                "custo_unit": float(custo_unit)
            })
            st.success("Item adicionado.")

    if st.session_state.despesa_itens:
        dfi = pd.DataFrame(st.session_state.despesa_itens)
        dfi["Subtotal"] = dfi["quantidade"] * dfi["custo_unit"]
        dview = dfi.copy()
        dview["custo_unit"] = dview["custo_unit"].apply(moeda)
        dview["Subtotal"] = dview["Subtotal"].apply(moeda)
        st.dataframe(dview.rename(columns={
            "produto_nome":"Produto","quantidade":"Qtd","categoria":"Categoria","tipo_item":"Tipo","custo_unit":"Custo unit"
        }), use_container_width=True)
        total_desp = float(dfi["Subtotal"].sum())
        st.markdown(f"**Total:** {moeda(total_desp)}")
        c1,c2 = st.columns(2)
        with c1:
            if st.button("Salvar despesa"):
                if not fornecedor_nome.strip():
                    st.error("Informe o nome do fornecedor.")
                else:
                    agora = datetime.now().isoformat()
                    cursor.execute("""
                        INSERT INTO despesas (data, descricao, valor, fornecedor_nome, fornecedor_cnpj, fornecedor_endereco, fornecedor_telefone, valor_total)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (agora, descricao, total_desp, fornecedor_nome.strip(), fornecedor_cnpj.strip(),
                          fornecedor_endereco.strip(), fornecedor_telefone.strip(), total_desp))
                    desp_id = cursor.lastrowid
                    for it in st.session_state.despesa_itens:
                        cursor.execute("""
                            INSERT INTO despesa_itens (despesa_id, produto_nome, categoria, tipo_item, quantidade, custo_unit)
                            VALUES (?,?,?,?,?,?)
                        """, (desp_id, it["produto_nome"], it["categoria"], it["tipo_item"], it["quantidade"], it["custo_unit"]))
                        if it["tipo_item"] == "Revenda":
                            upsert_produto_estoque(it["produto_nome"], it["quantidade"])
                    conn.commit()
                    st.session_state.despesa_itens = []
                    st.success(f"Despesa #{desp_id} salva. Estoque atualizado para itens de Revenda.")
        with c2:
            if st.button("Limpar itens"):
                st.session_state.despesa_itens = []; st.info("Itens limpos.")

    st.markdown("---")
    st.subheader("Histórico de Despesas (50 últimas)")
    dfdesp = pd.read_sql_query("""
        SELECT id, data, fornecedor_nome, valor_total, descricao
        FROM despesas ORDER BY id DESC LIMIT 50
    """, conn)
    if not dfdesp.empty:
        dfdesp["data"] = dfdesp["data"].apply(data_br)
        dfdesp["valor_total"] = dfdesp["valor_total"].apply(moeda)
    st.dataframe(dfdesp.rename(columns={"id":"ID","data":"Data","fornecedor_nome":"Fornecedor","valor_total":"Total","descricao":"Descrição"}),
                 use_container_width=True)

# Relatórios (placeholder)
elif menu == "Relatórios":
    st.subheader("📈 Relatórios")
    st.info("Monte filtros e exportações aqui (CSV/PDF).")

# Backup (download do banco)
elif menu == "Backup":
    st.subheader("💾 Backup")
    if os.path.exists("database.db"):
        with open("database.db","rb") as f:
            st.download_button("Baixar database.db", data=f.read(), file_name="database.db")
    else:
        st.info("Banco ainda não foi criado.")

# Sair
elif menu == "Sair":
    st.session_state.clear()
    st.success("Sessão encerrada.")
    st.stop()
