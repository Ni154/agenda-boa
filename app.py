# app_streamlit_baseado_original.txt
# Executar: streamlit run app_streamlit_baseado_original.txt

import streamlit as st
import sqlite3, os
import pandas as pd
from datetime import date, datetime
import io

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Studio - ERP", layout="wide")

# --------------- CONEXÃO / DB ---------------
@st.cache_resource
def get_conn():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

conn = get_conn()
cursor = conn.cursor()

def criar_tabelas_basicas():
    # --- Tabelas base conforme seu app original ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        senha TEXT
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
        quantidade INTEGER,
        valor REAL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        unidade TEXT,
        quantidade INTEGER,
        valor REAL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agendamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        data TEXT,
        hora TEXT,
        servicos TEXT,
        status TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        data TEXT,
        total REAL,
        cancelada INTEGER DEFAULT 0,
        forma_pagamento TEXT
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS venda_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER,
        tipo TEXT,
        item_id INTEGER,
        quantidade INTEGER,
        preco REAL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        descricao TEXT,
        valor REAL
    )
    """)
    conn.commit()

def upgrade_esquema():
    # Acrescenta colunas de fornecedor na tabela despesas (se não existirem)
    for coldef in [
        "fornecedor_nome TEXT",
        "fornecedor_cnpj TEXT",
        "fornecedor_endereco TEXT",
        "fornecedor_telefone TEXT",
        "valor_total REAL"
    ]:
        try:
            cursor.execute(f"ALTER TABLE despesas ADD COLUMN {coldef}")
            conn.commit()
        except Exception:
            pass  # já existe
    # Tabela de itens da despesa
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesa_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        despesa_id INTEGER NOT NULL,
        produto_nome TEXT NOT NULL,
        categoria TEXT,
        tipo_item TEXT,       -- 'Uso e consumo' ou 'Revenda'
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

criar_tabelas_basicas()
upgrade_esquema()
criar_usuario_padrao()

# ---------------- HELPERS ----------------
def formatar_moeda(val):
    try:
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def formatar_data_br(s):
    try:
        return datetime.fromisoformat(s).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return s

def upsert_produto_estoque(nome, quantidade):
    row = cursor.execute("SELECT id FROM produtos WHERE nome=?", (nome,)).fetchone()
    if row:
        cursor.execute("UPDATE produtos SET quantidade = COALESCE(quantidade,0) + ? WHERE id=?", (int(quantidade), row[0]))
    else:
        cursor.execute("INSERT INTO produtos (nome, quantidade, valor) VALUES (?, ?, 0.0)", (nome, int(quantidade)))
    conn.commit()

def baixar_estoque(item_id, quantidade):
    cursor.execute("UPDATE produtos SET quantidade = MAX(0, COALESCE(quantidade,0) - ?) WHERE id=?", (int(quantidade), item_id))
    conn.commit()

def gerar_comprovante_pdf(venda_id:int):
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

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    y = h - 20*mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20*mm, y, "Comprovante de Venda")
    y -= 8*mm
    c.setFont("Helvetica", 10)
    c.drawString(20*mm, y, f"Venda #{venda[0]}")
    y -= 6*mm
    c.drawString(20*mm, y, f"Data: {formatar_data_br(venda[1])}")
    y -= 6*mm
    c.drawString(20*mm, y, f"Cliente: {venda[2]}")
    y -= 6*mm
    c.drawString(20*mm, y, f"Pagamento: {venda[3]}")
    y -= 10*mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(20*mm, y, "Item")
    c.drawString(110*mm, y, "Qtd")
    c.drawString(130*mm, y, "Preço")
    c.drawString(160*mm, y, "Subtotal")
    y -= 5*mm
    c.line(20*mm, y, 190*mm, y)
    y -= 5*mm
    c.setFont("Helvetica", 10)

    total = 0.0
    for tipo, qtd, preco, nome_item in itens:
        if y < 30*mm:
            c.showPage()
            y = h - 20*mm
        subtotal = (qtd or 0) * (preco or 0.0)
        total += subtotal
        c.drawString(20*mm, y, f"{nome_item} ({tipo})")
        c.drawRightString(125*mm, y, str(qtd))
        c.drawRightString(155*mm, y, formatar_moeda(preco))
        c.drawRightString(190*mm, y, formatar_moeda(subtotal))
        y -= 6*mm

    y -= 6*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(190*mm, y, f"TOTAL: {formatar_moeda(total)}")
    c.showPage()
    c.save()

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
            # Começar em "Cadastro Cliente" (pedido do usuário)
            st.session_state["menu"] = "Cadastro Cliente"
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
    st.stop()

# --------------- SIDEBAR (LOGO + MENU) ---------------
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
    uploaded_logo = st.file_uploader("Importar Logo", type=["png", "jpg", "jpeg"])
    if uploaded_logo:
        bytes_logo = uploaded_logo.read()
        with open("logo_studio.png", "wb") as f:
            f.write(bytes_logo)
        st.session_state["logo_img"] = bytes_logo
        st.success("Logo atualizada!")

    menu_opcoes = [
        "Início", "Dashboard", "Cadastro Cliente", "Cadastro Empresa", "Cadastro Produtos",
        "Cadastro Serviços", "Agendamento", "Vendas", "Cancelar Vendas", "Despesas", "Relatórios", "Backup", "Sair"
    ]

    # Botões do menu (mantendo o estilo do original)
    for opcao in menu_opcoes:
        if st.button(opcao):
            st.session_state["menu"] = opcao

menu = st.session_state.get("menu", "Cadastro Cliente")
st.title(f"🧭 {menu}")

# --------------- PÁGINAS ---------------
# --- Cadastro Cliente (PRIMEIRO) ---
if menu == "Cadastro Cliente":
    st.subheader("🧍 Cadastro e Gerenciamento de Clientes")
    col1, col2 = st.columns([1,2])
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
        df_clientes = pd.read_sql_query("SELECT id, nome, telefone, email FROM clientes ORDER BY nome", conn)
        st.dataframe(df_clientes, use_container_width=True)

# --- Início ---
elif menu == "Início":
    st.subheader("👋 Bem-vindo(a)")
    hoje = date.today().strftime("%d/%m/%Y")
    st.markdown(f"### Agendamentos para o dia: **{hoje}**")

    data_inicio = st.date_input("Filtrar de", date.today(), format="DD/MM/YYYY")
    data_fim = st.date_input("até", date.today(), format="DD/MM/YYYY")

    if data_inicio > data_fim:
        st.error("Data inicial não pode ser maior que a data final.")
    else:
        data_inicio_iso = data_inicio.strftime("%Y-%m-%d")
        data_fim_iso = data_fim.strftime("%Y-%m-%d")
        agendamentos = cursor.execute("""
            SELECT a.id, c.nome, a.data, a.hora, a.servicos, a.status
            FROM agendamentos a
            JOIN clientes c ON a.cliente_id = c.id
            WHERE a.data BETWEEN ? AND ?
            ORDER BY a.data, a.hora
        """, (data_inicio_iso, data_fim_iso)).fetchall()
        if agendamentos:
            df = pd.DataFrame(agendamentos, columns=["ID","Cliente","Data","Hora","Serviços","Status"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Sem agendamentos no período.")

# --- Dashboard (resumo simples) ---
elif menu == "Dashboard":
    st.subheader("📊 Visão Geral")
    total_clientes = cursor.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    total_vendas = cursor.execute("SELECT COUNT(*) FROM vendas WHERE cancelada=0").fetchone()[0]
    total_produtos = cursor.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
    total_servicos = cursor.execute("SELECT COUNT(*) FROM servicos").fetchone()[0]
    total_despesas = cursor.execute("SELECT SUM(COALESCE(valor_total, valor)) FROM despesas").fetchone()[0] or 0
    total_faturamento = cursor.execute("SELECT SUM(total) FROM vendas WHERE cancelada=0").fetchone()[0] or 0
    lucro_liquido = total_faturamento - total_despesas

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Clientes", total_clientes)
    c2.metric("🧾 Vendas", total_vendas)
    c3.metric("📦 Produtos", total_produtos)
    c4.metric("💆 Serviços", total_servicos)

    st.metric("💰 Faturamento", formatar_moeda(total_faturamento))
    st.metric("💸 Despesas", formatar_moeda(total_despesas))
    st.metric("📈 Lucro Líquido", formatar_moeda(lucro_liquido))

# --- Cadastro Produtos ---
elif menu == "Cadastro Produtos":
    st.subheader("📦 Produtos")
    col1, col2 = st.columns([1,2])
    with col1:
        with st.form("form_produto", clear_on_submit=True):
            nome = st.text_input("Nome do produto")
            quantidade = st.number_input("Quantidade", min_value=0, step=1, value=0)
            valor = st.number_input("Preço de venda (R$)", min_value=0.0, format="%.2f", step=1.0)
            if st.form_submit_button("Salvar"):
                if nome.strip():
                    try:
                        cursor.execute("INSERT INTO produtos (nome, quantidade, valor) VALUES (?,?,?)",
                                       (nome.strip(), int(quantidade), float(valor)))
                    except sqlite3.IntegrityError:
                        cursor.execute("UPDATE produtos SET quantidade=COALESCE(quantidade,0)+?, valor=? WHERE nome=?",
                                       (int(quantidade), float(valor), nome.strip()))
                    conn.commit()
                    st.success("Produto salvo/atualizado!")
                else:
                    st.error("Informe o nome.")
    with col2:
        dfp = pd.read_sql_query("SELECT id, nome, quantidade, valor FROM produtos ORDER BY nome", conn)
        if not dfp.empty:
            dfp["valor"] = dfp["valor"].apply(formatar_moeda)
        st.dataframe(dfp, use_container_width=True)

# --- Cadastro Serviços ---
elif menu == "Cadastro Serviços":
    st.subheader("💆 Serviços")
    col1, col2 = st.columns([1,2])
    with col1:
        with st.form("form_servico", clear_on_submit=True):
            nome = st.text_input("Nome")
            unidade = st.text_input("Unidade (ex: sessão)")
            quantidade = st.number_input("Quantidade", min_value=0, step=1, value=0)
            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f", step=1.0)
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
            dfs["valor"] = dfs["valor"].apply(formatar_moeda)
        st.dataframe(dfs, use_container_width=True)

# --- Agendamento (básico) ---
elif menu == "Agendamento":
    st.subheader("📅 Agendamento")
    clientes = cursor.execute("SELECT id, nome FROM clientes ORDER BY nome").fetchall()
    clientes_dict = {c[1]: c[0] for c in clientes}
    servicos = cursor.execute("SELECT id, nome FROM servicos ORDER BY nome").fetchall()
    servicos_dict = {s[1]: s[0] for s in servicos}

    cliente_nome = st.selectbox("Cliente", [""] + list(clientes_dict.keys()))
    data_ag = st.date_input("Data", date.today())
    hora_ag = st.text_input("Hora (ex: 14:30)")
    servicos_sel = st.multiselect("Serviços", list(servicos_dict.keys()))

    if st.button("Salvar Agendamento"):
        if not cliente_nome:
            st.error("Selecione um cliente.")
        elif not hora_ag:
            st.error("Informe a hora.")
        elif not servicos_sel:
            st.error("Selecione ao menos um serviço.")
        else:
            cursor.execute("""
                INSERT INTO agendamentos (cliente_id, data, hora, servicos, status)
                VALUES (?,?,?,?, 'Agendado')
            """, (clientes_dict[cliente_nome], data_ag.strftime("%Y-%m-%d"), hora_ag, ", ".join(servicos_sel)))
            conn.commit()
            st.success("Agendamento salvo!")

    st.markdown("---")
    st.subheader("📋 Lista de Agendamentos")
    data_filtro = st.date_input("A partir de", date.today())
    df_ag = pd.read_sql_query(f"""
        SELECT a.id, c.nome AS cliente, a.data, a.hora, a.servicos, a.status
        FROM agendamentos a JOIN clientes c ON a.cliente_id=c.id
        WHERE a.data >= '{data_filtro.strftime("%Y-%m-%d")}' ORDER BY a.data, a.hora
    """, conn)
    st.dataframe(df_ag, use_container_width=True)

# --- Vendas ---
elif menu == "Vendas":
    st.subheader("💰 Vendas")
    # Carrinho em sessão
    if "carrinho" not in st.session_state:
        st.session_state.carrinho = []
    # Dados
    clientes = cursor.execute("SELECT id, nome FROM clientes ORDER BY nome").fetchall()
    produtos = cursor.execute("SELECT id, nome, valor, quantidade FROM produtos ORDER BY nome").fetchall()
    servicos = cursor.execute("SELECT id, nome, valor FROM servicos ORDER BY nome").fetchall()

    tabs = st.tabs(["Produtos", "Serviços"])
    with tabs[0]:
        if produtos:
            nomes = [f"{p[1]} (Estoque: {p[3]})" for p in produtos]
            sel = st.selectbox("Produto", nomes)
            idx = nomes.index(sel)
            prod = produtos[idx]
            qtd = st.number_input("Qtd", min_value=1, step=1, value=1, key="qtd_prod")
            preco = st.number_input("Preço (R$)", min_value=0.0, value=float(prod[2] or 0.0), format="%.2f", step=1.0, key="preco_prod")
            if st.button("Adicionar produto"):
                st.session_state.carrinho.append({"tipo":"produto","id":prod[0],"nome":prod[1],"qtd":int(qtd),"preco":float(preco)})
                st.success("Adicionado.")
        else:
            st.info("Cadastre produtos.")

    with tabs[1]:
        if servicos:
            nomes = [f"{s[1]} (R$ {s[2]:.2f})" for s in servicos]
            sel = st.selectbox("Serviço", nomes)
            idx = nomes.index(sel)
            serv = servicos[idx]
            qtd = st.number_input("Qtd", min_value=1, step=1, value=1, key="qtd_serv")
            preco = st.number_input("Preço (R$)", min_value=0.0, value=float(serv[2] or 0.0), format="%.2f", step=1.0, key="preco_serv")
            if st.button("Adicionar serviço"):
                st.session_state.carrinho.append({"tipo":"servico","id":serv[0],"nome":serv[1],"qtd":int(qtd),"preco":float(preco)})
                st.success("Adicionado.")
        else:
            st.info("Cadastre serviços.")

    st.markdown("### Carrinho")
    if st.session_state.carrinho:
        dfc = pd.DataFrame([
            {"Tipo":i["tipo"],"Item":i["nome"],"Qtd":i["qtd"],"Preço":i["preco"],"Subtotal":i["qtd"]*i["preco"]}
            for i in st.session_state.carrinho
        ])
        dfc["Preço"] = dfc["Preço"].apply(formatar_moeda)
        dfc["Subtotal"] = dfc["Subtotal"].apply(formatar_moeda)
        st.dataframe(dfc, use_container_width=True)

        total = sum(i["qtd"]*i["preco"] for i in st.session_state.carrinho)
        st.markdown(f"**Total:** {formatar_moeda(total)}")

        colf1, colf2, colf3 = st.columns([2,2,1])
        with colf1:
            nomes_cli = ["Selecione..."] + [c[1] for c in clientes]
            idxc = st.selectbox("Cliente", range(len(nomes_cli)), format_func=lambda i: nomes_cli[i])
            cliente_id = None if idxc==0 else clientes[idxc-1][0]
        with colf2:
            forma = st.selectbox("Forma de pagamento", ["Dinheiro","Pix","Cartão","Outro"])
        with colf3:
            if st.button("Finalizar venda", type="primary"):
                if not cliente_id:
                    st.error("Selecione um cliente.")
                else:
                    agora = datetime.now().isoformat()
                    cursor.execute("INSERT INTO vendas (cliente_id, data, total, forma_pagamento) VALUES (?,?,?,?)",
                                   (cliente_id, agora, total, forma))
                    venda_id = cursor.lastrowid
                    for it in st.session_state.carrinho:
                        cursor.execute("""
                            INSERT INTO venda_itens (venda_id, tipo, item_id, quantidade, preco)
                            VALUES (?,?,?,?,?)
                        """, (venda_id, it["tipo"], it["id"], it["qtd"], it["preco"]))
                        if it["tipo"]=="produto":
                            baixar_estoque(it["id"], it["qtd"])
                    conn.commit()
                    # Gerar PDF
                    pdf_bytes, err = gerar_comprovante_pdf(venda_id)
                    if pdf_bytes:
                        st.download_button("Baixar comprovante (PDF)", data=pdf_bytes, file_name=f"comprovante_venda_{venda_id}.pdf", mime="application/pdf")
                    else:
                        st.warning(f"Não foi possível gerar o PDF: {err}")
                    st.success(f"Venda #{venda_id} finalizada!")
                    st.session_state.carrinho = []
    else:
        st.info("Carrinho vazio.")

    st.markdown("---")
    st.subheader("Histórico de Vendas")
    vendas = cursor.execute("""
        SELECT v.id, v.data, COALESCE(c.nome,'Cliente'), v.forma_pagamento, v.total
        FROM vendas v LEFT JOIN clientes c ON c.id=v.cliente_id
        WHERE v.cancelada=0
        ORDER BY v.id DESC LIMIT 100
    """).fetchall()
    for v in vendas:
        with st.expander(f"Venda #{v[0]} - {formatar_data_br(v[1])} - {v[2]} - Total: {formatar_moeda(v[4])}"):
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
                dfi["Preço"] = dfi["Preço"].apply(formatar_moeda)
                dfi["Subtotal"] = dfi["Subtotal"].apply(formatar_moeda)
                st.dataframe(dfi, use_container_width=True)
            pdf_bytes, err = gerar_comprovante_pdf(v[0])
            if pdf_bytes:
                st.download_button("Baixar comprovante (PDF)", data=pdf_bytes, file_name=f"comprovante_venda_{v[0]}.pdf", mime="application/pdf", key=f"pdf_{v[0]}")
            else:
                st.caption(f"PDF indisponível: {err}")

# --- Cancelar Vendas (simples) ---
elif menu == "Cancelar Vendas":
    st.subheader("🚫 Cancelar Vendas")
    vendas = cursor.execute("""
        SELECT v.id, COALESCE(c.nome,'Cliente'), v.data, v.total
        FROM vendas v LEFT JOIN clientes c ON c.id=v.cliente_id
        WHERE v.cancelada=0
        ORDER BY v.id DESC LIMIT 100
    """).fetchall()
    if not vendas:
        st.info("Sem vendas para cancelar.")
    else:
        opcoes = {f"#{v[0]} - {v[1]} - {formatar_data_br(v[2])} - {formatar_moeda(v[3])}": v[0] for v in vendas}
        sel = st.selectbox("Selecione a venda", list(opcoes.keys()))
        if st.button("Cancelar venda selecionada"):
            cursor.execute("UPDATE vendas SET cancelada=1 WHERE id=?", (opcoes[sel],))
            conn.commit()
            st.success("Venda cancelada.")
            st.rerun()

# --- Despesas com fornecedor (+ itens e estoque de revenda) ---
elif menu == "Despesas":
    st.subheader("💸 Registro de Despesa com Fornecedor")

    if "despesa_itens" not in st.session_state:
        st.session_state.despesa_itens = []

    with st.form("form_despesa"):
        cfor = st.columns(4)
        with cfor[0]:
            fornecedor_nome = st.text_input("Fornecedor - Nome")
        with cfor[1]:
            fornecedor_cnpj = st.text_input("CNPJ (opcional)")
        with cfor[2]:
            fornecedor_endereco = st.text_input("Endereço (opcional)")
        with cfor[3]:
            fornecedor_telefone = st.text_input("Telefone (opcional)")

        descricao = st.text_input("Descrição da despesa")

        st.markdown("### Itens da despesa")
        cols = st.columns([3,1,2,2,2])
        with cols[0]:
            produto_nome = st.text_input("Produto/Item")
        with cols[1]:
            quantidade = st.number_input("Qtd", min_value=1, step=1, value=1)
        with cols[2]:
            categoria = st.selectbox("Categoria", ["Sem categoria","Geral","Insumo","Embalagem","Higiene","Outro"])
        with cols[3]:
            tipo_item = st.selectbox("Tipo", ["Uso e consumo","Revenda"])
        with cols[4]:
            custo_unit = st.number_input("Custo unit (R$)", min_value=0.0, step=0.5, format="%.2f")

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
        dview["custo_unit"] = dview["custo_unit"].apply(formatar_moeda)
        dview["Subtotal"] = dview["Subtotal"].apply(formatar_moeda)
        st.dataframe(dview.rename(columns={
            "produto_nome":"Produto","quantidade":"Qtd","categoria":"Categoria","tipo_item":"Tipo","custo_unit":"Custo unit"
        }), use_container_width=True)
        total_desp = float(dfi["Subtotal"].sum())
        st.markdown(f"**Total da despesa:** {formatar_moeda(total_desp)}")

        c1, c2 = st.columns(2)
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
                st.session_state.despesa_itens = []
                st.info("Itens limpos.")

    st.markdown("---")
    st.subheader("Histórico de Despesas (50 últimas)")
    dfdesp = pd.read_sql_query("""
        SELECT id, data, fornecedor_nome, valor_total, descricao
        FROM despesas ORDER BY id DESC LIMIT 50
    """, conn)
    if not dfdesp.empty:
        dfdesp["data"] = dfdesp["data"].apply(formatar_data_br)
        dfdesp["valor_total"] = dfdesp["valor_total"].apply(formatar_moeda)
    st.dataframe(dfdesp.rename(columns={
        "id":"ID","data":"Data","fornecedor_nome":"Fornecedor","valor_total":"Total","descricao":"Descrição"
    }), use_container_width=True)

# --- Cadastro Empresa (placeholder simples) ---
elif menu == "Cadastro Empresa":
    st.subheader("🏢 Cadastro da Empresa")
    st.info("Seção pronta para receber os campos específicos da sua empresa (CNPJ, IE, endereço, etc.).")

# --- Relatórios (placeholder) ---
elif menu == "Relatórios":
    st.subheader("📈 Relatórios")
    st.info("Monte filtros e exportações aqui (CSV/PDF).")

# --- Backup (placeholder) ---
elif menu == "Backup":
    st.subheader("💾 Backup")
    st.info("Implemente sua estratégia de backup (copiar database.db, exportar CSV, etc.).")

# --- Sair ---
elif menu == "Sair":
    st.session_state.clear()
    st.success("Sessão encerrada.")
    st.stop()
